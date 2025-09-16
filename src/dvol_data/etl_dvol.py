"""ETL adapter for DVOL (DeriBit Volatility Index) via CryptoDataDownload.

Functions are intentionally small and easy to read. They avoid side effects
unless explicitly requested (e.g., writing parquet).

References:
- API doc: see `CryptoDataDownloadAPI.txt` in repo root
- Config: `.env` for `CDD_API_BASE_URL` and `CDD_API_KEY`
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd


def parse_dvol_json(payload: Mapping[str, Any] | str) -> pd.DataFrame:
    """Parse DVOL JSON payload to a DataFrame.

    Accepts either a decoded JSON mapping with shape {"result": [...]}
    or a JSON string containing the same structure.

    Returns a DataFrame with raw fields from the API: date, unix, symbol,
    open, high, low, close.
    """
    if isinstance(payload, str):
        import json

        payload = json.loads(payload)

    result = payload.get("result", []) if isinstance(payload, Mapping) else []
    if not isinstance(result, Iterable):
        result = []

    df = pd.DataFrame(result or [])
    # Ensure expected columns exist (fill missing with NA)
    for col in ["date", "unix", "symbol", "open", "high", "low", "close"]:
        if col not in df.columns:
            df[col] = pd.NA
    return df[["date", "unix", "symbol", "open", "high", "low", "close"]]


def normalize_dvol_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize raw DVOL DataFrame to the `raw_dvol` contract shape.

    Output columns:
      - asset: str in {BTC, ETH}
      - date: YYYY-MM-DD (string)
      - unix: seconds since epoch (int)
      - open/high/low/close: float
      - symbol: optional passthrough (kept for traceability)
    """
    out = df.copy()

    # Asset from symbol: extract base like BTC/ETH
    sym = out.get("symbol", "").astype(str).str.upper()
    out["asset"] = sym.str.extract(r"(BTC|ETH)", expand=False).fillna("")

    # Date: keep as YYYY-MM-DD
    # API returns either "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS" in some endpoints.
    out["date"] = (
        pd.to_datetime(out["date"], errors="coerce")
        .dt.tz_localize(None)
        .dt.strftime("%Y-%m-%d")
    )

    # Unix: API example shows milliseconds as string; convert to integer seconds.
    # If value looks like ms (>= 10^12), downscale to seconds.
    unix_num = pd.to_numeric(out["unix"], errors="coerce")
    # scale ms->s where needed
    out["unix"] = unix_num.where(unix_num < 10**12, (unix_num // 1000)).astype("Int64")

    # Numeric conversions
    for c in ["open", "high", "low", "close"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    # Minimal column order; keep symbol for traceability though not required.
    cols = ["asset", "date", "unix", "symbol", "open", "high", "low", "close"]
    out = out[cols]
    return out


def write_raw_dvol(df: pd.DataFrame, *, asset: str, date: str, root: str | Path = "data") -> Path:
    """Write DVOL rows to raw storage using shared partitioning.

    Writes to: data/raw/raw_dvol/asset={asset}/date={date}/part.parquet
    """
    from .storage import write_partition

    return write_partition(df, layer="raw", table="raw_dvol", asset=asset, date=date, root=root)
