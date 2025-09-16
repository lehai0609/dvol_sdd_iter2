# Implementation Plan: DVOL Forecasting & Volatility Trading (BTC primary, ETH optional)

Branch: `001-dvol-forecasting-volatility` | Date: 2025-09-15 | Spec: d:\Document\OneDrive\10_Works\GitHub\dvol_sdd_iter2\specs\001-dvol-forecasting-volatility\spec.md
Input: Feature specification from `/specs/001-dvol-forecasting-volatility/spec.md`

## Summary
Goal: deliver daily end-of-day forecasts of ΔDVOL for BTC (primary) and optionally ETH at 1d/7d/14d horizons, plus a stance mapping for DVOL futures or options, with strict anti-leakage and governance artifacts. Approach: single-library Python project with TDD, pure functions and explicit data contracts; daily ETL from CryptoDataDownload (CDD) to Parquet; leak-safe feature builders; walk-forward models (HAR baseline, linear, GBDT, optional LSTM); trade mapping with explicit cost and guardrails; one orchestrating Jupyter notebook as the only UI.

## Technical Context
- Language/Version: Python 3.11.9
- Primary Dependencies: pandas, numpy, pyarrow, scikit-learn, lightgbm, xgboost, statsmodels, torch (optional), matplotlib, requests, pydantic, pandera, loguru, rich, nbclient, hypothesis (dev)
- Storage: Local Parquet (partitioned by `asset/date`) under `data/{raw,staging,features}/`; artifacts under `artifacts/{models,reports}/`
- Testing: pytest, hypothesis, nbclient (smoke-run notebook)
- Target Platform: Local dev and CI on Windows; UTC processing only
- Project Type: Single project (library-first) with tests and one notebook UI
- Performance Goals: Daily ETL and feature build for BTC/ETH under minutes; training on small windows in CI under ~5–10 minutes
- Constraints: Strict anti-leakage; 00:00 UTC cut-off discipline; single notebook UI (no CLI); TDD with failing tests first; small, typed, pure functions
- Scale/Scope: 2 assets (BTC mandatory, ETH optional), daily cadence; backtest initial window small for CI; expandable later

## Constitution Check
Simplicity
- Projects: 1 (src + tests + notebooks); no extra services
- Using frameworks directly: yes (sklearn/lightgbm/statsmodels directly)
- Single data model: yes (explicit table schemas; no DTO indirection beyond pydantic/pandera validation)
- Avoiding patterns: yes (no repositories/UoW; YAGNI)

Architecture
- Every feature as library: yes, all logic lives in `src/` importable by tests and notebook
- Libraries listed: 
  - `dvol_data`: IO, ETL adapters, validation, data contracts
  - `features`: leak-safe feature functions
  - `models`: baselines, trees, optional sequence
  - `backtest`: stance mapping, costs, hedging simulators
  - `metrics`: evaluation metrics and reporting
- CLI per library: intentionally NO CLI (project constraint); single Jupyter notebook is the UI
- Library docs: contracts and quickstart documented in `specs/...`

Testing (NON-NEGOTIABLE)
- Red-Green-Refactor: enforced; unit tests and property tests precede implementation
- Commits: tests added before impl in PRs (project rule)
- Order: Contract → Integration → E2E (notebook smoke) → Unit (continuous)
- Real deps: real CDD schemas used; network calls stubbed for CI; Parquet I/O used
- Integration tests: sample 6-month slice covering ETL → features → model → mapping

Observability
- Structured logging via `loguru`; audit metadata (row counts, ranges, checksums) recorded alongside Parquet partitions

Versioning
- Project version in `pyproject.toml` (0.1.0). Breaking changes tracked via spec updates; artifacts versioned by date/run-id

## Project Structure

Documentation (this feature)
```
specs/001-dvol-forecasting-volatility/
├── plan.md              # This file
├── research.md          # Phase 0 output (this plan run)
├── data-model.md        # Phase 1 output (this plan run)
├── quickstart.md        # Phase 1 output (this plan run)
└── contracts/           # Phase 1 output (this plan run)
```

Source Code (repository root)
```
src/
  dvol_data/
  features/
  models/
  backtest/
  metrics/
tests/
  data/
  features/
  models/
  backtest/
  metrics/
notebooks/
  00_Control_Pipeline.ipynb  # Single UI (to be added during implementation)
data/{raw,staging,features}/
artifacts/{models,reports}/
```

Structure Decision: Single project (DEFAULT) with domain-oriented subpackages; one notebook UI, no CLI.

## Phase 0: Outline & Research
Unknowns and decisions were addressed in `research.md`:
- CDD canonical reference file path in repo is `CryptoDataDownloadAPI.txt` (use this exact filename)
- Staging tables: exact columns and dtypes defined; mapping rules for CDD field name variants (e.g., `base_volume` vs `volume_usd`)
- Uncertainty: standardize on quantile regression for trees; LSTM optional with MC-dropout as ablation
- Threshold calibration: net-of-cost grid search with walk-forward inner validation; ensure monotone risk/size rules
- ETH enablement gate: data availability flags and liquidity checks

Output: see `research.md` for decisions, rationale, and alternatives.

## Phase 1: Design & Contracts
Artifacts created by this plan run:
- `data-model.md`: Entities, fields, dtypes, validation rules, relationships
- `contracts/`: JSON Schemas for raw/staging/feature/label/forecast tables; cut-off policy YAML
- `quickstart.md`: Environment setup, TDD workflow, CI smoke guidance

Contract tests will be generated in implementation via pytest to validate schemas against golden samples; notebook smoke test will use `nbclient` in CI.

## Phase 2: Task Planning Approach
Task Generation Strategy
- Start from `templates/tasks-template.md`
- Derive tasks from data-model and contracts: one test file per contract; integration tests for ETL → features → model → mapping; notebook smoke test

Ordering Strategy
- TDD order: tests before implementation
- Dependency order: data contracts → ETL → features → models → mapping → metrics → notebook orchestration
- Parallelizable: independent test files per module [P]

Estimated Output: ~28 tasks in `tasks.md` (created by /tasks in next step)

## Complexity Tracking
- No deviations from simplicity; CLI intentionally omitted per requirements

## Progress Tracking
Phase Status:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - tasks.md generated)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

Gate Status:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented
