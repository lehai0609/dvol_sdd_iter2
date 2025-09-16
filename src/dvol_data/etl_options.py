"""ETL adapter for Options summaries normalized to contract.

Maps raw fields to the `raw_options_summary` contract:
  - asset, date, maturity, avg_iv, usd_volume, net_vega
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

import pandas as pd


def parse_options_json(payload: Mapping[str, Any] | str) -> pd.DataFrame:
    """Parse options summary JSON payload to a DataFrame.

    Accepts decoded mapping or JSON string containing {"result": [...]}.
    """
    if isinstance(payload, str):
        import json

        payload = json.loads(payload)
    result = payload.get("result", []) if isinstance(payload, Mapping) else []
    if not isinstance(result, Iterable):
        result = []
    df = pd.DataFrame(result or [])
    # Standardize columns we will use downstream
    for col in [
        "date",
        "maturity",
        "avg_iv",
        "usd_volume",
        "net_vega",
        "underlying",
        "symbol",
    ]:
        if col not in df.columns:
            df[col] = pd.NA
    return df[["date", "maturity", "avg_iv", "usd_volume", "net_vega", "underlying", "symbol"]]


def normalize_options_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize options summary to `raw_options_summary` contract fields.

    Output columns: asset, date, maturity, avg_iv, usd_volume, net_vega
    """
    out = df.copy()

    # Asset from `underlying` if present, otherwise from symbol
    underlying = out.get("underlying", "").astype(str).str.upper()
    if underlying.isna().all() or (underlying == "").all():
        sym = out.get("symbol", "").astype(str).str.upper()
        underlying = sym.str.extract(r"(BTC|ETH)", expand=False)
    out["asset"] = underlying.fillna("")

    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["maturity"] = pd.to_datetime(out["maturity"], errors="coerce").dt.strftime("%Y-%m-%d")

    # Rename/convert metrics
    out["avg_iv"] = pd.to_numeric(out.get("avg_iv"), errors="coerce")
    out["usd_volume"] = pd.to_numeric(out.get("usd_volume"), errors="coerce")
    out["net_vega"] = pd.to_numeric(out.get("net_vega"), errors="coerce")

    cols = ["asset", "date", "maturity", "avg_iv", "usd_volume", "net_vega"]
    return out[cols]
