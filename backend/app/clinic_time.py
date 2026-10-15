from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .config import settings


def clinic_zone() -> ZoneInfo:
    return ZoneInfo(settings.clinic_timezone)


def clinic_today() -> date:
    return datetime.now(clinic_zone()).date()


def day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    """Start and end (exclusive) of a clinic-local calendar day, expressed in UTC."""
    zone = clinic_zone()
    start = datetime.combine(day, time.min, tzinfo=zone)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone)
    return start.astimezone(UTC), end.astimezone(UTC)
