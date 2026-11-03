from dataclasses import asdict
from datetime import UTC, date, datetime, time
from typing import Any, cast

from app.db import models
from app.domain import views as api
from app.domain.enums import CampaignState, PlaceState, SegmentKind, Topic
from app.domain.users import UserProfile


def split_moment(moment: datetime | None) -> tuple[date | None, str | None]:
    """Момент в UTC → пара «дата, HH:mm», как её отдаёт и принимает API кампаний."""
    if moment is None:
        return None, None
    utc = moment.astimezone(UTC)
    return utc.date(), utc.strftime("%H:%M")


def join_moment(day: date, hhmm: str) -> datetime:
    hours, minutes = hhmm.split(":")
    return datetime.combine(day, time(int(hours), int(minutes)), tzinfo=UTC)


def campaign_ref(c: models.Campaign) -> api.CampaignRef:
    return api.CampaignRef(
        id=c.id,
        state=CampaignState(c.state),
        published=c.published,
        author=c.author.username,
        lastEditAuthor=c.last_editor.username,
    )


def campaign_list_item(c: models.Campaign) -> api.CampaignListItem:
    start_date, start_time = split_moment(c.start_at)
    end_date, end_time = split_moment(c.end_at)
    assert start_date is not None and start_time is not None
    return api.CampaignListItem(
        id=c.id,
        name=c.name,
        state=CampaignState(c.state),
        published=c.published,
        topic=Topic(c.topic),
        startDate=start_date,
        startTime=start_time,
        endDate=end_date,
        endTime=end_time,
    )


def campaign_header(c: models.Campaign) -> dict[str, Any]:
    start_date, start_time = split_moment(c.start_at)
    end_date, end_time = split_moment(c.end_at)
    return dict(
        id=c.id,
        name=c.name,
        marketingName=c.marketing_name,
        startDate=start_date,
        startTime=start_time,
        endDate=end_date,
        endTime=end_time,
        topic=Topic(c.topic),
        tags=c.tag_ids,
        keywords=c.keywords,
        state=CampaignState(c.state),
        published=c.published,
        audienceType=c.audience_type,
        weight=c.weight,
        initialCtr=c.initial_ctr,
        author=c.author.username,
        lastEditAuthor=c.last_editor.username,
    )


def banner(b: models.Banner) -> api.BannerDto:
    return api.BannerDto(
        id=b.id,
        campaignId=b.campaign_id,
        name=b.name,
        bannerTypeId=b.banner_type_id,
        content=b.content,
    )


def content(c: models.Content) -> api.ContentDto:
    return api.ContentDto(
        id=c.id,
        campaignId=c.campaign_id,
        name=c.name,
        contentType=c.content_type,
        content=c.content,
    )


def creative(c: models.Creative) -> api.CreativeDto:
    return api.CreativeDto(
        id=c.id,
        campaignId=c.campaign_id,
        name=c.name,
        bannerId=c.banner_id,
        contentId=c.content_id,
        channelCode=c.channel_code,
    )


def segments(c: models.Campaign) -> api.Segments:
    return api.Segments(
        included=c.segment_codes(SegmentKind.INCLUDED),
        excluded=c.segment_codes(SegmentKind.EXCLUDED),
    )


def campaign_details(c: models.Campaign) -> api.CampaignDetails:
    return api.CampaignDetails(
        **campaign_header(c),
        places=c.place_ids,
        segments=segments(c),
        banners=[banner(b) for b in c.banners],
        contents=[content(x) for x in c.contents],
        creatives=[creative(x) for x in c.creatives],
    )


def audit_record(e: models.AuditEntry) -> api.AuditRecord:
    return api.AuditRecord(
        entity=e.entity,
        entityId=e.entity_id,
        action=e.action,
        changes=e.changes,
        at=e.at,
        actor=e.actor.username,
        comment=e.comment,
    )


def place(p: models.Place) -> api.PlaceDto:
    return api.PlaceDto(
        id=p.id,
        code=p.code,
        description=p.description,
        defaultBanner=p.default_banner,
        state=PlaceState(p.state),
    )


def banner_type(t: models.BannerType) -> api.BannerTypeDto:
    return api.BannerTypeDto(
        id=t.id,
        code=t.code,
        description=t.description,
        previewForm=t.preview_form,
        titleMaxLength=t.title_max_length,
        textMaxLength=t.text_max_length,
        channels=t.channels,
    )


def snapshot(value: Any) -> dict[str, Any]:
    def json_value(item: Any) -> Any:
        if isinstance(item, (date, datetime)):
            return item.isoformat()
        if isinstance(item, dict):
            return {key: json_value(value) for key, value in item.items()}
        if isinstance(item, list):
            return [json_value(value) for value in item]
        return item

    return cast(dict[str, Any], json_value(asdict(value)))


def to_profile(user: models.User) -> UserProfile:
    return UserProfile(
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role,
        is_banned=user.banned_at is not None,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
