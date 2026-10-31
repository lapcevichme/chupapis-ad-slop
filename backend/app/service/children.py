from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts import campaigns as api
from app.core.errors import api_error, fail, not_found, raise_if
from app.db import models
from app.db.uow import UnitOfWork
from app.domain import views as dto
from app.domain.actors import Actor
from app.domain.enums import AuditAction, AuditEntity
from app.domain.lifecycle import mark_edited
from app.infra.creative_validation import check_banner, check_content
from app.service import audit
from app.service.common import editable_campaign
from app.service.mappers import banner, content, creative, snapshot


async def _child[T: (models.Banner, models.Content, models.Creative)](
    session: AsyncSession, model: type[T], campaign_id: int, child_id: int, field: str
) -> T:
    item = await session.get(model, child_id)
    if item is None or item.campaign_id != campaign_id:
        raise not_found(field, child_id)
    return item


def _record(
    session: AsyncSession,
    c: models.Campaign,
    entity: AuditEntity,
    entity_id: int,
    action: AuditAction,
    actor: Actor,
    changes: dict[str, Any] | None = None,
) -> None:
    audit.record(
        session,
        campaign_id=c.id,
        entity=entity,
        entity_id=entity_id,
        action=action,
        actor=actor.login,
        changes=changes,
    )


async def _banner_type(session: AsyncSession, banner_type_id: int) -> models.BannerType:
    t = await session.get(models.BannerType, banner_type_id)
    if t is None:
        raise not_found("bannerTypeId", banner_type_id)
    return t


async def _check_banner_body(session: AsyncSession, body: api.BannerCreate) -> models.BannerType:
    t = await _banner_type(session, body.bannerTypeId)
    raise_if(
        check_banner(
            body.content, type_code=t.code, title_max=t.title_max_length, text_max=t.text_max_length
        )
    )
    return t


def _banner_json(body: api.BannerCreate) -> dict[str, Any]:
    return body.content.model_dump(mode="json", exclude_none=True)


def _content_json(body: api.ContentCreate) -> dict[str, Any]:
    return body.content.model_dump(mode="json", exclude_none=True)


async def _check_creative(
    session: AsyncSession, c: models.Campaign, body: api.CreativeCreate, creative_id: int | None
) -> None:
    b = await _child(session, models.Banner, c.id, body.bannerId, "bannerId")
    if body.contentId is not None:
        await _child(session, models.Content, c.id, body.contentId, "contentId")
    if (
        await session.scalar(select(models.Channel).where(models.Channel.code == body.channelCode))
        is None
    ):
        raise not_found("channelCode", body.channelCode)
    if body.channelCode not in b.banner_type.channels:
        raise fail(
            "CHANNEL_NOT_ALLOWED",
            "channelCode",
            f"Канал {body.channelCode} не поддерживается типом {b.banner_type.code}; допустимы: {', '.join(b.banner_type.channels)}",
        )
    duplicate = await session.scalar(
        select(models.Creative.id).where(
            models.Creative.campaign_id == c.id,
            models.Creative.banner_id == body.bannerId,
            models.Creative.channel_code == body.channelCode,
            models.Creative.id != (creative_id or -1),
        )
    )
    if duplicate is not None:
        raise fail(
            "CREATIVE_DUPLICATE",
            "channelCode",
            f"Креатив {duplicate} уже связывает баннер {body.bannerId} с каналом {body.channelCode}",
        )


class CreativeService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def create_banner(
        self, campaign_id: int, body: api.BannerCreate, actor: Actor
    ) -> dto.BannerDto:
        session = self._uow.session
        c = await editable_campaign(session, actor, campaign_id)
        await _check_banner_body(session, body)
        b = models.Banner(
            campaign_id=c.id,
            name=body.name,
            banner_type_id=body.bannerTypeId,
            content=_banner_json(body),
        )
        session.add(b)
        mark_edited(c, actor.login)
        await session.flush()
        _record(session, c, AuditEntity.BANNER, b.id, AuditAction.CREATE, actor)
        return banner(b)

    async def update_banner(
        self, campaign_id: int, banner_id: int, body: api.BannerCreate, actor: Actor
    ) -> dto.BannerDto:
        session = self._uow.session
        c = await editable_campaign(session, actor, campaign_id)
        b = await _child(session, models.Banner, c.id, banner_id, "bannerId")
        t = await _check_banner_body(session, body)
        used = (
            await session.scalars(select(models.Creative).where(models.Creative.banner_id == b.id))
        ).all()
        raise_if(
            [
                api_error(
                    "CHANNEL_NOT_ALLOWED",
                    "bannerTypeId",
                    f"Креатив {cr.id} в канале {cr.channel_code} несовместим с типом {t.code}",
                )
                for cr in used
                if cr.channel_code not in t.channels
            ]
        )
        before = snapshot(banner(b))
        b.name, b.banner_type_id, b.content = (body.name, body.bannerTypeId, _banner_json(body))
        mark_edited(c, actor.login)
        await session.flush()
        await session.refresh(b)
        _record(
            session,
            c,
            AuditEntity.BANNER,
            b.id,
            AuditAction.UPDATE,
            actor,
            audit.diff(before, snapshot(banner(b))),
        )
        return banner(b)

    async def delete_banner(self, campaign_id: int, banner_id: int, actor: Actor) -> None:
        session = self._uow.session
        c = await editable_campaign(session, actor, campaign_id)
        b = await _child(session, models.Banner, c.id, banner_id, "bannerId")
        if await session.scalar(
            select(models.Creative.id).where(models.Creative.banner_id == b.id)
        ):
            raise fail("BANNER_IN_USE", "bannerId")
        c.banners.remove(b)
        mark_edited(c, actor.login)
        _record(session, c, AuditEntity.BANNER, banner_id, AuditAction.DELETE, actor)
        return None

    async def create_content(
        self, campaign_id: int, body: api.ContentCreate, actor: Actor
    ) -> dto.ContentDto:
        session = self._uow.session
        c = await editable_campaign(session, actor, campaign_id)
        raise_if(check_content(body.content))
        x = models.Content(
            campaign_id=c.id,
            name=body.name,
            content_type=body.contentType,
            content=_content_json(body),
        )
        session.add(x)
        mark_edited(c, actor.login)
        await session.flush()
        _record(session, c, AuditEntity.CONTENT, x.id, AuditAction.CREATE, actor)
        return content(x)

    async def update_content(
        self, campaign_id: int, content_id: int, body: api.ContentCreate, actor: Actor
    ) -> dto.ContentDto:
        session = self._uow.session
        c = await editable_campaign(session, actor, campaign_id)
        x = await _child(session, models.Content, c.id, content_id, "contentId")
        raise_if(check_content(body.content))
        before = snapshot(content(x))
        x.name, x.content_type, x.content = (body.name, body.contentType, _content_json(body))
        mark_edited(c, actor.login)
        await session.flush()
        _record(
            session,
            c,
            AuditEntity.CONTENT,
            x.id,
            AuditAction.UPDATE,
            actor,
            audit.diff(before, snapshot(content(x))),
        )
        return content(x)

    async def delete_content(self, campaign_id: int, content_id: int, actor: Actor) -> None:
        session = self._uow.session
        c = await editable_campaign(session, actor, campaign_id)
        x = await _child(session, models.Content, c.id, content_id, "contentId")
        if await session.scalar(
            select(models.Creative.id).where(models.Creative.content_id == x.id)
        ):
            raise fail("CONTENT_IN_USE", "contentId")
        c.contents.remove(x)
        mark_edited(c, actor.login)
        _record(session, c, AuditEntity.CONTENT, content_id, AuditAction.DELETE, actor)
        return None

    async def create_creative(
        self, campaign_id: int, body: api.CreativeCreate, actor: Actor
    ) -> dto.CreativeDto:
        session = self._uow.session
        c = await editable_campaign(session, actor, campaign_id)
        await _check_creative(session, c, body, None)
        cr = models.Creative(
            campaign_id=c.id,
            name=body.name,
            banner_id=body.bannerId,
            content_id=body.contentId,
            channel_code=body.channelCode,
        )
        session.add(cr)
        mark_edited(c, actor.login)
        await session.flush()
        _record(session, c, AuditEntity.CREATIVE, cr.id, AuditAction.CREATE, actor)
        return creative(cr)

    async def update_creative(
        self, campaign_id: int, creative_id: int, body: api.CreativeCreate, actor: Actor
    ) -> dto.CreativeDto:
        session = self._uow.session
        c = await editable_campaign(session, actor, campaign_id)
        cr = await _child(session, models.Creative, c.id, creative_id, "creativeId")
        await _check_creative(session, c, body, cr.id)
        before = snapshot(creative(cr))
        cr.name, cr.banner_id, cr.content_id, cr.channel_code = (
            body.name,
            body.bannerId,
            body.contentId,
            body.channelCode,
        )
        mark_edited(c, actor.login)
        await session.flush()
        _record(
            session,
            c,
            AuditEntity.CREATIVE,
            cr.id,
            AuditAction.UPDATE,
            actor,
            audit.diff(before, snapshot(creative(cr))),
        )
        return creative(cr)

    async def delete_creative(self, campaign_id: int, creative_id: int, actor: Actor) -> None:
        session = self._uow.session
        c = await editable_campaign(session, actor, campaign_id)
        cr = await _child(session, models.Creative, c.id, creative_id, "creativeId")
        c.creatives.remove(cr)
        mark_edited(c, actor.login)
        _record(session, c, AuditEntity.CREATIVE, creative_id, AuditAction.DELETE, actor)
        return None
