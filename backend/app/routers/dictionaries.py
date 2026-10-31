from fastapi import APIRouter
from sqlalchemy import select

from app import models
from app.actor import require_role
from app.domain import audit
from app.domain.enums import AuditAction, AuditEntity, PlaceState, Role
from app.errors import fail
from app.routers.common import ERROR_RESPONSES, ActorDep, SessionDep
from app.schemas import api
from app.serializers import banner_type, place

router = APIRouter(tags=["dictionaries"], responses=ERROR_RESPONSES)


@router.get("/topics", response_model=list[api.TopicDto])
def list_topics(session: SessionDep):
    return [api.TopicDto(value=t.value, label=t.label) for t in session.scalars(select(models.Topic))]


@router.get("/tags", response_model=list[api.TagDto])
def list_tags(session: SessionDep):
    return [api.TagDto(id=t.id, name=t.name) for t in session.scalars(select(models.Tag).order_by(models.Tag.id))]


@router.get("/channels", response_model=list[api.ChannelDto])
def list_channels(session: SessionDep):
    rows = session.scalars(select(models.Channel).order_by(models.Channel.id))
    return [api.ChannelDto(id=c.id, code=c.code, description=c.description) for c in rows]


@router.get("/banner-types", response_model=list[api.BannerTypeDto])
def list_banner_types(session: SessionDep):
    return [banner_type(t) for t in session.scalars(select(models.BannerType).order_by(models.BannerType.id))]


@router.get("/segment-types", response_model=list[api.SegmentTypeDto])
def list_segment_types(session: SessionDep):
    return [api.SegmentTypeDto(code=t.code, name=t.name) for t in session.scalars(select(models.SegmentType))]


@router.get("/segments", response_model=list[api.SegmentDto])
def list_segments(session: SessionDep):
    rows = session.scalars(select(models.Segment))
    return [api.SegmentDto(code=s.code, name=s.name, type=s.type, state=s.state, count=s.count) for s in rows]


@router.get("/places", response_model=list[api.PlaceDto])
def list_places(session: SessionDep):
    return [place(p) for p in session.scalars(select(models.Place).order_by(models.Place.id))]


@router.post("/places", response_model=api.PlaceDto, status_code=201)
def create_place(body: api.PlaceCreate, session: SessionDep, actor: ActorDep):
    require_role(actor, Role.MANAGER)
    if session.scalar(select(models.Place).where(models.Place.code == body.code)):
        raise fail("PLACE_CODE_DUPLICATE", "code")
    # defaultBanner у созданных мест не задаётся, правило PLACE_NO_CREATIVE к ним не применяется (§2.5).
    p = models.Place(code=body.code, description=body.description, default_banner=None, state=PlaceState.ACTIVE)
    session.add(p)
    session.flush()
    audit.record(session, campaign_id=None, entity=AuditEntity.PLACE, entity_id=p.id, action=AuditAction.CREATE, actor=actor.login)
    session.commit()
    return place(p)


@router.post("/tags", response_model=api.TagDto, status_code=201)
def create_tag(body: api.TagCreate, session: SessionDep, actor: ActorDep):
    require_role(actor, Role.MANAGER)
    if session.scalar(select(models.Tag).where(models.Tag.name == body.name)):
        raise fail("TAG_NAME_DUPLICATE", "name")
    t = models.Tag(name=body.name)
    session.add(t)
    session.flush()
    audit.record(session, campaign_id=None, entity=AuditEntity.TAG, entity_id=t.id, action=AuditAction.CREATE, actor=actor.login)
    session.commit()
    return api.TagDto(id=t.id, name=t.name)
