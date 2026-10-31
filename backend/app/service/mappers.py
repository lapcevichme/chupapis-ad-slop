from dataclasses import asdict
from datetime import date, datetime
from typing import Any, cast

from app.db import models
from app.domain import views as api
from app.domain.enums import CampaignState, PlaceState, Topic


def campaign_ref(c: models.Campaign) -> api.CampaignRef:
    return api.CampaignRef(
        id=c.id,
        state=CampaignState(c.state),
        published=c.published,
        author=c.author,
        lastEditAuthor=c.last_edit_author,
    )


def campaign_list_item(c: models.Campaign) -> api.CampaignListItem:
    return api.CampaignListItem(
        id=c.id,
        name=c.name,
        state=CampaignState(c.state),
        published=c.published,
        topic=Topic(c.topic),
        startDate=c.start_date,
        startTime=c.start_time,
        endDate=c.end_date,
        endTime=c.end_time,
    )


def campaign_header(c: models.Campaign) -> dict[str, Any]:
    return dict(
        id=c.id,
        name=c.name,
        marketingName=c.marketing_name,
        startDate=c.start_date,
        startTime=c.start_time,
        endDate=c.end_date,
        endTime=c.end_time,
        topic=Topic(c.topic),
        tags=c.tag_ids,
        keywords=c.keywords,
        state=CampaignState(c.state),
        published=c.published,
        audienceType=c.audience_type,
        weight=c.weight,
        initialCtr=c.initial_ctr,
        author=c.author,
        lastEditAuthor=c.last_edit_author,
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
    return api.Segments(included=c.segment_codes("included"), excluded=c.segment_codes("excluded"))


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
        actor=e.actor,
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
