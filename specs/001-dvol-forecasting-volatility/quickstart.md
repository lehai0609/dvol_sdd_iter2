# Quickstart: DVOL Forecasting & Vol Trading

## 1) Environment
- Requires Python 3.11.9 via Poetry
- Install deps:
  - `poetry install`
  - Register kernel: `poetry run python -m ipykernel install --user --name dvol-research`

## 2) Repo Layout
- Code lives under `src/`; tests under `tests/`; notebook under `notebooks/00_Control_Pipeline.ipynb`
- Data Parquet under `data/{raw,staging,features}/`; artifacts under `artifacts/{models,reports}/`

## 3) TDD Workflow
1. Write failing test in `tests/...`
2. Run tests: `poetry run pytest -q`
3. Implement minimal code in `src/...` to pass
4. Refactor, keep tests green

## 4) Notebook UI
- Open `notebooks/00_Control_Pipeline.ipynb` and select kernel `dvol-research`
- Sections:
  - A. Run ETL → calls `dvol_data.etl.run(date_range)`
  - B. Build Features → `features.build.run(date_range)`
  - C. Train/Walk-forward → choose model, folds; emits artifacts
  - D. Backtest & Report → select expression; writes to `artifacts/reports/`
  - E. Paper-trade → runs today’s signal; prints `{forecast, direction, confidence}`
  - F. Audit → shows data-quality checks and leakage checklist

## 5) CI Guidance
- Unit tests + 6-month sample integration test + notebook smoke via `nbclient`
- Commands:
  - `poetry run pytest -q`
  - `poetry run python -m nbclient notebooks/00_Control_Pipeline.ipynb --ExecutePreprocessor.enabled=True --allow-errors`

## 6) Data Contracts
- See `specs/001-dvol-forecasting-volatility/contracts/*.schema.json` and `policy.cutoff.yaml`
- All ETL adapters must conform to `CryptoDataDownloadAPI.txt`
