# DVOL Forecasting & Volatility Trading – Status Report
Date: 2025-09-16
Feature: `specs/001-dvol-forecasting-volatility`

## Executive Summary
- Contract, policy, and schema coverage plus ETL/feature/model scaffolding are in place and green (`tests/data/test_schema_raw_dvol.py:1`, `src/dvol_data/etl_dvol.py:17`, `src/features/build.py:44`, `src/models/walkforward.py:37`).
- Synthetic walk-forward pipelines generate forecasts, artifacts, and reports while exercising quantile modeling and backtest helpers (`tests/integration/test_walkforward_pipeline.py:5`, `src/models/reproduce.py:17`, `notebooks/dvol_pipeline.ipynb#L1`).
- Remaining work centers on applying governance gates, running the real data flow end-to-end, and instrumenting observability per the plan (`specs/001-dvol-forecasting-volatility/plan.md:6`, `specs/001-dvol-forecasting-volatility/research.md:45`).

## Progress Against Plan
- **Documentation & Contracts**: Spec, plan, research, data-model, quickstart, and JSON/YAML contracts committed and validated in tests (`specs/001-dvol-forecasting-volatility/spec.md:1`, `specs/001-dvol-forecasting-volatility/contracts/raw_dvol.schema.json:1`, `tests/data/test_policy_cutoff.py:1`).
- **ETL Layer**: Normalizers for DVOL, futures, options, funding, and on-chain data align with schemas and shared partitioning (`src/dvol_data/storage.py:7`, `src/dvol_data/etl_ohlcv.py:18`, `src/dvol_data/etl_onchain.py:13`, `tests/dvol_data/test_etl_onchain_conformance.py:1`).
- **Features & Labels**: Daily features and label builders respect cut-off requirements and contract fields (`src/features/build.py:44`, `src/features/labels.py:9`, `tests/features/test_daily_features_schema.py:1`).
- **Modeling & Backtest**: LightGBM quantile wrapper, walk-forward runner, baseline models, and guardrails deliver forecasts with direction/confidence plus cost-aware stance helpers (`src/models/trees.py:1`, `src/models/walkforward.py:37`, `src/backtest/mapping.py:8`, `tests/backtest/test_thresholds.py:1`).
- **Reporting & Notebook**: Metrics reporters persist CSV/PNG/HTML outputs and the orchestration notebook executes a synthetic pipeline writing artifacts (`src/metrics/reports.py:8`, `notebooks/dvol_pipeline.ipynb#L1`, `tests/e2e/test_notebook_smoke.py:5`).
- **CI & Tooling**: GitHub Actions workflow runs lint + pytest + nbclient smoke, matching pipeline expectations (`.github/workflows/ci.yml:1`).

## Gap Analysis vs Spec/Plan
- Plan mandates a single control notebook at `notebooks/00_Control_Pipeline.ipynb` that calls library ETL/feature/model functions (`specs/001-dvol-forecasting-volatility/plan.md:78`, `specs/001-dvol-forecasting-volatility/quickstart.md:19`); current notebook `notebooks/dvol_pipeline.ipynb#L1` and smoke test `tests/e2e/test_notebook_smoke.py:5` generate synthetic cells and bypass the actual modules.
- Integration testing is limited to synthetic data; the plan calls for a 6-month sample covering ETL → features → model → mapping with real schemas (`specs/001-dvol-forecasting-volatility/plan.md:43`, `tests/integration/test_walkforward_pipeline.py:5`).
- Governance policies for ETH enablement and options availability ratios are defined but not enforced (policy `specs/001-dvol-forecasting-volatility/contracts/policy.cutoff.yaml:25`, research decision `specs/001-dvol-forecasting-volatility/research.md:56`); current builders only mark simple volume flags or always emit forecasts (`src/features/build.py:113`, `src/models/reproduce.py:84`).
- Observability requirements to record audit metadata alongside Parquet writes are unmet (`specs/001-dvol-forecasting-volatility/plan.md:45`); storage helper only dumps Parquet without row counts or ranges (`src/dvol_data/storage.py:7`).
- Experiment tracking via mlflow/wandb was selected in research (`specs/001-dvol-forecasting-volatility/research.md:61`) but no run metadata is captured in the pipeline (`src/models/reproduce.py:84`).
- Threshold-to-stance plumbing exists but is not exercised end-to-end; `map_forecasts_to_stance` lacks tests/integration hooks (`specs/001-dvol-forecasting-volatility/tasks-gap-closure.md:100`, `src/backtest/mapping.py:79`, `src/models/reproduce.py:84`).
- Quickstart instructions and repo layout references still point to the previous notebook name and ETL entrypoints that do not exist (`specs/001-dvol-forecasting-volatility/quickstart.md:10`).

## Proposed Follow-up Tasks
1. Replace the synthetic orchestration with the planned control notebook: wire `notebooks/dvol_pipeline.ipynb#L1` (or rename to `00_Control_Pipeline.ipynb`) to call the ETL/feature/model/backtest modules, update smoke test to execute that notebook, and refresh quickstart references (`tests/e2e/test_notebook_smoke.py:5`, `specs/001-dvol-forecasting-volatility/quickstart.md:19`).
2. Add a golden 6-month fixture and integration test that runs ETL → features → walk-forward → mapping end-to-end, persisting sample Parquet partitions and verifying schema compliance (`tests/integration/test_walkforward_pipeline.py:5`, `data/raw/.gitkeep`).
3. Implement policy-driven availability gating: compute the options volume ratio + DVOL liquidity checks before emitting ETH forecasts, and drop forecasts when gates fail (`src/features/build.py:113`, `src/models/reproduce.py:84`, `specs/001-dvol-forecasting-volatility/contracts/policy.cutoff.yaml:25`).
4. Extend storage/pipeline instrumentation to record audit metadata (row counts, min/max, checksums) and hook mlflow/wandb run logging when replaying slices (`src/dvol_data/storage.py:7`, `src/models/reproduce.py:84`, `specs/001-dvol-forecasting-volatility/research.md:61`).
5. Integrate stance calibration into the reproducible pipeline and cover it with tests: apply `calibrate_per_horizon`/`map_forecasts_to_stance` and assert guardrail behaviour in integration outputs (`src/backtest/mapping.py:57`, `src/models/reproduce.py:84`, `tests/backtest/test_risk.py:1`).
