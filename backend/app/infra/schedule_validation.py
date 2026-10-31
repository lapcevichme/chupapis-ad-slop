from datetime import date, datetime

from app.core.errors import ApiError, api_error


def check_schedule(
    start_date: date, start_time: str, end_date: date | None, end_time: str | None
) -> list[ApiError]:
    if (end_date is None) != (end_time is None):
        return [api_error("END_DATETIME_INCOMPLETE", "endDate" if end_date is None else "endTime")]
    if end_date is None or end_time is None:
        return []
    start = datetime.combine(start_date, datetime.strptime(start_time, "%H:%M").time())
    end = datetime.combine(end_date, datetime.strptime(end_time, "%H:%M").time())
    if end <= start:
        return [api_error("DATE_RANGE_INVALID", "endDate")]
    return []
