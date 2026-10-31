from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts import campaigns as api
from app.core.errors import api_error, fail, not_found, raise_if
from app.db import models
from app.db.uow import UnitOfWork
from app.domain import views as dto
from app.domain.actors import Actor, require_role
from app.domain.enums import AudienceType, AuditAction, AuditEntity, CampaignState, Role
from app.domain.lifecycle import (
    TRANSITIONS,
    ensure_deletable,
    ensure_stoppable,
    ensure_transition,
    mark_edited,
)
from app.infra.cbro import export_campaign
from app.service import audit
from app.service.common import editable_campaign, get_campaign, info_snapshot
from app.service.mappers import (
    audit_record,
    campaign_details,
    campaign_list_item,
    campaign_ref,
    segments,
    snapshot,
)
from app.service.validation import (
    campaign_errors,
    campaign_warnings,
    check_schedule,
    check_segment_codes,
)


def _unique[T](values: list[T]) -> list[T]:
    return list(dict.fromkeys(values))


async def _apply_info(session: AsyncSession, c: models.Campaign, body: api.CampaignInfo) -> None:
    for index, ref in enumerate(body.tags):
        if await session.get(models.Tag, ref.value) is None:
            raise not_found(f"tags[{index}].value", ref.value)
    for index, ref in enumerate(body.places):
        if await session.get(models.Place, ref.value) is None:
            raise not_found(f"places[{index}].value", ref.value)
    errors = check_schedule(body.startDate, body.startTime, body.endDate, body.endTime)
    duplicate = await session.scalar(
        select(models.Campaign.id).where(
            models.Campaign.name == body.name, models.Campaign.id != c.id
        )
    )
    if duplicate is not None:
        errors.append(
            api_error(
                "NAME_DUPLICATE", "name", f"Кампания «{body.name}» уже существует (id {duplicate})"
            )
        )
    if body.audienceType == AudienceType.ALL_USERS and c.segment_links:
        errors.append(
            api_error(
                "SEGMENTS_FORBIDDEN_FOR_ALL_USERS",
                "audienceType",
                "У кампании сохранены сегменты: сначала очистите их через PUT /segments, затем меняйте тип аудитории",
            )
        )
    raise_if(errors)
    c.name = body.name
    c.marketing_name = body.marketingName
    c.start_date, c.start_time = (body.startDate, body.startTime)
    c.end_date, c.end_time = (body.endDate, body.endTime)
    c.topic = body.topic.value
    c.keywords = body.keywords
    c.audience_type = body.audienceType
    c.weight = body.weight
    c.initial_ctr = body.initialCtr
    c.tag_links = [
        models.CampaignTag(tag_id=t, position=i)
        for i, t in enumerate(_unique([r.value for r in body.tags]))
    ]
    c.place_links = [
        models.CampaignPlace(place_id=p, position=i, place=await session.get(models.Place, p))
        for i, p in enumerate(_unique([r.value for r in body.places]))
    ]


async def _transition(
    session: AsyncSession,
    actor: Actor,
    campaign_id: int,
    action: AuditAction,
    comment: str | None = None,
    *,
    media_base_url: str = "/api/media",
) -> models.Campaign:
    require_role(actor, TRANSITIONS[action].role)
    c = await get_campaign(session, campaign_id)
    transition = ensure_transition(c, action)
    if action == AuditAction.DECLINE and (not (comment or "").strip()):
        raise fail("DECLINE_COMMENT_REQUIRED", "comment")
    if action == AuditAction.TO_MODERATION:
        raise_if(await campaign_errors(session, c, media_base_url=media_base_url))
    if action == AuditAction.ACTIVATE:
        export_campaign(c.id)
        c.published = True
    c.state = transition.to_state
    audit.record(
        session,
        campaign_id=c.id,
        entity=AuditEntity.CAMPAIGN,
        entity_id=c.id,
        action=action,
        actor=actor.login,
        comment=comment,
    )
    return c


class CampaignService:
    def __init__(self, uow: UnitOfWork, *, media_base_url: str = "/api/media") -> None:
        self._uow = uow
        self._media_base_url = media_base_url

    async def list_campaigns(self) -> list[dto.CampaignListItem]:
        return [campaign_list_item(c) for c in await self._uow.campaigns.list()]

    async def get_campaign_details(self, campaign_id: int) -> dto.CampaignDetails:
        session = self._uow.session
        return campaign_details(await get_campaign(session, campaign_id))

    async def create_campaign(self, body: api.CampaignInfo, actor: Actor) -> dto.CampaignRef:
        session = self._uow.session
        require_role(actor, Role.MANAGER)
        c = models.Campaign(
            state=CampaignState.DRAFT,
            published=False,
            author=actor.login,
            last_edit_author=actor.login,
            tag_links=[],
            place_links=[],
            segment_links=[],
            banners=[],
            contents=[],
            creatives=[],
        )
        await _apply_info(session, c, body)
        session.add(c)
        await self._uow.flush()
        audit.record(
            session,
            campaign_id=c.id,
            entity=AuditEntity.CAMPAIGN,
            entity_id=c.id,
            action=AuditAction.CREATE,
            actor=actor.login,
        )
        return campaign_ref(c)

    async def update_campaign(
        self, campaign_id: int, body: api.CampaignInfo, actor: Actor
    ) -> dto.CampaignRef:
        session = self._uow.session
        c = await editable_campaign(session, actor, campaign_id)
        before = info_snapshot(c)
        await _apply_info(session, c, body)
        mark_edited(c, actor.login)
        await self._uow.flush()
        audit.record(
            session,
            campaign_id=c.id,
            entity=AuditEntity.CAMPAIGN,
            entity_id=c.id,
            action=AuditAction.UPDATE,
            actor=actor.login,
            changes=audit.diff(before, info_snapshot(c)),
        )
        return campaign_ref(c)

    async def delete_campaign(self, campaign_id: int, actor: Actor) -> None:
        session = self._uow.session
        require_role(actor, Role.MANAGER)
        c = await get_campaign(session, campaign_id)
        ensure_deletable(c)
        audit.record(
            session,
            campaign_id=c.id,
            entity=AuditEntity.CAMPAIGN,
            entity_id=c.id,
            action=AuditAction.DELETE,
            actor=actor.login,
        )
        await session.delete(c)
        return None

    async def set_segments(
        self, campaign_id: int, body: api.Segments, actor: Actor
    ) -> dto.Segments:
        session = self._uow.session
        c = await editable_campaign(session, actor, campaign_id)
        included, excluded = (_unique(body.included), _unique(body.excluded))
        errors = []
        if c.audience_type == AudienceType.ALL_USERS and (included or excluded):
            errors.append(
                api_error(
                    "SEGMENTS_FORBIDDEN_FOR_ALL_USERS", "included" if included else "excluded"
                )
            )
        errors += await check_segment_codes(session, included, "included")
        errors += await check_segment_codes(session, excluded, "excluded")
        for code in set(included) & set(excluded):
            errors.append(
                api_error(
                    "SEGMENT_INCLUDED_AND_EXCLUDED",
                    "excluded",
                    f"Сегмент {code} одновременно включён и исключён",
                )
            )
        raise_if(errors)
        before = snapshot(segments(c))
        c.segment_links = [
            models.CampaignSegment(segment_code=code, kind=kind, position=i)
            for kind, codes in (("included", included), ("excluded", excluded))
            for i, code in enumerate(codes)
        ]
        mark_edited(c, actor.login)
        await self._uow.flush()
        after = snapshot(segments(c))
        audit.record(
            session,
            campaign_id=c.id,
            entity=AuditEntity.SEGMENTS,
            entity_id=c.id,
            action=AuditAction.UPDATE,
            actor=actor.login,
            changes=audit.diff(before, after),
        )
        return segments(c)

    async def get_warnings(self, campaign_id: int) -> dto.ValidationReport:
        session = self._uow.session
        c = await get_campaign(session, campaign_id)
        return dto.ValidationReport(
            errors=await campaign_errors(session, c, media_base_url=self._media_base_url),
            warnings=campaign_warnings(c),
        )

    async def get_audit(self, campaign_id: int) -> list[dto.AuditRecord]:
        session = self._uow.session
        await get_campaign(session, campaign_id)
        rows = await session.scalars(
            select(models.AuditEntry)
            .where(models.AuditEntry.campaign_id == campaign_id)
            .order_by(models.AuditEntry.at, models.AuditEntry.id)
        )
        return [audit_record(e) for e in rows]

    async def send_to_moderation(self, campaign_id: int, actor: Actor) -> dto.CampaignRef:
        session = self._uow.session
        return campaign_ref(
            await _transition(
                session,
                actor,
                campaign_id,
                AuditAction.TO_MODERATION,
                media_base_url=self._media_base_url,
            )
        )

    async def decline_campaign(
        self, campaign_id: int, body: api.DeclineBody, actor: Actor
    ) -> dto.CampaignRef:
        session = self._uow.session
        return campaign_ref(
            await _transition(
                session,
                actor,
                campaign_id,
                AuditAction.DECLINE,
                comment=body.comment,
                media_base_url=self._media_base_url,
            )
        )

    async def approve_campaign(self, campaign_id: int, actor: Actor) -> dto.CampaignRef:
        session = self._uow.session
        return campaign_ref(
            await _transition(
                session,
                actor,
                campaign_id,
                AuditAction.APPROVE,
                media_base_url=self._media_base_url,
            )
        )

    async def activate_campaign(self, campaign_id: int, actor: Actor) -> dto.CampaignRef:
        session = self._uow.session
        return campaign_ref(
            await _transition(
                session,
                actor,
                campaign_id,
                AuditAction.ACTIVATE,
                media_base_url=self._media_base_url,
            )
        )

    async def stop_campaign(self, campaign_id: int, actor: Actor) -> dto.CampaignRef:
        session = self._uow.session
        require_role(actor, Role.MANAGER)
        c = await get_campaign(session, campaign_id)
        ensure_stoppable(c)
        c.state = CampaignState.STOPPED
        c.published = False
        audit.record(
            session,
            campaign_id=c.id,
            entity=AuditEntity.CAMPAIGN,
            entity_id=c.id,
            action=AuditAction.STOP,
            actor=actor.login,
        )
        return campaign_ref(c)
