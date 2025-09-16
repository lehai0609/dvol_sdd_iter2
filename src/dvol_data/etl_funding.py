"""ETL adapter for Funding rates normalized to daily contract.

Produces rows with: asset, date, symbol, interest_8h, interest_1h, optional index_price.
"""

from __future__ import annotations

import pandas as pd


def daily_funding_from_intraday(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate intraday rows to daily contract columns.

    Accepts columns: date, symbol, interest_1h, interest_8h, index_price (optional).
    """
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["symbol"] = out.get("symbol", "").astype(str)

    out["interest_1h"] = pd.to_numeric(out.get("interest_1h"), errors="coerce")
    out["interest_8h"] = pd.to_numeric(out.get("interest_8h"), errors="coerce")
    if "index_price" in out.columns:
        out["index_price"] = pd.to_numeric(out.get("index_price"), errors="coerce")

    # Derive asset from symbol like BTC-PERPETUAL -> BTC
    symu = out["symbol"].str.upper()
    out["asset"] = symu.str.extract(r"(BTC|ETH)", expand=False)

    agg_map = {
        "interest_1h": "mean",
        "interest_8h": "mean",
        "index_price": "mean",
    }
    # Keep only available columns for aggregation
    present = {k: v for k, v in agg_map.items() if k in out.columns}
    daily = (
        out.groupby(["asset", "date", "symbol"], dropna=False)
        .agg(present)
        .reset_index()
    )

    cols = ["asset", "date", "symbol", "interest_8h", "interest_1h"]
    if "index_price" in daily.columns:
        cols.append("index_price")
    return daily[cols]
