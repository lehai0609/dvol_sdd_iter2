"""Feature builder utilities for daily features.

All rolling windows and lags are computed using only information strictly
before the cutoff (t-1). Functions are pure and side-effect free.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_dvol_lags(df: pd.DataFrame, *, close_col: str = "dvol_close") -> pd.DataFrame:
    out = df.copy()
    out["dvol_lag1"] = out[close_col].shift(1)
    out["dvol_change1"] = out[close_col].shift(1) - out[close_col].shift(2)
    return out


def realized_volatility(
    prices: pd.Series, *, window: int = 3, trading_days: int = 252
) -> pd.Series:
    returns = pd.Series(prices).pct_change()
    rv = returns.shift(1).rolling(window).std() * np.sqrt(trading_days)
    return rv


def build_basic_features(df: pd.DataFrame) -> pd.DataFrame:
    out = add_dvol_lags(df, close_col="dvol_close")
    if "price_close" in out.columns:
        out["rv_3d"] = realized_volatility(out["price_close"], window=3)
    return out


def _zscore_prev(series: pd.Series, window: int) -> pd.Series:
    prev = series.shift(1)
    roll = prev.rolling(window)
    mean = roll.mean()
    std = roll.std(ddof=0)
    z = (prev - mean) / std
    return z.replace([np.inf, -np.inf], np.nan)


def build_daily_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute a superset of daily features per the contract schema.

    Expected columns (optional):
      - asset, date
      - dvol_close, high, low
      - price_close (spot/futures close for RV)
      - options_usd_volume, options_net_vega
      - interest_8h, interest_1h
      - total_transactions
      - options_availability_flag, onchain_is_imputed
    """
    out = df.copy()
    if "asset" in out.columns:
        out["asset"] = out["asset"].astype(str).str.upper()
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    # Core DVOL lags/changes (t-1)
    out["dvol_lag1"] = out.get("dvol_close").shift(1)
    out["dvol_change1"] = out.get("dvol_close").shift(1) - out.get("dvol_close").shift(2)

    # Intraday range from previous day if available
    if "high" in out.columns and "low" in out.columns:
        out["dvol_range1"] = (pd.to_numeric(out["high"], errors="coerce") - pd.to_numeric(out["low"], errors="coerce")).shift(1)
    else:
        out["dvol_range1"] = np.nan

    # Realized volatility windows on price_close
    if "price_close" in out.columns:
        out["rv_1d"] = realized_volatility(out["price_close"], window=1)
        out["rv_5d"] = realized_volatility(out["price_close"], window=5)
        out["rv_22d"] = realized_volatility(out["price_close"], window=22)
    else:
        out["rv_1d"] = np.nan
        out["rv_5d"] = np.nan
        out["rv_22d"] = np.nan

    # Options z-scores over 5D using t-1 window
    if "options_net_vega" in out.columns:
        out["options_net_vega_z5"] = _zscore_prev(pd.to_numeric(out["options_net_vega"], errors="coerce"), 5)
    else:
        out["options_net_vega_z5"] = np.nan
    if "options_usd_volume" in out.columns:
        out["options_usd_volume_z5"] = _zscore_prev(pd.to_numeric(out["options_usd_volume"], errors="coerce"), 5)
    else:
        out["options_usd_volume_z5"] = np.nan

    # Funding stats
    if "interest_8h" in out.columns:
        f = pd.to_numeric(out["interest_8h"], errors="coerce")
        out["funding_mean_1d"] = f.shift(1)
        out["funding_change_5d"] = f.shift(1) - f.shift(6)
    elif "interest_1h" in out.columns:
        f = pd.to_numeric(out["interest_1h"], errors="coerce")
        out["funding_mean_1d"] = f.shift(1)
        out["funding_change_5d"] = f.shift(1) - f.shift(6)
    else:
        out["funding_mean_1d"] = np.nan
        out["funding_change_5d"] = np.nan

    # On-chain changes using total_transactions if present
    if "total_transactions" in out.columns:
        tx = pd.to_numeric(out["total_transactions"], errors="coerce")
        out["onchain_tx_change_5d"] = tx.shift(1) - tx.shift(6)
    else:
        out["onchain_tx_change_5d"] = np.nan

    # Flags
    if "options_availability_flag" not in out.columns:
        if "options_usd_volume" in out.columns:
            out["options_availability_flag"] = (
                pd.to_numeric(out["options_usd_volume"], errors="coerce").shift(1) > 0
            )
        else:
            out["options_availability_flag"] = np.nan
    if "onchain_is_imputed" not in out.columns:
        out["onchain_is_imputed"] = np.nan

    # Return a DataFrame including at least asset/date & feature columns
    cols = [
        "asset",
        "date",
        "dvol_lag1",
        "dvol_change1",
        "dvol_range1",
        "rv_1d",
        "rv_5d",
        "rv_22d",
        "options_net_vega_z5",
        "options_usd_volume_z5",
        "funding_mean_1d",
        "funding_change_5d",
        "onchain_tx_change_5d",
        "onchain_is_imputed",
        "options_availability_flag",
    ]
    present = [c for c in cols if c in out.columns]
    return out[present]
