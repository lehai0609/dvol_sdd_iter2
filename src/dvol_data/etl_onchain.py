"""ETL adapter for On-chain signals normalized to contract and policy.

Enforces t-1 lag, limited forward-fill per policy, and an imputation flag.
"""

from __future__ import annotations

import pandas as pd


def normalize_onchain_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize raw on-chain daily metrics to `raw_onchain` contract.

    Expected numeric cols if present: total_transactions, total_block_cnt,
    avg_secs_between_blocks, avg_block_size_mb, avg_transactions_count_per_block,
    base_gas_fee_sum_in_eth, block_utilization.
    """
    out = df.copy()

    # Normalize keys
    out["asset"] = out.get("asset", "").astype(str).str.upper()
    out["asset"] = out["asset"].str.extract(r"(BTC|ETH)", expand=False)
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    # Ensure numeric types where applicable
    metric_cols = [
        "total_transactions",
        "total_block_cnt",
        "avg_secs_between_blocks",
        "avg_block_size_mb",
        "avg_transactions_count_per_block",
        "base_gas_fee_sum_in_eth",
        "block_utilization",
    ]
    for c in metric_cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    # Sort for deterministic shifting
    out = out.sort_values(["asset", "date"]).reset_index(drop=True)

    # Determine which metric columns are present
    present_metrics = [c for c in metric_cols if c in out.columns]
    if present_metrics:
        # Enforce t-1 lag per asset
        out[present_metrics] = (
            out.groupby("asset", dropna=False)[present_metrics]
            .shift(1)
        )

    # Limited forward fill (max 1 day) and imputation flag
    # Track which rows were NA before ffill
    if present_metrics:
        pre_na = out[present_metrics].isna()
        out[present_metrics] = (
            out.groupby("asset", dropna=False)[present_metrics]
            .apply(lambda g: g.ffill(limit=1))
            .reset_index(drop=True)
        )
        imputed_any = pre_na & out[present_metrics].notna()
        out["onchain_is_imputed"] = imputed_any.any(axis=1)
    else:
        out["onchain_is_imputed"] = False

    # Drop first day per asset (due to lag)
    out["row_idx"] = out.groupby("asset", dropna=False).cumcount()
    out = out[out["row_idx"] > 0].drop(columns=["row_idx"]).reset_index(drop=True)

    # Keep only contract columns if present
    keep_cols = [
        "asset",
        "date",
        "total_transactions",
        "total_block_cnt",
        "avg_secs_between_blocks",
        "avg_block_size_mb",
        "avg_transactions_count_per_block",
        "base_gas_fee_sum_in_eth",
        "block_utilization",
        "onchain_is_imputed",
    ]
    present_cols = [c for c in keep_cols if c in out.columns]
    return out[present_cols]
