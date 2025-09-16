# Data Model: DVOL Forecasting & Vol Trading

This document defines canonical tables, fields, dtypes, and validation rules. All dates are UTC daily.

## Entities and Tables

1) raw_dvol (from CDD DVOL OHLC)
- asset: string enum {BTC, ETH}
- date: string YYYY-MM-DD (UTC)
- unix: int64 (ms)
- open: float64
- high: float64
- low: float64
- close: float64
Validation: non-null for date, asset, close; ranges: 0 <= open,high,low,close <= 300

2) raw_ohlcv (perpetual futures OHLCV)
- asset: {BTC, ETH}
- symbol: string (e.g., BTC-PERPETUAL)
- date: string YYYY-MM-DD
- unix: int64 (ms)
- open, high, low, close: float64
- volume: float64 (base ccy)
- volume_usd: float64 (from `base_volume`)
Validation: non-null key fields; volume >= 0; price > 0

3) raw_options_summary (CDD options greeks maturities)
- asset: {BTC, ETH}
- date: string
- maturity: string YYYY-MM-DD
- net_vega: float64
- avg_iv: float64
- usd_volume: float64
Validation: allow missing `net_vega` days; set `options_availability_flag`

4) raw_funding (perpetual funding aggregates)
- asset: {BTC, ETH}
- date: string
- symbol: string (BTC-PERPETUAL, ETH-PERPETUAL)
- interest_8h: float64
- interest_1h: float64
- index_price: float64 (if provided)
Validation: aggregate to daily mean/sum as appropriate

5) raw_onchain (blockchain summary)
- asset: {BTC, ETH}
- date: string
- total_transactions: int64
- total_block_cnt: int64
- avg_secs_between_blocks: float64
- avg_block_size_mb: float64
- avg_transactions_count_per_block: float64
- base_gas_fee_sum_in_eth: float64 (ETH only; nullable for BTC)
- block_utilization: float64 (ETH only; nullable for BTC)
- onchain_is_imputed: bool (derived)
Validation: enforce t−1 lag; if >30% fields missing, drop day

6) daily_features (one row per asset-date)
- Key: asset, date
- Inputs (examples):
  - dvol_lag1, dvol_change1, dvol_range1
  - rv_1d, rv_5d, rv_22d, har_terms
  - options_net_vega_z5, options_usd_volume_z5
  - funding_mean_1d, funding_change_5d
  - onchain_tx_change_5d, fees_change_5d
- Flags: options_availability_flag, onchain_is_imputed
Validation: no NaNs beyond allowed imputations with flags; windows do not cross cut-off

7) labels (targets per horizon)
- asset, date (reference date)
- target_dvol_d1: float64 (close_{t+1} − close_{t})
- target_dvol_d7, target_dvol_d14: float64
Validation: constructed strictly from future DVOL closes beyond cut-off; aligned by asset/date

8) forecasts (model outputs)
- asset, date, horizon ∈ {1d,7d,14d}
- forecast_dvol: float64 (points)
- direction: enum {up, flat, down}
- confidence: float64 in [0,1] (derived from quantile spread)
Validation: produced only when all gates pass (e.g., ETH availability)

## As-Of Join Keys and Rules
- All joins are as-of on (asset, date). Features may use t−k lags only. Never include fields from the target date post cut-off.

## Storage Layout
- Parquet partitioning: `data/raw/<table>/asset=BTC/date=YYYY-MM-DD/*.parquet`, similarly for staging/features.

## Quality Gates
- Schema checks: jsonschema for row fields; pandera for DataFrame dtypes and ranges
- Cut-off tests: unit tests assert no future timestamps in joins
