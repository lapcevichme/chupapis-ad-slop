from fastapi import APIRouter, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.actor import Actor, require_role
from app.domain import audit
from app.domain.enums import AudienceType, AuditAction, AuditEntity, CampaignState, Role
from app.domain.lifecycle import TRANSITIONS, ensure_deletable, ensure_stoppable, ensure_transition, mark_edited
from app.domain.validation import campaign_errors, campaign_warnings, check_schedule, check_segment_codes
from app.errors import api_error, fail, not_found, raise_if
from app.routers.cbro import export_campaign
from app.routers.common import ERROR_RESPONSES, ActorDep, SessionDep, editable_campaign, get_campaign, info_snapshot
from app.schemas import api
from app.serializers import audit_record, campaign_details, campaign_list_item, campaign_ref, segments

router = APIRouter(prefix="/campaigns", tags=["campaigns"], responses=ERROR_RESPONSES)


def _unique(values: list) -> list:
    return list(dict.fromkeys(values))


def _apply_info(session: Session, c: models.Campaign, body: api.CampaignInfo) -> None:
    for index, ref in enumerate(body.tags):
        if session.get(models.Tag, ref.value) is None:
            raise not_found(f"tags[{index}].value", ref.value)
    for index, ref in enumerate(body.places):
        if session.get(models.Place, ref.value) is None:
            raise not_found(f"places[{index}].value", ref.value)

    errors = check_schedule(body.startDate, body.startTime, body.endDate, body.endTime)
    duplicate = session.scalar(select(models.Campaign.id).where(models.Campaign.name == body.name, models.Campaign.id != c.id))
    if duplicate is not None:
        errors.append(api_error("NAME_DUPLICATE", "name", f"Кампания «{body.name}» уже существует (id {duplicate})"))
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
    c.start_date, c.start_time = body.startDate, body.startTime
    c.end_date, c.end_time = body.endDate, body.endTime
    c.topic = body.topic.value
    c.keywords = body.keywords
    c.audience_type = body.audienceType
    c.weight = body.weight
    c.initial_ctr = body.initialCtr
    c.tag_links = [models.CampaignTag(tag_id=t, position=i) for i, t in enumerate(_unique([r.value for r in body.tags]))]
    c.place_links = [
        models.CampaignPlace(place_id=p, position=i, place=session.get(models.Place, p))
        for i, p in enumerate(_unique([r.value for r in body.places]))
    ]


@router.get("", response_model=list[api.CampaignListItem])
def list_campaigns(session: SessionDep):
    return [campaign_list_item(c) for c in session.scalars(select(models.Campaign).order_by(models.Campaign.id))]


@router.get("/{campaign_id}", response_model=api.CampaignDetails)
def get_campaign_details(campaign_id: int, session: SessionDep):
    return campaign_details(get_campaign(session, campaign_id))


@router.post("", response_model=api.CampaignRef, status_code=201)
def create_campaign(body: api.CampaignInfo, session: SessionDep, actor: ActorDep):
    require_role(actor, Role.MANAGER)
    c = models.Campaign(state=CampaignState.DRAFT, published=False, author=actor.login, last_edit_author=actor.login)
    _apply_info(session, c, body)
    session.add(c)
    session.flush()
    audit.record(session, campaign_id=c.id, entity=AuditEntity.CAMPAIGN, entity_id=c.id, action=AuditAction.CREATE, actor=actor.login)
    session.commit()
    return campaign_ref(c)


@router.put("/{campaign_id}", response_model=api.CampaignRef)
def update_campaign(campaign_id: int, body: api.CampaignInfo, session: SessionDep, actor: ActorDep):
    c = editable_campaign(session, actor, campaign_id)
    before = info_snapshot(c)
    _apply_info(session, c, body)
    mark_edited(c, actor.login)
    session.flush()
    audit.record(
        session,
        campaign_id=c.id,
        entity=AuditEntity.CAMPAIGN,
        entity_id=c.id,
        action=AuditAction.UPDATE,
        actor=actor.login,
        changes=audit.diff(before, info_snapshot(c)),
    )
    session.commit()
    return campaign_ref(c)


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: int, session: SessionDep, actor: ActorDep):
    require_role(actor, Role.MANAGER)
    c = get_campaign(session, campaign_id)
    ensure_deletable(c)
    audit.record(session, campaign_id=c.id, entity=AuditEntity.CAMPAIGN, entity_id=c.id, action=AuditAction.DELETE, actor=actor.login)
    session.delete(c)
    session.commit()
    return Response(status_code=204)


@router.put("/{campaign_id}/segments", response_model=api.Segments)
def set_segments(campaign_id: int, body: api.Segments, session: SessionDep, actor: ActorDep):
    c = editable_campaign(session, actor, campaign_id)
    included, excluded = _unique(body.included), _unique(body.excluded)

    errors = []
    if c.audience_type == AudienceType.ALL_USERS and (included or excluded):
        errors.append(api_error("SEGMENTS_FORBIDDEN_FOR_ALL_USERS", "included" if included else "excluded"))
    errors += check_segment_codes(session, included, "included")
    errors += check_segment_codes(session, excluded, "excluded")
    for code in set(included) & set(excluded):
        errors.append(api_error("SEGMENT_INCLUDED_AND_EXCLUDED", "excluded", f"Сегмент {code} одновременно включён и исключён"))
    raise_if(errors)

    before = segments(c).model_dump()
    c.segment_links = [
        models.CampaignSegment(segment_code=code, kind=kind, position=i)
        for kind, codes in (("included", included), ("excluded", excluded))
        for i, code in enumerate(codes)
    ]
    mark_edited(c, actor.login)
    session.flush()
    after = segments(c).model_dump()
    audit.record(
        session,
        campaign_id=c.id,
        entity=AuditEntity.SEGMENTS,
        entity_id=c.id,
        action=AuditAction.UPDATE,
        actor=actor.login,
        changes=audit.diff(before, after),
    )
    session.commit()
    return after


@router.get("/{campaign_id}/warnings", response_model=api.ValidationReport)
def get_warnings(campaign_id: int, session: SessionDep):
    c = get_campaign(session, campaign_id)
    return api.ValidationReport(errors=campaign_errors(session, c), warnings=campaign_warnings(c))


@router.get("/{campaign_id}/audit", response_model=list[api.AuditRecord])
def get_audit(campaign_id: int, session: SessionDep):
    get_campaign(session, campaign_id)
    rows = session.scalars(
        select(models.AuditEntry).where(models.AuditEntry.campaign_id == campaign_id).order_by(models.AuditEntry.at, models.AuditEntry.id)
    )
    return [audit_record(e) for e in rows]


def _transition(session: Session, actor: Actor, campaign_id: int, action: AuditAction, comment: str | None = None) -> models.Campaign:
    require_role(actor, TRANSITIONS[action].role)
    c = get_campaign(session, campaign_id)
    transition = ensure_transition(c, action)
    if action == AuditAction.DECLINE and not (comment or "").strip():
        raise fail("DECLINE_COMMENT_REQUIRED", "comment")
    if action == AuditAction.TO_MODERATION:
        raise_if(campaign_errors(session, c))
    if action == AuditAction.ACTIVATE:
        export_campaign(c.id)
        c.published = True
    c.state = transition.to_state
    audit.record(session, campaign_id=c.id, entity=AuditEntity.CAMPAIGN, entity_id=c.id, action=action, actor=actor.login, comment=comment)
    session.commit()
    return c


@router.post("/{campaign_id}/to-moderation", response_model=api.CampaignRef)
def send_to_moderation(campaign_id: int, session: SessionDep, actor: ActorDep):
    return campaign_ref(_transition(session, actor, campaign_id, AuditAction.TO_MODERATION))


@router.post("/{campaign_id}/decline", response_model=api.CampaignRef)
def decline_campaign(campaign_id: int, body: api.DeclineBody, session: SessionDep, actor: ActorDep):
    return campaign_ref(_transition(session, actor, campaign_id, AuditAction.DECLINE, comment=body.comment))


@router.post("/{campaign_id}/approve", response_model=api.CampaignRef)
def approve_campaign(campaign_id: int, session: SessionDep, actor: ActorDep):
    return campaign_ref(_transition(session, actor, campaign_id, AuditAction.APPROVE))


@router.post("/{campaign_id}/activate", response_model=api.CampaignRef)
def activate_campaign(campaign_id: int, session: SessionDep, actor: ActorDep):
    return campaign_ref(_transition(session, actor, campaign_id, AuditAction.ACTIVATE))


@router.post("/{campaign_id}/stop", response_model=api.CampaignRef)
def stop_campaign(campaign_id: int, session: SessionDep, actor: ActorDep):
    require_role(actor, Role.MANAGER)
    c = get_campaign(session, campaign_id)
    ensure_stoppable(c)
    c.state = CampaignState.STOPPED
    c.published = False
    audit.record(session, campaign_id=c.id, entity=AuditEntity.CAMPAIGN, entity_id=c.id, action=AuditAction.STOP, actor=actor.login)
    session.commit()
    return campaign_ref(c)
