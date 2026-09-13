from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    return datetime.now(UTC)


def business_date(timezone: str, now: datetime | None = None) -> date:
    return (now or utcnow()).astimezone(ZoneInfo(timezone)).date()
