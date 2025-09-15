# Tasks: 01_data_ingest - DVOL Data Ingestion Pipeline

**Input**: Design documents from `/specs/003-data-ingest-module-spec/`
**Prerequisites**: plan.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

## Execution Flow (main)
```
✓ 1. Load plan.md from feature directory → Tech stack: Python 3.11+, pandas, pyarrow, pydantic, requests, typer
✓ 2. Load design documents:
   → data-model.md: 5 entities extracted (DVOLRecord, OptionsSummaryRecord, OHLCVRecord, FundingRecord, OnChainRecord)
   → contracts/: 2 API contract files (DVOL, Options) + 3 more endpoints needed
   → research.md: Technical decisions for setup and implementation
✓ 3. Generate tasks by category: Setup → Tests → Core → Integration → Polish
✓ 4. Apply TDD rules: All tests before implementation
✓ 5. Number tasks sequentially (T001-T035)
✓ 6. Mark parallel tasks [P] for different files
✓ 7. Create dependency graph and execution examples
✓ 8. Validate completeness: 5 API endpoints, 5 data models, CLI commands, integration tests
✓ 9. Return: SUCCESS (35 tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions
- All paths relative to repository root

## Path Conventions
**Single project structure** (from plan.md):
- **Source**: `src/dvol_data_ingest/`
- **Tests**: `tests/` (contract/, integration/, unit/, fixtures/)
- **Config**: `config/` (schemas/, settings.yaml)

## Phase 3.1: Setup & Project Infrastructure

- [x] **T001** Create Python project structure per implementation plan: `src/dvol_data_ingest/` with subdirectories (models/, clients/, validators/, storage/, utils/, cli/), `tests/` with subdirectories (contract/, integration/, unit/, fixtures/), `config/` with subdirectories (schemas/)

- [x] **T002** Initialize Python project with pyproject.toml: dependencies (pandas>=2.0, pyarrow>=10.0, requests>=2.28, pydantic>=2.0, typer>=0.9, schedule>=1.2), dev dependencies (pytest>=7.0, pytest-mock, pytest-asyncio, black, ruff), project metadata and entry points

- [x] **T003** [P] Configure development tools: `.pre-commit-hooks.yaml` with black, ruff, pytest; `.gitignore` for Python, data files, logs; `ruff.toml` for linting rules; `pytest.ini` for test configuration

- [x] **T004** [P] Create environment configuration template: `.env.example` with CDD_API_BASE_URL, CDD_API_KEY, DATA_ROOT_PATH, LOG_LEVEL, PARQUET_COMPRESSION settings; `config/settings.yaml` with default API endpoints, timeouts, retry settings

- [x] **T005** [P] Initialize logging configuration: `src/dvol_data_ingest/utils/logging.py` with structured JSON logging, configurable levels, file rotation; log format matching specification requirements

## Phase 3.2: Contract Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

 - [x] **T006** [P] Contract test DVOL API endpoint: `tests/contract/test_dvol_contract.py` - validate `/v1/data/ohlc/deribit/volatility` response schema matches `contracts/dvol_api_contract.json`, test required fields (Date, Unix, Symbol, Open, High, Low, Close), test BTC/ETH symbol validation

 - [x] **T007** [P] Contract test Options API endpoint: `tests/contract/test_options_contract.py` - validate `/v1/data/summary/deribit/options/greeks/maturities/` response schema matches `contracts/options_api_contract.json`, test all greeks fields, maturity validation

 - [x] **T008** [P] Contract test Futures OHLCV API: `tests/contract/test_futures_contract.py` - validate `/v1/data/ohlc/deribit/futures/` response schema, test Volume→volume_base mapping, test Base Volume→volume_usd mapping, test asset extraction from symbol

 - [x] **T009** [P] Contract test Funding API: `tests/contract/test_funding_contract.py` - validate `/v1/data/ohlc/deribit/funding` response schema, test BTC-PERPETUAL/ETH-PERPETUAL symbols, test interest rate fields

 - [x] **T010** [P] Contract test OnChain API: `tests/contract/test_onchain_contract.py` - validate `/v1/data/summary/blockchain/blocks/` response schema, test ETH-specific nullable fields for BTC data, test required vs optional fields

- [x] **T011** [P] Schema validation tests: `tests/contract/test_pydantic_schemas.py` - test all 5 Pydantic response models (DVOLApiResponse, OptionsSummaryApiResponse, FuturesOHLCVApiResponse, FundingRatesApiResponse, OnChainDataApiResponse) with valid/invalid data

## Phase 3.3: Data Model Implementation (ONLY after contract tests are failing)

- [x] **T012** [P] DVOL API response model: `src/dvol_data_ingest/models/api_responses.py` - implement `DVOLApiResponse` with field validation, Unix timestamp validation, Symbol enum (BTC/ETH), OHLC positive value constraints

- [x] **T013** [P] Options API response model: extend `src/dvol_data_ingest/models/api_responses.py` - implement `OptionsSummaryApiResponse` with maturity date validation, delta/gamma/vega/theta fields, volume constraints, IV range validation (0-5)

- [x] **T014** [P] Futures API response model: extend `src/dvol_data_ingest/models/api_responses.py` - implement `FuturesOHLCVApiResponse` with asset extraction computed field, Volume/Base Volume mapping, symbol validation

- [x] **T015** [P] Funding API response model: extend `src/dvol_data_ingest/models/api_responses.py` - implement `FundingRatesApiResponse` with perpetual symbol validation, interest rate fields, asset extraction

- [x] **T016** [P] OnChain API response model: extend `src/dvol_data_ingest/models/api_responses.py` - implement `OnChainDataApiResponse` with ETH-specific field validation, symbol case normalization, blockchain metrics validation

- [x] **T017** [P] Storage data models: `src/dvol_data_ingest/models/storage.py` - implement all 5 storage models (DVOLRecord, OptionsSummaryRecord, OHLCVRecord, FundingRecord, OnChainRecord) with metadata fields (data_source, ingestion_timestamp, checksum)

- [x] **T018** [P] Common metadata model: extend `src/dvol_data_ingest/models/storage.py` - implement `IngestionMetadata` base class with checksum calculation, pipeline version tracking, API response timestamp handling

## Phase 3.4: API Client Implementation

- [ ] **T019** [P] Base API client: `src/dvol_data_ingest/clients/base.py` - implement `CDDClient` base class with session management, authentication handling, timeout configuration, exponential backoff retry logic, rate limiting

- [ ] **T020** [P] DVOL client: `src/dvol_data_ingest/clients/dvol.py` - implement `DVOLClient` inheriting from CDDClient, handle symbol parameter (BTC/ETH), enddate parameter, limit parameter, response parsing to DVOLApiResponse

- [ ] **T021** [P] Options client: `src/dvol_data_ingest/clients/options.py` - implement `OptionsClient` for options summary endpoint, handle underlying parameter (BTC/ETH), parse response to OptionsSummaryApiResponse list

- [ ] **T022** [P] Futures client: `src/dvol_data_ingest/clients/futures.py` - implement `FuturesClient` for futures OHLCV, handle perpetual and dated futures symbols, parse response to FuturesOHLCVApiResponse

- [ ] **T023** [P] Funding client: `src/dvol_data_ingest/clients/funding.py` - implement `FundingClient` for funding rates, handle perpetual symbols only (BTC-PERPETUAL, ETH-PERPETUAL), parse to FundingRatesApiResponse

- [ ] **T024** [P] OnChain client: `src/dvol_data_ingest/clients/onchain.py` - implement `OnChainClient` for blockchain data, handle btc/eth lowercase symbols, parse to OnChainDataApiResponse with proper ETH field handling

## Phase 3.5: Data Processing & Validation

- [ ] **T025** [P] UTC normalization utility: `src/dvol_data_ingest/utils/datetime.py` - implement UTC timestamp conversion from Unix milliseconds, ISO date string parsing, timezone validation, 00:00 UTC cutoff enforcement

- [ ] **T026** [P] Checksum calculation utility: `src/dvol_data_ingest/utils/checksum.py` - implement deterministic SHA-256 hash calculation for records, sorted dictionary representation, JSON canonical encoding for platform independence

- [ ] **T027** [P] Schema validators: `src/dvol_data_ingest/validators/schema.py` - implement validation pipeline for API responses, field type checking, range validation, cross-field validation (e.g., maturity > date)

- [ ] **T028** [P] Data quality validators: `src/dvol_data_ingest/validators/quality.py` - implement outlier detection, completeness checking, temporal consistency validation, cross-source alignment checks

## Phase 3.6: Storage Engine

- [ ] **T029** [P] Parquet storage engine: `src/dvol_data_ingest/storage/parquet.py` - implement partitioned Parquet writing by asset/year-month, row group size optimization (~100MB), Snappy compression, atomic writes with staging

- [ ] **T030** [P] State management: `src/dvol_data_ingest/storage/state.py` - implement last-fetch tracking per (data_source, asset), state persistence in JSON format, incremental fetch logic, state validation and recovery

## Phase 3.7: CLI Interface

- [ ] **T031** CLI main application: `src/dvol_data_ingest/cli/main.py` - implement Typer-based CLI with commands: fetch, validate, backfill, status, run-daily, test-connection; argument parsing, error handling, progress reporting

- [ ] **T032** CLI fetch command: extend `src/dvol_data_ingest/cli/main.py` - implement fetch command with source selection (dvol, options, futures, funding, onchain), asset selection (BTC, ETH), date range parameters, incremental vs full refresh

## Phase 3.8: Integration & End-to-End

- [ ] **T033** Integration test pipeline: `tests/integration/test_pipeline.py` - implement full end-to-end test from API fetch → validation → Parquet storage → checksum verification, test with real CDD API endpoints, test error scenarios

- [ ] **T034** Integration test data flow: `tests/integration/test_data_flow.py` - implement cross-source temporal alignment tests, "as-of" join validation, gap detection tests, state management tests with incremental updates

## Phase 3.9: Polish & Documentation

- [ ] **T035** [P] Unit tests completion: `tests/unit/` - implement comprehensive unit tests for all utility functions (datetime conversion, checksum calculation), validator functions, storage operations, state management

## Dependencies

**Phase Dependencies**:
- Setup (T001-T005) → Contract Tests (T006-T011) → Models (T012-T018) → Clients (T019-T024) → Processing (T025-T028) → Storage (T029-T030) → CLI (T031-T032) → Integration (T033-T034) → Polish (T035)

**Critical Path**:
- T001-T002 (project setup) blocks everything
- T006-T011 (contract tests) must fail before T012-T018 (models)
- T012-T018 (models) blocks T019-T024 (clients)
- T025-T030 (processing/storage) required for T031-T032 (CLI)
- T031-T032 (CLI) required for T033-T034 (integration tests)

**Parallel Execution Opportunities**:
- T003-T005 can run in parallel after T002
- T006-T011 can all run in parallel (different contract files)
- T012-T018 can run in parallel (different model files)
- T019-T024 can run in parallel (different client files)
- T025-T028 can run in parallel (different utility modules)

## Parallel Execution Examples

### Contract Tests (after T005 complete):
```bash
# Launch T006-T011 together:
Task: "Contract test DVOL API endpoint in tests/contract/test_dvol_contract.py"
Task: "Contract test Options API endpoint in tests/contract/test_options_contract.py"
Task: "Contract test Futures OHLCV API in tests/contract/test_futures_contract.py"
Task: "Contract test Funding API in tests/contract/test_funding_contract.py"
Task: "Contract test OnChain API in tests/contract/test_onchain_contract.py"
Task: "Schema validation tests in tests/contract/test_pydantic_schemas.py"
```

### API Response Models (after T011 complete):
```bash
# Launch T012-T016 together:
Task: "DVOL API response model in src/dvol_data_ingest/models/api_responses.py"
Task: "Options API response model in src/dvol_data_ingest/models/api_responses.py"
Task: "Futures API response model in src/dvol_data_ingest/models/api_responses.py"
Task: "Funding API response model in src/dvol_data_ingest/models/api_responses.py"
Task: "OnChain API response model in src/dvol_data_ingest/models/api_responses.py"
```

### API Clients (after T018 complete):
```bash
# Launch T020-T024 together (after T019 base client):
Task: "DVOL client in src/dvol_data_ingest/clients/dvol.py"
Task: "Options client in src/dvol_data_ingest/clients/options.py"
Task: "Futures client in src/dvol_data_ingest/clients/futures.py"
Task: "Funding client in src/dvol_data_ingest/clients/funding.py"
Task: "OnChain client in src/dvol_data_ingest/clients/onchain.py"
```

### Processing Utilities (after T024 complete):
```bash
# Launch T025-T028 together:
Task: "UTC normalization utility in src/dvol_data_ingest/utils/datetime.py"
Task: "Checksum calculation utility in src/dvol_data_ingest/utils/checksum.py"
Task: "Schema validators in src/dvol_data_ingest/validators/schema.py"
Task: "Data quality validators in src/dvol_data_ingest/validators/quality.py"
```

## API Endpoints Coverage

**5 CryptoDataDownload Endpoints**:
1. **DVOL OHLC**: `/v1/data/ohlc/deribit/volatility` (T006, T012, T020)
2. **Options Summary**: `/v1/data/summary/deribit/options/greeks/maturities/` (T007, T013, T021)
3. **Futures OHLCV**: `/v1/data/ohlc/deribit/futures/` (T008, T014, T022)
4. **Funding Rates**: `/v1/data/ohlc/deribit/funding` (T009, T015, T023)
5. **OnChain Data**: `/v1/data/summary/blockchain/blocks/` (T010, T016, T024)

## Data Models Coverage

**5 API Response Models**: DVOLApiResponse, OptionsSummaryApiResponse, FuturesOHLCVApiResponse, FundingRatesApiResponse, OnChainDataApiResponse

**5 Storage Models**: DVOLRecord, OptionsSummaryRecord, OHLCVRecord, FundingRecord, OnChainRecord

**Metadata**: IngestionMetadata common to all storage models

## CLI Commands Coverage

- `dvol-ingest fetch` - Fetch data from specific sources and assets
- `dvol-ingest validate` - Run data quality validation checks
- `dvol-ingest backfill` - Historical data backfill operations
- `dvol-ingest status` - Pipeline status and data freshness reporting
- `dvol-ingest run-daily` - Complete daily ingestion cycle
- `dvol-ingest test-connection` - API connectivity testing

## Validation Checklist
*GATE: All items must be checked before task execution*

- [x] All 5 API endpoints have corresponding contract tests (T006-T010)
- [x] All 5 data models have implementation tasks (T012-T016 API, T017 storage)
- [x] All contract tests come before model implementation (T006-T011 → T012-T018)
- [x] Parallel tasks [P] are truly independent (different files)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] TDD enforced: contract tests must fail before implementation
- [x] Integration tests cover end-to-end pipeline (T033-T034)
- [x] CLI provides all required commands from specification
- [x] Storage engine handles Parquet partitioning requirements
- [x] UTC normalization and checksum requirements covered

## Notes

- **TDD Enforcement**: Contract tests (T006-T011) MUST fail before any model implementation
- **Parallel Execution**: [P] tasks can run simultaneously using Task agent
- **File Dependencies**: Tasks modifying the same file must run sequentially
- **Commit Strategy**: Commit after each task completion for atomic progress tracking
- **Error Handling**: Each task includes comprehensive error handling and logging
- **Performance**: Target 30-minute processing window for daily operations
- **Quality Gates**: All acceptance criteria from specification must pass

**SUCCESS CRITERIA**: When all 35 tasks are complete, the system should pass all acceptance criteria (AC-001 through AC-023) and be ready for production deployment with daily scheduled execution.
