"""ETL adapter for Futures OHLCV (T072 minimal scaffolding)."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

import pandas as pd


def parse_ohlcv_json(payload: Mapping[str, Any] | str) -> pd.DataFrame:
    if isinstance(payload, str):
        import json

        payload = json.loads(payload)
    result = payload.get("result", []) if isinstance(payload, Mapping) else []
    if not isinstance(result, Iterable):
        result = []
    df = pd.DataFrame(result or [])
    # Standardize columns
    for col in [
        "date",
        "unix",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "base_volume",
        "quote_volume",
        "volume_usd",
    ]:
        if col not in df.columns:
            df[col] = pd.NA
    return df[
        [
            "date",
            "unix",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "base_volume",
            "quote_volume",
            "volume_usd",
        ]
    ]


def normalize_ohlcv_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize OHLCV to the `raw_ohlcv` contract shape.

    Output columns:
      - asset, date, unix, symbol, open, high, low, close, volume, volume_usd
    """
    out = df.copy()

    # Derive asset from symbol (e.g., BTC-PERPETUAL -> BTC)
    sym = out.get("symbol", "").astype(str).str.upper()
    out["asset"] = sym.str.extract(r"(BTC|ETH)", expand=False).fillna("")

    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["unix"] = pd.to_numeric(out["unix"], errors="coerce").astype("Int64")
    for c in ["open", "high", "low", "close"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    # Volumes
    base_series = out["base_volume"] if "base_volume" in out.columns else pd.Series([pd.NA] * len(out))
    base = pd.to_numeric(base_series, errors="coerce")
    if "volume" in out.columns:
        volume = pd.to_numeric(out["volume"], errors="coerce")
    else:
        volume = base
    out["volume"] = volume

    quote_series = out["quote_volume"] if "quote_volume" in out.columns else pd.Series([pd.NA] * len(out))
    quote = pd.to_numeric(quote_series, errors="coerce")
    if "volume_usd" in out.columns:
        vol_usd = pd.to_numeric(out["volume_usd"], errors="coerce")
    else:
        vol_usd = pd.Series([pd.NA] * len(out))
    if vol_usd.isna().all():
        # Prefer quote volume if available; otherwise approximate base * close
        approx = quote
        if approx is None or approx.isna().all():
            approx = base * out["close"]
        out["volume_usd"] = approx
    else:
        out["volume_usd"] = vol_usd

    cols = [
        "asset",
        "date",
        "unix",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "volume_usd",
    ]
    return out[cols]
