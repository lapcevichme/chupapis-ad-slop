"""Баннеры, контент и креативы кампании. Правка любой из них — правка кампании (§2.3)."""

from fastapi import APIRouter, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.domain import audit
from app.domain.creatives import check_banner, check_content
from app.domain.enums import AuditAction, AuditEntity
from app.domain.lifecycle import mark_edited
from app.errors import api_error, fail, not_found, raise_if
from app.routers.common import ERROR_RESPONSES, ActorDep, SessionDep, editable_campaign
from app.schemas import api
from app.serializers import banner, content, creative

router = APIRouter(prefix="/campaigns/{campaign_id}", tags=["creatives"], responses=ERROR_RESPONSES)


def _child[T](session: Session, model: type[T], campaign_id: int, child_id: int, field: str) -> T:
    item = session.get(model, child_id)
    if item is None or item.campaign_id != campaign_id:
        raise not_found(field, child_id)
    return item


def _record(session, c, entity, entity_id, action, actor, changes=None):
    audit.record(session, campaign_id=c.id, entity=entity, entity_id=entity_id, action=action, actor=actor.login, changes=changes)


# --- Баннеры


def _banner_type(session: Session, banner_type_id: int) -> models.BannerType:
    t = session.get(models.BannerType, banner_type_id)
    if t is None:
        raise not_found("bannerTypeId", banner_type_id)
    return t


def _check_banner_body(session: Session, body: api.BannerCreate) -> models.BannerType:
    t = _banner_type(session, body.bannerTypeId)
    raise_if(check_banner(body.content, type_code=t.code, title_max=t.title_max_length, text_max=t.text_max_length))
    return t


def _banner_json(body: api.BannerCreate) -> dict:
    return body.content.model_dump(mode="json", exclude_none=True)


@router.post("/banners", response_model=api.BannerDto, status_code=201)
def create_banner(campaign_id: int, body: api.BannerCreate, session: SessionDep, actor: ActorDep):
    c = editable_campaign(session, actor, campaign_id)
    _check_banner_body(session, body)
    b = models.Banner(campaign_id=c.id, name=body.name, banner_type_id=body.bannerTypeId, content=_banner_json(body))
    session.add(b)
    mark_edited(c, actor.login)
    session.flush()
    _record(session, c, AuditEntity.BANNER, b.id, AuditAction.CREATE, actor)
    session.commit()
    return banner(b)


@router.put("/banners/{banner_id}", response_model=api.BannerDto)
def update_banner(campaign_id: int, banner_id: int, body: api.BannerCreate, session: SessionDep, actor: ActorDep):
    c = editable_campaign(session, actor, campaign_id)
    b = _child(session, models.Banner, c.id, banner_id, "bannerId")
    t = _check_banner_body(session, body)
    used = session.scalars(select(models.Creative).where(models.Creative.banner_id == b.id)).all()
    raise_if(
        [
            api_error("CHANNEL_NOT_ALLOWED", "bannerTypeId", f"Креатив {cr.id} в канале {cr.channel_code} несовместим с типом {t.code}")
            for cr in used
            if cr.channel_code not in t.channels
        ]
    )
    before = banner(b).model_dump(mode="json")
    b.name, b.banner_type_id, b.content = body.name, body.bannerTypeId, _banner_json(body)
    mark_edited(c, actor.login)
    session.flush()
    session.refresh(b)
    _record(session, c, AuditEntity.BANNER, b.id, AuditAction.UPDATE, actor, audit.diff(before, banner(b).model_dump(mode="json")))
    session.commit()
    return banner(b)


@router.delete("/banners/{banner_id}", status_code=204)
def delete_banner(campaign_id: int, banner_id: int, session: SessionDep, actor: ActorDep):
    c = editable_campaign(session, actor, campaign_id)
    b = _child(session, models.Banner, c.id, banner_id, "bannerId")
    if session.scalar(select(models.Creative.id).where(models.Creative.banner_id == b.id)):
        raise fail("BANNER_IN_USE", "bannerId")
    c.banners.remove(b)
    mark_edited(c, actor.login)
    _record(session, c, AuditEntity.BANNER, banner_id, AuditAction.DELETE, actor)
    session.commit()
    return Response(status_code=204)


# --- Контент


def _content_json(body: api.ContentCreate) -> dict:
    return body.content.model_dump(mode="json", exclude_none=True)


@router.post("/contents", response_model=api.ContentDto, status_code=201)
def create_content(campaign_id: int, body: api.ContentCreate, session: SessionDep, actor: ActorDep):
    c = editable_campaign(session, actor, campaign_id)
    raise_if(check_content(body.content))
    x = models.Content(campaign_id=c.id, name=body.name, content_type=body.contentType, content=_content_json(body))
    session.add(x)
    mark_edited(c, actor.login)
    session.flush()
    _record(session, c, AuditEntity.CONTENT, x.id, AuditAction.CREATE, actor)
    session.commit()
    return content(x)


@router.put("/contents/{content_id}", response_model=api.ContentDto)
def update_content(campaign_id: int, content_id: int, body: api.ContentCreate, session: SessionDep, actor: ActorDep):
    c = editable_campaign(session, actor, campaign_id)
    x = _child(session, models.Content, c.id, content_id, "contentId")
    raise_if(check_content(body.content))
    before = content(x).model_dump(mode="json")
    x.name, x.content_type, x.content = body.name, body.contentType, _content_json(body)
    mark_edited(c, actor.login)
    session.flush()
    _record(session, c, AuditEntity.CONTENT, x.id, AuditAction.UPDATE, actor, audit.diff(before, content(x).model_dump(mode="json")))
    session.commit()
    return content(x)


@router.delete("/contents/{content_id}", status_code=204)
def delete_content(campaign_id: int, content_id: int, session: SessionDep, actor: ActorDep):
    c = editable_campaign(session, actor, campaign_id)
    x = _child(session, models.Content, c.id, content_id, "contentId")
    if session.scalar(select(models.Creative.id).where(models.Creative.content_id == x.id)):
        raise fail("CONTENT_IN_USE", "contentId")
    c.contents.remove(x)
    mark_edited(c, actor.login)
    _record(session, c, AuditEntity.CONTENT, content_id, AuditAction.DELETE, actor)
    session.commit()
    return Response(status_code=204)


# --- Креативы


def _check_creative(session: Session, c: models.Campaign, body: api.CreativeCreate, creative_id: int | None) -> None:
    b = _child(session, models.Banner, c.id, body.bannerId, "bannerId")
    if body.contentId is not None:
        _child(session, models.Content, c.id, body.contentId, "contentId")
    if session.scalar(select(models.Channel).where(models.Channel.code == body.channelCode)) is None:
        raise not_found("channelCode", body.channelCode)
    if body.channelCode not in b.banner_type.channels:
        raise fail(
            "CHANNEL_NOT_ALLOWED",
            "channelCode",
            f"Канал {body.channelCode} не поддерживается типом {b.banner_type.code}; допустимы: {', '.join(b.banner_type.channels)}",
        )
    duplicate = session.scalar(
        select(models.Creative.id).where(
            models.Creative.campaign_id == c.id,
            models.Creative.banner_id == body.bannerId,
            models.Creative.channel_code == body.channelCode,
            models.Creative.id != (creative_id or -1),
        )
    )
    if duplicate is not None:
        raise fail("CREATIVE_DUPLICATE", "channelCode", f"Креатив {duplicate} уже связывает баннер {body.bannerId} с каналом {body.channelCode}")


@router.post("/creatives", response_model=api.CreativeDto, status_code=201)
def create_creative(campaign_id: int, body: api.CreativeCreate, session: SessionDep, actor: ActorDep):
    c = editable_campaign(session, actor, campaign_id)
    _check_creative(session, c, body, None)
    cr = models.Creative(campaign_id=c.id, name=body.name, banner_id=body.bannerId, content_id=body.contentId, channel_code=body.channelCode)
    session.add(cr)
    mark_edited(c, actor.login)
    session.flush()
    _record(session, c, AuditEntity.CREATIVE, cr.id, AuditAction.CREATE, actor)
    session.commit()
    return creative(cr)


@router.put("/creatives/{creative_id}", response_model=api.CreativeDto)
def update_creative(campaign_id: int, creative_id: int, body: api.CreativeCreate, session: SessionDep, actor: ActorDep):
    c = editable_campaign(session, actor, campaign_id)
    cr = _child(session, models.Creative, c.id, creative_id, "creativeId")
    _check_creative(session, c, body, cr.id)
    before = creative(cr).model_dump(mode="json")
    cr.name, cr.banner_id, cr.content_id, cr.channel_code = body.name, body.bannerId, body.contentId, body.channelCode
    mark_edited(c, actor.login)
    session.flush()
    _record(session, c, AuditEntity.CREATIVE, cr.id, AuditAction.UPDATE, actor, audit.diff(before, creative(cr).model_dump(mode="json")))
    session.commit()
    return creative(cr)


@router.delete("/creatives/{creative_id}", status_code=204)
def delete_creative(campaign_id: int, creative_id: int, session: SessionDep, actor: ActorDep):
    c = editable_campaign(session, actor, campaign_id)
    cr = _child(session, models.Creative, c.id, creative_id, "creativeId")
    c.creatives.remove(cr)
    mark_edited(c, actor.login)
    _record(session, c, AuditEntity.CREATIVE, creative_id, AuditAction.DELETE, actor)
    session.commit()
    return Response(status_code=204)
