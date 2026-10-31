from sqlalchemy import select

from app.contracts import campaigns as api
from app.core.errors import fail
from app.db import models
from app.db.uow import UnitOfWork
from app.domain import views as dto
from app.domain.actors import Actor, require_role
from app.domain.enums import AuditAction, AuditEntity, PlaceState, Role, SegmentState, Topic
from app.service import audit
from app.service.mappers import banner_type, place


class DictionaryService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def list_topics(self) -> list[dto.TopicDto]:
        session = self._uow.session
        return [
            dto.TopicDto(value=Topic(t.value), label=t.label)
            for t in await session.scalars(select(models.Topic))
        ]

    async def list_tags(self) -> list[dto.TagDto]:
        session = self._uow.session
        return [
            dto.TagDto(id=t.id, name=t.name)
            for t in await session.scalars(select(models.Tag).order_by(models.Tag.id))
        ]

    async def list_channels(self) -> list[dto.ChannelDto]:
        session = self._uow.session
        rows = await session.scalars(select(models.Channel).order_by(models.Channel.id))
        return [dto.ChannelDto(id=c.id, code=c.code, description=c.description) for c in rows]

    async def list_banner_types(self) -> list[dto.BannerTypeDto]:
        session = self._uow.session
        return [
            banner_type(t)
            for t in await session.scalars(select(models.BannerType).order_by(models.BannerType.id))
        ]

    async def list_segment_types(self) -> list[dto.SegmentTypeDto]:
        session = self._uow.session
        return [
            dto.SegmentTypeDto(code=t.code, name=t.name)
            for t in await session.scalars(select(models.SegmentType))
        ]

    async def list_segments(self) -> list[dto.SegmentDto]:
        session = self._uow.session
        rows = await session.scalars(select(models.Segment))
        return [
            dto.SegmentDto(
                code=s.code, name=s.name, type=s.type, state=SegmentState(s.state), count=s.count
            )
            for s in rows
        ]

    async def list_places(self) -> list[dto.PlaceDto]:
        session = self._uow.session
        return [
            place(p) for p in await session.scalars(select(models.Place).order_by(models.Place.id))
        ]

    async def create_place(self, body: api.PlaceCreate, actor: Actor) -> dto.PlaceDto:
        session = self._uow.session
        require_role(actor, Role.MANAGER)
        if await session.scalar(select(models.Place).where(models.Place.code == body.code)):
            raise fail("PLACE_CODE_DUPLICATE", "code")
        p = models.Place(
            code=body.code,
            description=body.description,
            default_banner=None,
            state=PlaceState.ACTIVE,
        )
        session.add(p)
        await session.flush()
        audit.record(
            session,
            campaign_id=None,
            entity=AuditEntity.PLACE,
            entity_id=p.id,
            action=AuditAction.CREATE,
            actor=actor.login,
        )
        return place(p)

    async def create_tag(self, body: api.TagCreate, actor: Actor) -> dto.TagDto:
        session = self._uow.session
        require_role(actor, Role.MANAGER)
        if await session.scalar(select(models.Tag).where(models.Tag.name == body.name)):
            raise fail("TAG_NAME_DUPLICATE", "name")
        t = models.Tag(name=body.name)
        session.add(t)
        await session.flush()
        audit.record(
            session,
            campaign_id=None,
            entity=AuditEntity.TAG,
            entity_id=t.id,
            action=AuditAction.CREATE,
            actor=actor.login,
        )
        return dto.TagDto(id=t.id, name=t.name)
