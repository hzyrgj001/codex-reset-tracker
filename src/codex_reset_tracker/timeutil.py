"""Time helpers. All stored timestamps are UTC ISO-8601 with a trailing 'Z'."""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
TAIPEI = ZoneInfo("Asia/Taipei")
PACIFIC = ZoneInfo("America/Los_Angeles")

# Tibo's "28 days" series: announced 2026-10-04 (PT); Day 1 is 2026-10-05 PT.
CAMPAIGN_DAY0 = date(2026, 10, 4)
CAMPAIGN_LENGTH = 28


def parse_ts(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def fmt_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def fmt_tpe(dt: datetime) -> str:
    return dt.astimezone(TAIPEI).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def campaign_day(dt: datetime) -> int | None:
    """Day N of the 28-day series, using the Pacific calendar date. None outside it."""
    n = (dt.astimezone(PACIFIC).date() - CAMPAIGN_DAY0).days
    return n if 1 <= n <= CAMPAIGN_LENGTH else None


def now_utc() -> datetime:
    return datetime.now(UTC)
