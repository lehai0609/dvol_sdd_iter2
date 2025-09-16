# Phase 0 Research: DVOL Forecasting & Vol Trading

Date: 2025-09-15 | Branch: 001-dvol-forecasting-volatility

Scope: Resolve unknowns and lock decisions that guide Phase 1 design and later implementation. Canonical data source doc: `CryptoDataDownloadAPI.txt` at repo root.

## Data Sources and Semantics

Decision: Use CryptoDataDownload (CDD) endpoints only, schemas aligned with `CryptoDataDownloadAPI.txt`.
Rationale: Single provider for DVOL, futures, options summaries, funding, and on-chain summaries; consistent field naming and date semantics.
Alternatives: Native Deribit + Dune for on-chain. Rejected for complexity and multi-provider alignment risk.

Details
- DVOL OHLC: `/v1/data/ohlc/deribit/volatility?symbol=BTC|ETH` → fields: `date`, `unix`, `symbol`, `open`, `high`, `low`, `close`.
- Futures OHLCV: `/v1/data/ohlc/deribit/futures/?symbol=BTC-PERPETUAL|...` → fields: `unix`, `date`, `symbol`, `open`, `high`, `low`, `close`, `volume`, `base_volume` (USD notional)
- Options summaries (maturities): `/v1/data/summary/deribit/options/greeks/maturities/?underlying=BTC|ETH` → includes `net_vega`, `avg_iv`, `usd_volume`.
- Funding: `/v1/data/ohlc/deribit/futures/funding/?symbol=BTC-PERPETUAL` → fields include `interest_8h`, `interest_1h` (aggregate to daily).
- On-chain summary: `/v1/data/summary/blockchain/blocks/?symbol=btc|eth` → daily TX, block count, gas, etc. Apply t−1 lag policy for inclusion.

Constraints and Policies
- UTC discipline: treat `date` as UTC calendar; cut-off at 00:00 UTC. Features must be finalized pre target close.
- Missing data: allow single-day forward-fill for on-chain only, set flags; otherwise drop or mark unavailable.
- Anti-leakage: as-of joins on (asset, date_utc). Never use future rows for features.

## Staging Tables and Dtypes

Decision: Define five raw/staging tables and one feature table with explicit dtypes. See `data-model.md` and `contracts/*.schema.json`.
Rationale: Repeatable I/O, validation via pandera/jsonschema, and easy partitioning.
Alternatives: DuckDB database. Rejected initially to minimize dependencies; can layer later.

Key columns (all UTC):
- Keys: `asset` ∈ {BTC, ETH}, `date` = YYYY-MM-DD (string) plus `date_utc` as date type in parquet metadata.
- Numeric types: float64 for prices/indices, int64 for counts; categorical strings for symbols.

## Targets and Horizons

Decision: Predict absolute ΔDVOL in points for t+1d; t+7d and t+14d also in points for mapping, with auxiliary %Δ for analysis.
Rationale: DVOL futures P&L linear in points; consistent across horizons, while %Δ used to sanity-check scaling.
Alternatives: Mixed absolute/% depending on horizon. Rejected due to complexity in mapping.

## Models and Uncertainty

Decision: Baselines = Naïve (Δ=0), HAR-RV (statsmodels), linear (ridge). Primary = Gradient-boosted trees (LightGBM/XGBoost). Optional LSTM ablation.
Rationale: Tabular signal mix favors trees; HAR baseline is standard for volatility.
Uncertainty: Standardize on quantile regression with trees (q10/50/90) to derive confidence; LSTM uses MC-dropout only in ablation.
Alternatives: Bayesian linear models. Deferred.

## Threshold Calibration and Costs

Decision: Grid-search thresholds per horizon to maximize validation net Sharpe after conservative costs: taker 5bps/maker −1bps, slippage = 0.5× spread small clips, 1× for larger; minimum spread 0.1 tick when unknown.
Rationale: Simple, transparent, and robust to noise.
Alternatives: Dynamic programming sizing. Overkill for v1.

## ETH Enablement Gates

Decision: ETH forecasts only produced if `options_availability_flag` and liquidity checks pass: 20D median USD notional for DVOL futures > $2m, else route to options expression.
Rationale: Prevents low-liquidity exposure.

## Experiment Tracking & Reproducibility

Decision: Use mlflow (or wandb alternative if already in environment). Persist per-fold artifacts under `artifacts/models/` and reports under `artifacts/reports/` with run metadata.
Rationale: Lightweight, standard practice.

## Notebook UX

Decision: One thin orchestrator notebook `notebooks/00_Control_Pipeline.ipynb` with sections A–F calling library functions only.
Rationale: Single pane of glass; CI smoke-run via nbclient.

## Open Questions Resolved
- Net Vega availability: provided by CDD endpoint; add fallback proxies only later if needed. Track `options_availability_flag`.
- On-chain lag: enforce t−1 lag; allow 1-day forward-fill with `onchain_is_imputed`; drop day if >30% missing/imputed.
