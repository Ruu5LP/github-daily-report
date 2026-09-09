"""Time helpers for the report's business timezone."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


def to_jst_date(value: datetime) -> date:
    """Return the calendar date of an aware datetime in Japan Standard Time."""
    return value.astimezone(JST).date()
