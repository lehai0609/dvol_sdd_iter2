"""Data quality validation helpers.

Implements T028 with small, readable utilities:
- Outlier detection (simple z-score)
- Completeness checking for required fields
- Temporal consistency for daily data (gap detection)
- Cross-source trading day alignment
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, timedelta
from math import fsum
from typing import Any

from dvol_data_ingest.utils.datetime import to_utc_date


def detect_outliers_zscore(
    values: Sequence[float | int | None], z: float = 3.0
) -> list[int]:
    """Return indices considered outliers by absolute z-score > z.

    Ignores None values. If variance is zero or fewer than 2 finite values,
    returns an empty list.
    """
    # Collect finite floats and keep original indices
    data: list[tuple[int, float]] = []
    for i, v in enumerate(values):
        if v is None:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            continue
        if fv != fv:  # NaN check
            continue
        data.append((i, fv))
    if len(data) < 2:
        return []
    xs = [v for _, v in data]
    n = float(len(xs))
    mean = fsum(xs) / n
    var = fsum((x - mean) ** 2 for x in xs) / (n - 1.0)
    if var <= 0:
        return []
    std = var ** 0.5
    outliers: list[int] = []
    for idx, x in data:
        zscore = abs((x - mean) / std)
        if zscore > z:
            outliers.append(idx)
    return outliers


def _item_get(item: Any, field: str) -> Any:
    if isinstance(item, dict):
        return item.get(field)
    if hasattr(item, "model_dump") and callable(getattr(item, "model_dump")):
        return item.model_dump().get(field)
    return getattr(item, field, None)


def completeness_ratio(items: Iterable[Any], required_fields: Sequence[str]) -> float:
    """Compute fraction of items having all required fields non-null.

    Returns 0.0 for empty iterables.
    """
    total = 0
    ok = 0
    for item in items:
        total += 1
        if all(_item_get(item, f) is not None for f in required_fields):
            ok += 1
    return (ok / total) if total else 0.0


def daily_gaps(dates: Iterable[date | str]) -> list[date]:
    """Return missing daily dates between min and max (exclusive of ends).

    Input elements are normalized to UTC dates.
    """
    ds = sorted({to_utc_date(d) for d in dates})
    if len(ds) <= 1:
        return []
    missing: list[date] = []
    cur = ds[0]
    for d in ds[1:]:
        cur = cur + timedelta(days=1)
        while cur < d:
            missing.append(cur)
            cur = cur + timedelta(days=1)
        cur = d
    return missing


def is_daily_contiguous(dates: Iterable[date | str]) -> bool:
    """True if there are no gaps in the daily sequence."""
    return len(daily_gaps(dates)) == 0


def align_trading_days(
    a_dates: Iterable[date | str], b_dates: Iterable[date | str]
) -> tuple[set[date], set[date], set[date]]:
    """Align two date sets and return (common, missing_in_a, missing_in_b).

    Dates are normalized to UTC dates before comparison.
    """
    a = {to_utc_date(d) for d in a_dates}
    b = {to_utc_date(d) for d in b_dates}
    common = a & b
    missing_in_a = b - a
    missing_in_b = a - b
    return common, missing_in_a, missing_in_b


__all__ = [
    "detect_outliers_zscore",
    "completeness_ratio",
    "daily_gaps",
    "is_daily_contiguous",
    "align_trading_days",
]
