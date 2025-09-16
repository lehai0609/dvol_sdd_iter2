# Tasks: DVOL Gap Closure (Phase 4 – Implementation Continuation)

Repository root: `D:\Document\OneDrive\10_Works\GitHub\dvol_sdd_iter2`
Feature dir: `specs\001-dvol-forecasting-volatility`
Design refs: `plan.md`, `research.md`, `data-model.md`, `contracts\*`, `quickstart.md`, `STATUS.md`

Conventions
- TDD-first: write failing tests, then minimum implementation to pass, then refactor.
- Paths are relative to repo root. Marked [P] tasks can run in parallel (different files).
- Use Poetry and pytest. Example run: `poetry run pytest -q tests/data/test_schema_raw_dvol.py`.

Parallel execution guidance appears after the tasks.

## Governance & Contracts Tests [P]

G010. Add JSON Schema tests for raw tables [P]
- Files: `tests/data/test_schema_raw_dvol.py`, `.../test_schema_raw_ohlcv.py`, `.../test_schema_raw_options_summary.py`, `.../test_schema_raw_funding.py`, `.../test_schema_raw_onchain.py`
- Validate sample rows against `specs/.../contracts/*.schema.json`.
- Acceptance: Each test loads schema via `jsonschema` and validates golden rows; tests pass.

G011. Add JSON Schema tests for features/labels/forecasts [P]
- Files: `tests/data/test_schema_daily_features.py`, `tests/data/test_schema_labels.py`, `tests/data/test_schema_forecasts.py`
- Acceptance: Rows built by builders in later tasks validate against schemas.

G012. Add cutoff policy loader and structure checks [P]
- File: `tests/data/test_policy_cutoff.py`
- Load `specs/.../contracts/policy.cutoff.yaml`; assert required keys/sections present.

G013. Anti-leakage tests from policy (as-of joins & windows) [P]
- Files: `tests/data/test_cutoff.py`, `tests/data/test_asof_join.py`
- Acceptance: Windows end strictly before cutoff; joins avoid future leakage; tests green on synthetic data.

## ETL Conformance & Storage Layout

G020. Shared parquet writer utility
- File: `src/dvol_data/storage.py`
- Implement `write_partition(df, *, layer: str, table: str, asset: str, date: str) -> Path` writing to `data/{layer}/{table}/asset={asset}/date={date}/part.parquet`.
- Acceptance: Unit test writes a tiny DF and asserts path and existence.

G021. Align DVOL ETL to contract + storage
- Files: `src/dvol_data/etl_dvol.py`
- Ensure normalized columns match `raw_dvol.schema.json` (`asset`, `date`, `unix`, `open/high/low/close`, optional `symbol`).
- Use `storage.write_partition` with `layer='raw'`, `table='raw_dvol'` for writes.
- Acceptance: Schema test passes on normalized sample; write creates correct partition path.

G022. Align OHLCV ETL to contract + add `asset`
- Files: `src/dvol_data/etl_ohlcv.py`
- Derive `asset` from `symbol` (e.g., `BTC-PERPETUAL` -> `BTC`); ensure `volume` and `volume_usd` present per schema.
- Acceptance: Schema test passes on sample; mapping `base_volume -> volume_usd` covered.

G023. Align Options ETL to contract fields
- Files: `src/dvol_data/etl_options.py`
- Map fields to `avg_iv`, `usd_volume`, `net_vega`, and include `maturity`; keep `asset`, `date` normalized.
- Acceptance: Schema test passes; downstream features will compute availability flags.

G024. Align Funding ETL to daily contract
- Files: `src/dvol_data/etl_funding.py`
- Produce daily rows with `asset`, `date`, `symbol`, `interest_8h`, `interest_1h`, optional `index_price`.
- Acceptance: Schema test passes on aggregated sample.

G025. Align On-chain ETL to contract and policy
- Files: `src/dvol_data/etl_onchain.py`
- Normalize to `raw_onchain.schema.json`; set `onchain_is_imputed` per policy; enforce t-1 lag and drop first day accordingly.
- Acceptance: Schema test passes; anti-leakage tests remain green.

## Features and Labels

G030. Implement labels builder with strict cutoff
- File: `src/features/labels.py`
- Functions: `build_labels(df_dvol, horizons=(1,7,14)) -> DataFrame` producing `target_dvol_d1/d7/d14` from future closes; align on `asset,date`.
- Tests: `tests/data/test_labels_build.py` crafting a small DVOL series and asserting correct future diffs.
- Acceptance: Test passes and `labels.schema.json` validation succeeds.

G031. Expand feature builder to full `daily_features`
- File: `src/features/build.py`
- Add: `dvol_range1`, RV windows (`rv_1d/5d/22d` on spot/futures), options z-scores over 5D (`options_net_vega_z5`, `options_usd_volume_z5`), funding mean/change, on-chain change windows; include `options_availability_flag` and `onchain_is_imputed`.
- Tests: `tests/features/test_feature_defs.py` extended with additional checks; new `tests/features/test_daily_features_schema.py` validates against schema.
- Acceptance: Deterministic outputs on golden set; schema test passes.

## Modeling & Walk-Forward

G040. Tree models with quantile outputs (LightGBM/XGBoost)
- File: `src/models/trees.py`
- Implement a thin wrapper supporting: `fit(X,y, quantiles=[0.1,0.5,0.9])`, `predict`, `predict_quantiles`; store model artifacts per fold if path given.
- Tests: Extend `tests/models/test_uncertainty.py` or add `tests/models/test_trees_quantiles.py` to validate quantile monotonicity and bounded confidence using `quantile_interval_confidence`.
- Acceptance: Tests pass; predictions finite and quantiles monotone.

G041. Walk-forward training and artifact persistence
- Files: `src/models/walkforward.py`, `src/models/reproduce.py`
- Implement expanding folds training across horizons; emit per-date forecasts (point + quantiles), persist artifacts under `artifacts/models/<run_id>/...`.
- Acceptance: New `tests/integration/test_walkforward_pipeline.py` ensures end-to-end on synthetic data produces forecasts and artifacts.

G042. Forecast record construction
- File: `src/models/reproduce.py`
- Build `forecasts` rows with `asset`, `date`, `horizon in {1d,7d,14d}`, `forecast_dvol`, `direction` (sign of forecast in {up,flat,down}), and `confidence` (from quantile width normalization).
- Acceptance: `tests/data/test_schema_forecasts.py` passes; rows produced for all horizons.

## Mapping, Backtest, and Guardrails

G050. Threshold calibration integrated with forecasts
- Files: `src/backtest/mapping.py`
- Add function `calibrate_per_horizon(scores, returns, costs, grid)` and `map_forecasts_to_stance(forecasts_df, thresholds_by_horizon)`.
- Acceptance: Validation on synthetic returns shows positive net edge and produces stances per horizon.

G051. Guardrails applied to positions
- Files: `src/backtest/risk.py`
- Ensure guardrail application is integrated in mapping flow using config from plan (`max_abs_position`, `event_guard_threshold`, `daily_stop_loss`).
- Acceptance: Existing `tests/backtest/test_risk.py` remains green; new mapping tests verify capped outputs.

## Governance & Policy Integration

G060. Policy loader utility and hooks
- File: `src/dvol_data/policy.py`
- Implement `load_policy()` to parse YAML and expose keys. Wire simple checks in features/labels to assert windows and cutoff rules in debug mode.
- Tests: `tests/data/test_policy_cutoff.py` extended to call loader; `tests/data/test_cutoff.py` uses loader rules.
- Acceptance: All policy-related tests pass without leakage.

## Notebook & CI

G070. Orchestrator notebook
- File: `notebooks/00_Control_Pipeline.ipynb`
- Sections A–F per quickstart calling library functions only; small synthetic run section for CI smoke.
- Acceptance: Manual run creates artifacts in `artifacts/`; optional smoke via nbclient locally.

G071. GitHub Actions CI workflow
- File: `.github/workflows/ci.yml`
- Steps: setup Python 3.11, `poetry install`, `ruff check .`, `black --check .`, `pytest -q`, and nbclient smoke on the orchestrator notebook.
- Acceptance: Workflow runs successfully on PRs and main.

## Configuration Cleanup & Reporting Integration

G080. Remove invalid CLI script entry
- File: `pyproject.toml`
- Remove `project.scripts.dvol-ingest = dvol_data_ingest.cli.main:app` (no CLI in this repo per plan).
- Acceptance: `poetry build` or `poetry run` commands unaffected; no missing-entrypoint warnings.

G081. Integrate metrics and reporting into pipeline
- Files: `src/models/reproduce.py`, `src/metrics/reports.py`
- After walk-forward/backtest, write CSV/PNG/HTML summaries to `artifacts/reports/` with deterministic naming.
- Acceptance: New `tests/metrics/test_pipeline_reports.py` verifies files exist and names match stem/run_id.

---

## Parallel Execution Guidance
- Group A (contracts/policy) [P]: G010–G013
- Group B (ETL) [P]: G020–G025
- Group C (features/labels) [P]: G030–G031
- Group D (models/walk-forward) [P]: G040–G042
- Group E (mapping/risk) [P]: G050–G051
- Group F (notebook/CI/config) [P]: G070–G071, G080–G081

Example commands (PowerShell):
```
# Group A
poetry run pytest -q tests/data/test_schema_raw_dvol.py;
poetry run pytest -q tests/data/test_schema_raw_ohlcv.py;
poetry run pytest -q tests/data/test_schema_raw_options_summary.py;
poetry run pytest -q tests/data/test_schema_raw_funding.py;
poetry run pytest -q tests/data/test_schema_raw_onchain.py;
poetry run pytest -q tests/data/test_schema_daily_features.py;
poetry run pytest -q tests/data/test_schema_labels.py;
poetry run pytest -q tests/data/test_schema_forecasts.py;
poetry run pytest -q tests/data/test_policy_cutoff.py;

# Group B
poetry run pytest -q tests/data/test_cutoff.py;
poetry run pytest -q tests/data/test_asof_join.py;

# Group C
poetry run pytest -q tests/features/test_feature_defs.py;
poetry run pytest -q tests/features/test_daily_features_schema.py;

# Group D
poetry run pytest -q tests/models/test_uncertainty.py;
poetry run pytest -q tests/models/test_trees_quantiles.py;
poetry run pytest -q tests/integration/test_walkforward_pipeline.py;

# Group E
poetry run pytest -q tests/backtest/test_thresholds.py;
poetry run pytest -q tests/backtest/test_risk.py;

# Group F
poetry run pytest -q tests/metrics/test_pipeline_reports.py;
```

Dependencies overview
- Contracts/Policy (G010–G013) → ETL conformance (G020–G025) → Features/Labels (G030–G031) → Models/Walk-forward (G040–G042) → Mapping/Backtest (G050–G051) → Notebook/CI/Config/Reports (G070–G071, G080–G081).

Acceptance of this phase
- Contract and policy tests exist and pass for all schemas.
- ETL adapters produce contract-conformant frames and write to spec-compliant partitions.
- Feature builder and labels satisfy schemas and anti-leakage tests.
- Walk-forward produces forecasts with quantiles, direction, and confidence; artifacts persisted.
- Mapping/backtest integrated with thresholds and guardrails; positive net edge on synthetic validation.
- Orchestrator notebook added; CI workflow runs linters, tests, and notebook smoke; config cleaned.
- Reports generated under `artifacts/reports/` with deterministic names.
