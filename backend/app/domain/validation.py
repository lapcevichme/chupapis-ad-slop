"""Прогон валидации всей кампании (§4): GET /warnings и проверка перед to-moderation."""

from datetime import datetime

from sqlalchemy.orm import Session

from app import models
from app.domain.creatives import validate_banner_json, validate_content_json
from app.domain.enums import AudienceType, PlaceState, SegmentState
from app.domain.rules import WARNINGS
from app.errors import ApiError, api_error


def check_schedule(start_date, start_time, end_date, end_time) -> list[ApiError]:
    if (end_date is None) != (end_time is None):
        return [api_error("END_DATETIME_INCOMPLETE", "endDate" if end_date is None else "endTime")]
    if end_date is None:
        return []
    start = datetime.combine(start_date, datetime.strptime(start_time, "%H:%M").time())
    end = datetime.combine(end_date, datetime.strptime(end_time, "%H:%M").time())
    if end <= start:
        return [api_error("DATE_RANGE_INVALID", "endDate")]
    return []


def check_segment_codes(session: Session, codes: list[str], field: str) -> list[ApiError]:
    errors: list[ApiError] = []
    for index, code in enumerate(codes):
        segment = session.get(models.Segment, code)
        if segment is None:
            errors.append(api_error("SEGMENT_NOT_FOUND", f"{field}[{index}]", f"Сегмента {code} нет в справочнике"))
        elif segment.state != SegmentState.ACTIVE:
            errors.append(
                api_error(
                    "SEGMENT_NOT_ACTIVE",
                    f"{field}[{index}]",
                    f"Сегмент {code} в состоянии {segment.state}: в нём {segment.count} клиентов, выбрать его нельзя",
                )
            )
    return errors


def campaign_errors(session: Session, c: models.Campaign) -> list[ApiError]:
    errors = check_schedule(c.start_date, c.start_time, c.end_date, c.end_time)

    included, excluded = c.segment_codes("included"), c.segment_codes("excluded")
    if c.audience_type == AudienceType.SEGMENTED and not included:
        errors.append(api_error("SEGMENTS_REQUIRED", "segments.included"))
    if c.audience_type == AudienceType.ALL_USERS and (included or excluded):
        errors.append(api_error("SEGMENTS_FORBIDDEN_FOR_ALL_USERS", "segments"))
    errors += check_segment_codes(session, included, "segments.included")
    errors += check_segment_codes(session, excluded, "segments.excluded")

    if not c.place_links:
        errors.append(api_error("PLACES_REQUIRED", "places"))

    for b in c.banners:
        t = b.banner_type
        _, banner_errors = validate_banner_json(
            b.content,
            type_code=t.code,
            title_max=t.title_max_length,
            text_max=t.text_max_length,
            prefix=f"banners[{b.id}].content",
        )
        errors += banner_errors
    for x in c.contents:
        _, content_errors = validate_content_json(x.content, prefix=f"contents[{x.id}].content")
        errors += content_errors
    for cr in c.creatives:
        if cr.channel_code not in cr.banner.banner_type.channels:
            errors.append(
                api_error(
                    "CHANNEL_NOT_ALLOWED",
                    f"creatives[{cr.id}].channelCode",
                    f"Канал {cr.channel_code} не поддерживается типом {cr.banner.banner_type.code}",
                )
            )
    return errors


def place_covered(place: models.Place, creatives: list[models.Creative]) -> bool:
    """§7.2 mock-data: место покрыто, если есть креатив с баннером типа place.defaultBanner."""
    if place.default_banner is None:
        return True
    return any(cr.banner.banner_type.code == place.default_banner for cr in creatives)


def campaign_warning_codes(c: models.Campaign) -> list[str]:
    places = [link.place for link in c.place_links]
    codes: list[str] = []
    if not all(place_covered(p, c.creatives) for p in places):
        codes.append("PLACE_NO_CREATIVE")
    if any(p.state == PlaceState.INACTIVE for p in places):
        codes.append("PLACE_INACTIVE")
    if not c.tag_links:
        codes.append("TAGS_MISSING")
    return codes


def campaign_warnings(c: models.Campaign) -> list[str]:
    return [WARNINGS[code] for code in campaign_warning_codes(c)]
