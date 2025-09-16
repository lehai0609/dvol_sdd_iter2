# Tasks: DVOL Forecasting & Volatility Trading (Phase 3 - Implementation)

Repository root: `D:\Document\OneDrive\10_Works\GitHub\dvol_sdd_iter2`
Feature dir: `specs\001-dvol-forecasting-volatility`
Design refs: `plan.md`, `research.md`, `data-model.md`, `contracts\*`, `quickstart.md`

Conventions
- TDD-first: write failing tests, then minimum implementation to pass, then refactor.
- Paths are relative to repo root. Marked [P] tasks can run in parallel (different files).
- Use Poetry and pytest. Example run: `poetry run pytest -q tests/data/test_schema_raw_dvol.py`.

Parallel execution guidance appears after the tasks.

## Setup (before any tests)

T001. Create package skeletons and init files
- Create directories and `__init__.py`:
  - `src/dvol_data/`, `src/features/`, `src/models/`, `src/backtest/`, `src/metrics/`
  - `tests/data/`, `tests/features/`, `tests/models/`, `tests/backtest/`, `tests/metrics/`, `tests/e2e/`, `tests/integration/`, `tests/docs/`
- Acceptance: Imports `from features import ...` and `from dvol_data import ...` succeed.
- Example commands:
  - `git add -A && git commit -m "chore: create src/tests skeletons"`

T002. Ensure dev dependencies
- Add Hypothesis for property tests if missing; keep versions pinned by Poetry.
- Files: `pyproject.toml`
- Example commands:
  - `poetry add --group dev hypothesis`
  - `poetry install`

T003. Data directories placeholders
- Create folders: `data/raw/`, `data/staging/`, `data/features/`, `artifacts/models/`, `artifacts/reports/` with `.gitkeep` files.
- Acceptance: Folders exist and are git-tracked.

T004. Notebook kernel check
- Ensure Jupyter kernel registered: `dvol-research` (already in quickstart). If missing, register.
- Example command:
  - `poetry run python -m ipykernel install --user --name dvol-research`

## Contract Tests (one per schema) [P]

T010. Test CDD API contracts match docs [P]
- File: `tests/data/test_api_contracts.py`
- Validate fields/types against `CryptoDataDownloadAPI.txt` using mocked payloads.

T011. Test raw_dvol schema [P]
- File: `tests/data/test_schema_raw_dvol.py`
- Validate rows vs `specs/001-dvol-forecasting-volatility/contracts/raw_dvol.schema.json`.

T012. Test raw_ohlcv schema [P]
- File: `tests/data/test_schema_raw_ohlcv.py`
- Validate rows vs `contracts/raw_ohlcv.schema.json` and map `base_volume -> volume_usd`.

T013. Test raw_options_summary schema [P]
- File: `tests/data/test_schema_raw_options_summary.py`
- Validate rows vs `contracts/raw_options_summary.schema.json`.

T014. Test raw_funding schema [P]
- File: `tests/data/test_schema_raw_funding.py`
- Validate rows vs `contracts/raw_funding.schema.json`.

T015. Test raw_onchain schema [P]
- File: `tests/data/test_schema_raw_onchain.py`
- Validate rows vs `contracts/raw_onchain.schema.json`.

T016. Test daily_features schema [P]
- File: `tests/data/test_schema_daily_features.py`
- Validate rows vs `contracts/daily_features.schema.json`.

T017. Test labels schema [P]
- File: `tests/data/test_schema_labels.py`
- Validate rows vs `contracts/labels.schema.json`.

T018. Test forecasts schema [P]
- File: `tests/data/test_schema_forecasts.py`
- Validate rows vs `contracts/forecasts.schema.json`.

T019. Test policy.cutoff.yaml loads [P]
- File: `tests/data/test_policy_cutoff.py`
- Validate required keys and structures in `contracts/policy.cutoff.yaml`.

## Anti-leakage & Cut-off Tests [P]

T020. Test cut-off discipline [P]
- File: `tests/data/test_cutoff.py`
- Assert features use t-1 or earlier; labels use future DVOL closes correctly.

T021. Property test for as-of joins [P]
- File: `tests/data/test_asof_join.py`
- Property: joined rows never depend on future info.

## Feature Engineering Tests [P]

T022. Rolling windows and scalers [P]
- File: `tests/features/test_windows.py`
- Windows stop before cut-off; scalers fit only on training windows.

T023. Deterministic feature definitions [P]
- File: `tests/features/test_feature_defs.py`
- Golden dataset → deterministic feature outputs.

## Modeling Tests

T030. Baselines: naïve, HAR, linear
- File: `tests/models/test_baselines.py`
- Fit/predict shapes; simple sanity metrics.

T031. Walk-forward folds
- File: `tests/models/test_walkforward.py`
- Expanding folds; no leakage.

T032. Uncertainty calibration
- File: `tests/models/test_uncertainty.py`
- Quantile outputs monotone and confidence in [0,1].

## Backtest & Mapping Tests

T040. Costs applied consistently
- File: `tests/backtest/test_costs.py`
- Fees/slippage always deducted.

T041. Threshold calibration shows net edge
- File: `tests/backtest/test_thresholds.py`
- On validation split, thresholds produce >0 net edge.

T042. Risk guardrails trigger
- File: `tests/backtest/test_risk.py`
- Guardrails fire on jump scenarios; caps enforced.

## Metrics & Reporting Tests [P]

T050. Evaluation metrics [P]
- File: `tests/metrics/test_eval_metrics.py`
- RMSE/MAE/Spearman/hit-rate correct on toy data.

T051. Report generation [P]
- File: `tests/metrics/test_reports.py`
- CSV/PNG/HTML stubs; deterministic filenames.

## Notebook & Repro Tests

T060. Notebook smoke test
- File: `tests/e2e/test_notebook_smoke.py`
- Execute tiny sample via nbclient; all sections run on mock data.

T061. Reproduce-run entrypoint
- File: `tests/integration/test_reproduce_run.py`
- Calls function to replay one walk-forward slice end-to-end (mocked data).

## Minimal Implementation Scaffolding (after RED)

T070. Module skeletons and exports
- Files: `src/**/__init__.py` and minimal module stubs raising `NotImplementedError`.
- Ensure tests can import modules without runtime side effects.

T071. ETL adapter: DVOL
- File: `src/dvol_data/etl_dvol.py`
- Functions: `parse_dvol_json`, `normalize_dvol_df`, `write_parquet_partition`.

T072. ETL adapter: Futures OHLCV
- File: `src/dvol_data/etl_ohlcv.py`
- Functions: `parse_ohlcv_json`, `normalize_ohlcv_df` (map `base_volume`→`volume_usd`).

T073. ETL adapter: Options summaries
- File: `src/dvol_data/etl_options.py`
- Functions: `parse_options_json`, `normalize_options_df` (set `options_availability_flag`).

T074. ETL adapter: Funding
- File: `src/dvol_data/etl_funding.py`
- Aggregate 8h/1h → daily.

T075. ETL adapter: On-chain
- File: `src/dvol_data/etl_onchain.py`
- Enforce t−1 lag; imputation flags; drop-day policy.

T076. Feature builder
- File: `src/features/build.py`
- Pure functions for RV, DVOL lags/diffs, options z-scores, funding/on-chain changes.

T077. Modeling baselines and trees
- File: `src/models/baselines.py`, `src/models/trees.py`
- Baselines using statsmodels/sklearn; quantile regression for uncertainty.

T078. Walk-forward runner
- File: `src/models/walkforward.py`
- Expanding folds; per-fold artifacts persisted under `artifacts/models/`.

T079. Backtest mapping & costs
- File: `src/backtest/mapping.py`, `src/backtest/costs.py`, `src/backtest/risk.py`
- Threshold calibration, cost model, guardrails.

T080. Metrics and reporting
- File: `src/metrics/eval.py`, `src/metrics/reports.py`
- Compute metrics; generate simple CSV/PNG/HTML outputs.

T081. Reproduce-run function
- File: `src/models/reproduce.py`
- Replay one slice raw→features→model→backtest for validation.

T090. CI workflow
- File: `.github/workflows/ci.yml`
- Run `poetry install`, `poetry run pytest -q`, and notebook smoke via nbclient.

T091. Docs checks
- File: `tests/docs/test_quickstart_refs.py` and updates to `specs/.../quickstart.md` if needed.

---

## Parallel Execution Guidance
- After T001–T004, run these groups in parallel:
  - Group A (contracts) [P]: T010–T019
  - Group B (anti-leakage/features) [P]: T020–T023
  - Group C (metrics) [P]: T050–T051

Example commands (bash):
```bash
# Group A
poetry run pytest -q tests/data/test_api_contracts.py &
poetry run pytest -q tests/data/test_schema_raw_dvol.py &
poetry run pytest -q tests/data/test_schema_raw_ohlcv.py &
poetry run pytest -q tests/data/test_schema_raw_options_summary.py &
poetry run pytest -q tests/data/test_schema_raw_funding.py &
poetry run pytest -q tests/data/test_schema_raw_onchain.py &
poetry run pytest -q tests/data/test_schema_daily_features.py &
poetry run pytest -q tests/data/test_schema_labels.py &
poetry run pytest -q tests/data/test_schema_forecasts.py &
poetry run pytest -q tests/data/test_policy_cutoff.py &
wait

# Group B
poetry run pytest -q tests/data/test_cutoff.py &
poetry run pytest -q tests/data/test_asof_join.py &
poetry run pytest -q tests/features/test_windows.py &
poetry run pytest -q tests/features/test_feature_defs.py &
wait

# Group C
poetry run pytest -q tests/metrics/test_eval_metrics.py &
poetry run pytest -q tests/metrics/test_reports.py &
wait
```

Dependencies overview
- Setup (T001–T004) → Contract/Feature/Anti-Leakage tests (T010–T023, T050–T051) → Modeling/Backtest tests (T030–T042) → Notebook/Repro tests (T060–T061) → Minimal code scaffolding/impl (T070–T081) → CI + Docs (T090–T091).

Acceptance of this phase
- A complete `tests/` skeleton exists with failing tests aligned to contracts and plan.
- Minimal `src/` scaffolding exists; all imports resolve.
- CI config ready to run unit tests and notebook smoke later.
