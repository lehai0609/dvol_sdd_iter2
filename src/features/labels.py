from __future__ import annotations

from typing import Iterable, Sequence

import pandas as pd


def _ensure_date_str(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.strftime("%Y-%m-%d")


def build_labels(
    df_dvol: pd.DataFrame,
    *,
    horizons: Sequence[int] | Iterable[int] = (1, 7, 14),
    close_col: str = "dvol_close",
) -> pd.DataFrame:
    """Build labels from future DVOL closes with strict cutoff.

    Produces columns `target_dvol_d{h}` for each horizon in days using
    future closes (shift(-h)). Output aligned by `asset`, `date`.
    """
    out = df_dvol.copy()
    if "asset" in out.columns:
        out["asset"] = out["asset"].astype(str).str.upper()
    else:
        out["asset"] = "BTC"
    out["date"] = _ensure_date_str(out["date"]) if "date" in out.columns else None

    # Compute targets as future closes
    for h in horizons:
        col = f"target_dvol_d{h}"
        out[col] = pd.to_numeric(out[close_col], errors="coerce").shift(-h)

    keep = ["asset", "date"] + [f"target_dvol_d{h}" for h in horizons]
    return out[keep]

