import json
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.passwords import hash_password
from app.db import models
from app.domain.enums import Role, SegmentKind

# Таблицы, где сид задаёт id явно: после него последовательности нужно сдвинуть.
SEQUENCED_TABLES = (
    "tags",
    "places",
    "channels",
    "banner_types",
    "campaigns",
    "banners",
    "contents",
    "creatives",
)

DEMO_USERS = (
    ("ivanov.p", "ivanov.p@example.com", Role.MANAGER),
    ("petrova.m", "petrova.m@example.com", Role.MODERATOR),
)


def _load(name: str, seed_dir: Path) -> Any:
    return json.loads((seed_dir / f"{name}.json").read_text(encoding="utf-8"))


def _moment(day: str, hhmm: str) -> datetime:
    hours, minutes = hhmm.split(":")
    return datetime.combine(date.fromisoformat(day), time(int(hours), int(minutes)), tzinfo=UTC)


async def seed_dictionaries(session: AsyncSession, seed_dir: Path) -> bool:
    """Справочники нужны любому окружению. Повторный запуск ничего не меняет."""
    if await session.scalar(select(models.Topic.value).limit(1)) is not None:
        return False
    data = {
        name: _load(name, seed_dir)
        for name in ["topics", "tags", "channels", "banner_types", "segment_types", "segments", "places"]
    }  # fmt: skip
    session.add_all(models.Topic(**t) for t in data["topics"])
    session.add_all(models.Tag(**t) for t in data["tags"])
    session.add_all(models.Channel(**c) for c in data["channels"])
    session.add_all(models.SegmentType(**t) for t in data["segment_types"])
    session.add_all(
        models.BannerType(
            id=t["id"],
            code=t["code"],
            description=t["description"],
            preview_form=t["previewForm"],
            title_max_length=t["titleMaxLength"],
            text_max_length=t["textMaxLength"],
            channel_links=[
                models.BannerTypeChannel(channel_code=code, position=i)
                for i, code in enumerate(t["channels"])
            ],
        )
        for t in data["banner_types"]
    )
    await session.flush()
    session.add_all(models.Segment(**s) for s in data["segments"])
    session.add_all(
        models.Place(
            id=p["id"],
            code=p["code"],
            description=p["description"],
            default_banner=p["defaultBanner"],
            state=p["state"],
        )
        for p in data["places"]
    )
    await session.flush()
    await _advance_sequences(session)
    return True


async def seed_demo_users(session: AsyncSession, password: str) -> dict[str, models.User]:
    """Менеджер и модератор из кейса. Пароль задаёт оператор, в коде его нет."""
    users: dict[str, models.User] = {}
    for username, email, role in DEMO_USERS:
        user = await session.scalar(
            select(models.User).where(func.lower(models.User.username) == username)
        )
        if user is None:
            user = models.User(
                email=email,
                username=username,
                password_hash=await hash_password(password),
                role=role,
            )
            session.add(user)
        users[username] = user
    await session.flush()
    return users


async def seed_demo_campaigns(
    session: AsyncSession, seed_dir: Path, users: dict[str, models.User]
) -> bool:
    if await session.scalar(select(models.Campaign.id).limit(1)) is not None:
        return False
    data = {
        name: _load(name, seed_dir)
        for name in [
            "campaigns", "campaign_places", "campaign_segments", "campaign_banners",
            "campaign_contents", "campaign_creatives", "lifecycle_transitions",
        ]
    }  # fmt: skip
    places = {row["campaignId"]: row["placeIds"] for row in data["campaign_places"]}
    segments = {row["campaignId"]: row for row in data["campaign_segments"]}
    for c in data["campaigns"]:
        segment_row = segments.get(c["id"], {"included": [], "excluded": []})
        end = _moment(c["endDate"], c["endTime"]) if c["endDate"] else None
        session.add(
            models.Campaign(
                id=c["id"],
                name=c["name"],
                marketing_name=c["marketingName"],
                start_at=_moment(c["startDate"], c["startTime"]),
                end_at=end,
                topic=c["topic"],
                keywords=c["keywords"],
                audience_type=c["audienceType"],
                weight=c["weight"],
                initial_ctr=c["initialCtr"],
                state=c["state"],
                published=c["published"],
                author_id=users[c["author"]].id,
                last_editor_id=users[c["lastEditAuthor"]].id,
                tag_links=[
                    models.CampaignTag(tag_id=t, position=i) for i, t in enumerate(c["tags"])
                ],
                place_links=[
                    models.CampaignPlace(place_id=p, position=i)
                    for i, p in enumerate(places.get(c["id"], []))
                ],
                segment_links=[
                    models.CampaignSegment(segment_code=code, kind=kind, position=i)
                    for kind in (SegmentKind.INCLUDED, SegmentKind.EXCLUDED)
                    for i, code in enumerate(segment_row[kind.value])
                ],
            )
        )
    await session.flush()
    session.add_all(
        models.Banner(
            id=b["id"],
            campaign_id=b["campaignId"],
            name=b["name"],
            banner_type_id=b["bannerTypeId"],
            content=b["content"],
        )
        for b in data["campaign_banners"]
    )
    session.add_all(
        models.Content(
            id=x["id"],
            campaign_id=x["campaignId"],
            name=x["name"],
            content_type=x["contentType"],
            content=x["content"],
        )
        for x in data["campaign_contents"]
    )
    await session.flush()
    session.add_all(
        models.Creative(
            id=cr["id"],
            campaign_id=cr["campaignId"],
            name=cr["name"],
            banner_id=cr["bannerId"],
            content_id=cr["contentId"],
            channel_code=cr["channelCode"],
        )
        for cr in data["campaign_creatives"]
    )
    session.add_all(
        models.AuditEntry(
            campaign_id=e["campaignId"],
            entity=e["entity"],
            entity_id=e["entityId"],
            action=e["action"],
            changes=e["changes"],
            at=datetime.fromisoformat(e["at"]).replace(tzinfo=UTC),
            actor_id=users[e["actor"]].id,
            comment=e["comment"],
        )
        for e in data["lifecycle_transitions"]
    )
    await session.flush()
    await _advance_sequences(session)
    return True


async def _advance_sequences(session: AsyncSession) -> None:
    for table in SEQUENCED_TABLES:
        await session.execute(
            text(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "  # noqa: S608 - имена таблиц из константы
                f"COALESCE((SELECT MAX(id) FROM {table}), 1), (SELECT COUNT(*) > 0 FROM {table}))"
            )
        )


async def seed(session: AsyncSession, seed_dir: Path, *, demo_password: str | None = None) -> bool:
    """Справочники всегда; демо-пользователи и демо-кампании только если задан пароль."""
    changed = await seed_dictionaries(session, seed_dir)
    if demo_password:
        users = await seed_demo_users(session, demo_password)
        changed = await seed_demo_campaigns(session, seed_dir, users) or changed
    return changed
