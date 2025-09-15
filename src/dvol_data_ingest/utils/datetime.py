"""UTC datetime utilities.

Implements T025: UTC normalization helpers
- Unix ms → UTC datetime
- ISO date/datetime parsing
- Timezone validation/normalization
- 00:00 UTC cut-off enforcement
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime, time

UTC = UTC


def unix_ms_to_utc(ms: int | str) -> datetime:
    """Convert Unix milliseconds to a timezone-aware UTC datetime.

    Accepts ints or numeric strings. Raises ValueError for negatives.
    """
    iv = int(ms)
    if iv < 0:
        raise ValueError("unix milliseconds must be non-negative")
    return datetime.fromtimestamp(iv / 1000.0, tz=UTC)


def parse_iso_date(s: str) -> date:
    """Parse date in YYYY-MM-DD format to a date object."""
    return datetime.strptime(s, "%Y-%m-%d").date()


def parse_iso_datetime_utc(s: str) -> datetime:
    """Parse datetime in 'YYYY-MM-DD HH:MM:SS' and set tz=UTC."""
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    return dt.replace(tzinfo=UTC)


def ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware and in UTC.

    If naive, assume it's already UTC and attach UTC tzinfo.
    If tz-aware, convert to UTC.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_utc_date(value: datetime | date | int | str) -> date:
    """Normalize a value to a UTC date.

    Supported inputs:
    - datetime/date
    - unix ms (int/str)
    - ISO date string (YYYY-MM-DD)
    - ISO datetime string (YYYY-MM-DD HH:MM:SS)
    """
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return ensure_utc(value).date()
    s = str(value)
    if s.isdigit():
        return unix_ms_to_utc(int(s)).date()
    # Heuristics: choose parser by length
    if len(s) == 10:
        return parse_iso_date(s)
    return parse_iso_datetime_utc(s).date()


def at_utc_midnight(d: date | datetime) -> datetime:
    """Return a UTC datetime at 00:00:00 for the given date or datetime."""
    if isinstance(d, datetime):
        d_utc = ensure_utc(d).date()
    else:
        d_utc = d
    return datetime.combine(d_utc, time(0, 0, 0, tzinfo=UTC))


def is_utc_midnight(dt: datetime) -> bool:
    """Check if datetime is exactly at 00:00:00 UTC."""
    x = ensure_utc(dt)
    return (
        x.hour == 0 and x.minute == 0 and x.second == 0 and x.microsecond == 0
    )


def require_utc_midnight(dt: datetime) -> datetime:
    """Validate that a datetime is at 00:00:00 UTC.

    Returns the UTC-aware datetime or raises ValueError.
    """
    x = ensure_utc(dt)
    if not is_utc_midnight(x):
        raise ValueError("timestamp must align to 00:00:00 UTC for daily cut-off")
    return x


def all_before_cutoff(dts: Iterable[datetime], cutoff_hour: int = 0) -> bool:
    """Return True if all datetimes occur strictly before the daily cutoff.

    Cutoff is defined as HH:00:00 UTC (default 00:00 UTC) of the NEXT day
    relative to each datetime's UTC date. For HH=0, this is midnight of the
    next day; for other hours, the same concept applies.
    """
    for dt in dts:
        x = ensure_utc(dt)
        day_start = at_utc_midnight(x)
        cutoff = day_start.replace(hour=cutoff_hour)
        if not (x < cutoff):
            return False
    return True


__all__ = [
    "UTC",
    "unix_ms_to_utc",
    "parse_iso_date",
    "parse_iso_datetime_utc",
    "ensure_utc",
    "to_utc_date",
    "at_utc_midnight",
    "is_utc_midnight",
    "require_utc_midnight",
    "all_before_cutoff",
]

