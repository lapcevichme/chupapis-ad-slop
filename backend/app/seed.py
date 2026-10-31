"""Загрузка моков в пустую БД: `uv run python -m app.seed`. Повторный запуск ничего не меняет."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.core.config import BACKEND_DIR, Settings
from app.db import Database


def _load(name: str, seed_dir: Path) -> Any:
    return json.loads((seed_dir / f"{name}.json").read_text(encoding="utf-8"))


def seed(session: Session, seed_dir: Path = BACKEND_DIR / "seed") -> bool:
    if session.scalar(select(models.Topic.value).limit(1)) is not None:
        return False

    data = {name: _load(name, seed_dir) for name in [
        "topics", "tags", "channels", "banner_types", "segment_types", "segments", "places", "campaigns",
        "campaign_places", "campaign_segments", "campaign_banners", "campaign_contents", "campaign_creatives",
        "lifecycle_transitions",
    ]}  # fmt: skip

    session.add_all(models.Topic(**t) for t in data["topics"])
    session.add_all(models.Tag(**t) for t in data["tags"])
    session.add_all(models.Channel(**c) for c in data["channels"])
    session.add_all(
        models.BannerType(
            id=t["id"],
            code=t["code"],
            description=t["description"],
            preview_form=t["previewForm"],
            title_max_length=t["titleMaxLength"],
            text_max_length=t["textMaxLength"],
            channels=t["channels"],
        )
        for t in data["banner_types"]
    )
    session.add_all(models.SegmentType(**t) for t in data["segment_types"])
    # Без relationship-связей ORM не знает порядок вставки, поэтому родителей сбрасываем раньше детей.
    session.flush()
    session.add_all(models.Segment(**s) for s in data["segments"])
    session.add_all(
        models.Place(id=p["id"], code=p["code"], description=p["description"], default_banner=p["defaultBanner"], state=p["state"])
        for p in data["places"]
    )
    session.flush()

    places = {row["campaignId"]: row["placeIds"] for row in data["campaign_places"]}
    segments = {row["campaignId"]: row for row in data["campaign_segments"]}
    for c in data["campaigns"]:
        segment_row = segments.get(c["id"], {"included": [], "excluded": []})
        session.add(
            models.Campaign(
                id=c["id"],
                name=c["name"],
                marketing_name=c["marketingName"],
                start_date=date.fromisoformat(c["startDate"]),
                start_time=c["startTime"],
                end_date=date.fromisoformat(c["endDate"]) if c["endDate"] else None,
                end_time=c["endTime"],
                topic=c["topic"],
                keywords=c["keywords"],
                audience_type=c["audienceType"],
                weight=c["weight"],
                initial_ctr=c["initialCtr"],
                state=c["state"],
                published=c["published"],
                author=c["author"],
                last_edit_author=c["lastEditAuthor"],
                tag_links=[models.CampaignTag(tag_id=t, position=i) for i, t in enumerate(c["tags"])],
                place_links=[models.CampaignPlace(place_id=p, position=i) for i, p in enumerate(places.get(c["id"], []))],
                segment_links=[
                    models.CampaignSegment(segment_code=code, kind=kind, position=i)
                    for kind in ("included", "excluded")
                    for i, code in enumerate(segment_row[kind])
                ],
            )
        )
    session.flush()

    session.add_all(
        models.Banner(id=b["id"], campaign_id=b["campaignId"], name=b["name"], banner_type_id=b["bannerTypeId"], content=b["content"])
        for b in data["campaign_banners"]
    )
    session.add_all(
        models.Content(id=x["id"], campaign_id=x["campaignId"], name=x["name"], content_type=x["contentType"], content=x["content"])
        for x in data["campaign_contents"]
    )
    session.flush()
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
            at=datetime.fromisoformat(e["at"]),
            actor=e["actor"],
            comment=e["comment"],
        )
        for e in data["lifecycle_transitions"]
    )
    session.commit()
    # В PostgreSQL после вставки явных id нужно сдвинуть последовательности (setval); SQLite продолжает с max(id).
    return True


if __name__ == "__main__":
    settings = Settings()
    database = Database(settings)
    try:
        with database.sessions() as session:
            print("Моки загружены" if seed(session, settings.seed_dir) else "БД уже заполнена, сид пропущен")
    finally:
        database.dispose()
