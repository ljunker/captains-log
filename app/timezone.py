from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.config import settings


APP_TIMEZONE = ZoneInfo(settings.timezone_name)


def assume_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def input_datetime_to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=APP_TIMEZONE).astimezone(UTC)
    return value.astimezone(UTC)


def to_app_timezone(value: datetime) -> datetime:
    return assume_utc(value).astimezone(APP_TIMEZONE)


def local_date(value: datetime) -> date:
    return to_app_timezone(value).date()
