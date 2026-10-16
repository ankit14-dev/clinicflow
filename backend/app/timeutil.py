from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .config import settings


def as_utc(value: datetime) -> datetime:
    """Normalise to an aware UTC datetime. Naive values are treated as UTC.

    PostgreSQL returns aware datetimes; SQLite (used for quick local tests) returns naive ones.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def clinic_tz() -> ZoneInfo:
    return ZoneInfo(settings.clinic_timezone)


def clinic_today() -> date:
    return datetime.now(clinic_tz()).date()


def clinic_day_bounds(day: date) -> tuple[datetime, datetime]:
    """[start, end) of a calendar day at the clinic, expressed in UTC."""
    start = datetime.combine(day, time.min, tzinfo=clinic_tz())
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)
