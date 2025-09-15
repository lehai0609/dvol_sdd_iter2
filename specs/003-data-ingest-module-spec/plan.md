# Implementation Plan: 01_data_ingest - DVOL Data Ingestion Pipeline

**Branch**: `003-data-ingest-module-spec` | **Date**: 2025-09-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/modules/01_data_ingest/spec.md`

## Execution Flow (/plan command scope)
```
✓ 1. Load feature spec from Input path → Feature spec loaded successfully
✓ 2. Fill Technical Context (scan for NEEDS CLARIFICATION) → Context filled with Python/Parquet stack
✓ 3. Evaluate Constitution Check section → Simplicity focused approach validated
✓ 4. Execute Phase 0 → research.md (Generated)
✓ 5. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md (Generated)
✓ 6. Re-evaluate Constitution Check → No violations after design
✓ 7. Plan Phase 2 → Task generation approach described
✓ 8. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

The 01_data_ingest module establishes a robust, daily ETL pipeline that pulls cryptocurrency data from CryptoDataDownload API endpoints (DVOL, options summaries, funding rates, futures OHLCV, and on-chain metrics) and stores them in partitioned Parquet format with strict UTC normalization and temporal controls to prevent data leakage in downstream modeling.

**Technical Approach**: Python-based ETL system using requests/httpx for API calls, pandas/pyarrow for data processing, Parquet for storage with asset/date partitioning, comprehensive retry logic, checksum validation, and monitoring dashboards for operational visibility.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pandas, pyarrow, requests, pydantic (schema validation), schedule (cron-like orchestration), typer (CLI)
**Storage**: Parquet files partitioned by asset and year-month, with optional PostgreSQL for metadata tracking
**Testing**: pytest with integration tests against actual API endpoints and mock responses
**Target Platform**: Linux server environment with scheduled execution (cron or systemd timers)
**Project Type**: single (focused data ingestion library with CLI interface)
**Performance Goals**: Process 5 data sources × 2 assets within 30 minutes, handle 2500-record API responses efficiently
**Constraints**: 00:00 UTC daily cut-off deadline, zero data leakage tolerance, deterministic checksums for reproducibility
**Scale/Scope**: ~10K records/day, 5 API endpoints, 2 assets (BTC/ETH), 1-year historical backfill capability

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Simplicity**:
- Projects: 1 (data ingestion pipeline with CLI)
- Using framework directly? Yes (pandas/pyarrow without wrapper classes)
- Single data model? Yes (common schema with asset-specific nullable fields)
- Avoiding patterns? Yes (direct API client, no Repository pattern overhead)

**Architecture**:
- EVERY feature as library? Yes (dvol_data_ingest library with CLI)
- Libraries listed:
  - `dvol_data_ingest`: Core ETL functionality (API clients, schema validation, Parquet I/O)
- CLI per library: `dvol-ingest --help/--version/--format` with commands: fetch, validate, backfill, status
- Library docs: llms.txt format planned for Claude Code integration

**Testing (NON-NEGOTIABLE)**:
- RED-GREEN-Refactor cycle enforced? Yes (test cases written first, must fail before implementation)
- Git commits show tests before implementation? Yes (commit strategy: tests → implementation → integration)
- Order: Contract→Integration→E2E→Unit strictly followed? Yes
- Real dependencies used? Yes (actual CDD API endpoints, real Parquet files)
- Integration tests for: API endpoint responses, schema validation, Parquet round-trip, checksum consistency
- FORBIDDEN: Implementation before test, skipping RED phase

**Observability**:
- Structured logging included? Yes (JSON logs with timestamp, source, asset, status fields)
- Frontend logs → backend? N/A (CLI-only tool)
- Error context sufficient? Yes (API response codes, data validation failures, file I/O errors)

**Versioning**:
- Version number assigned? 0.1.0 (MAJOR.MINOR.BUILD)
- BUILD increments on every change? Yes
- Breaking changes handled? Yes (schema migration plan, backward compatibility for Parquet readers)

## Project Structure

### Documentation (this feature)
```
specs/003-data-ingest-module-spec/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT)
src/dvol_data_ingest/
├── models/              # Pydantic schemas for API responses and Parquet tables
├── clients/             # CDD API client implementations
├── validators/          # Schema and data quality validation
├── storage/             # Parquet I/O and partitioning logic
├── utils/               # UTC normalization, checksum calculation
├── cli/                 # Typer-based CLI interface
└── __init__.py

tests/
├── contract/            # API response schema validation tests
├── integration/         # End-to-end pipeline tests with real APIs
├── unit/                # Component-level tests
└── fixtures/            # Mock API responses for testing

config/
├── schemas/             # JSON Schema definitions for validation
└── settings.yaml        # Default configuration (endpoints, timeouts, etc.)
```

**Structure Decision**: Option 1 (single project) - focused data ingestion tool without web/mobile complexity

## Phase 0: Outline & Research

**Research Tasks Completed**:

1. **CryptoDataDownload API Integration Patterns**
   - Decision: Use requests with session pooling and exponential backoff retry logic
   - Rationale: Proven reliability for API integrations, built-in timeout handling, extensive retry ecosystem
   - Alternatives considered: httpx (async), urllib3 (too low-level for this use case)

2. **Parquet Storage Optimization for Time Series**
   - Decision: PyArrow with row group size ~100MB, Snappy compression, partitioned by asset/year-month
   - Rationale: Optimal query performance for date range filters, efficient storage compression
   - Alternatives considered: Delta Lake (overkill), plain CSV (poor performance), HDF5 (not cloud-native)

3. **Schema Validation Strategy**
   - Decision: Pydantic for runtime validation with JSON Schema generation for documentation
   - Rationale: Type safety, validation error reporting, automatic documentation generation
   - Alternatives considered: Cerberus (less type safety), marshmallow (more complex), manual validation (error-prone)

4. **UTC Timestamp Normalization**
   - Decision: pandas.to_datetime() with utc=True, validate timezone-aware timestamps throughout pipeline
   - Rationale: Pandas built-in UTC handling prevents timezone bugs, explicit UTC enforcement
   - Alternatives considered: pytz (deprecated), dateutil (manual timezone handling), arrow (extra dependency)

5. **Checksum and Reproducibility**
   - Decision: SHA-256 hash of sorted row dictionary representations for deterministic checksums
   - Rationale: Platform-independent, deterministic ordering, detects any data changes
   - Alternatives considered: DataFrame hash (not deterministic), file hash (misses logical equivalence), CRC32 (collision risk)

**Output**: research.md with all technical decisions documented

## Phase 1: Design & Contracts

**Data Model Entities** (see data-model.md):
1. **DVOLRecord**: asset, date_utc, unix_ms, symbol, open, high, low, close + metadata
2. **OptionsSummaryRecord**: asset, date_utc, maturity_utc, greeks, volumes + metadata
3. **OHLCVRecord**: asset, symbol, date_utc, OHLCV data + metadata
4. **FundingRecord**: asset, symbol, date_utc, funding metrics + metadata
5. **OnChainRecord**: asset, date_utc, blockchain metrics + metadata
6. **IngestionMetadata**: data_source, ingestion_timestamp, checksum (common to all)

**API Contracts** (see contracts/):
- `/v1/data/ohlc/deribit/volatility` → DVOLRecord schema
- `/v1/data/summary/deribit/options/greeks/maturities/` → OptionsSummaryRecord schema
- `/v1/data/ohlc/deribit/futures/` → OHLCVRecord schema
- `/v1/data/ohlc/deribit/funding` → FundingRecord schema
- `/v1/data/summary/blockchain/blocks/` → OnChainRecord schema

**Contract Tests**: One test file per endpoint verifying request/response schema compliance

**Integration Test Scenarios**: Full pipeline test from API fetch → validation → Parquet write → checksum verification

**Agent Context Update**: CLAUDE.md updated with data ingestion context, API patterns, and troubleshooting guidance

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, CLAUDE.md

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `/templates/tasks-template.md` as base with data ingestion-specific context
- Generate tasks from Phase 1 design docs (API contracts, data models, CLI interface)
- Each API endpoint → contract test task [P] (can run in parallel)
- Each data model → Pydantic schema creation task [P]
- Each validation rule → validator implementation task
- Integration pipeline → end-to-end test scenario
- CLI commands → user acceptance test scenarios

**Ordering Strategy**:
- TDD order: Schema tests → Schema implementation → API client tests → API client implementation
- Dependency order: Models → Validators → API Clients → Storage → CLI → Integration
- Mark [P] for parallel execution where dependencies allow
- Critical path: UTC normalization and checksum logic (foundational for all downstream tasks)

**Estimated Output**: 30-35 numbered, ordered tasks covering:
- 5 API client implementations with retry logic
- 5 Pydantic schema definitions with validation rules
- Parquet I/O with partitioning strategy
- UTC timezone normalization utilities
- Checksum calculation and verification
- CLI interface with fetch/validate/backfill/status commands
- Integration tests for complete pipeline
- Monitoring and alerting setup
- Documentation and runbooks

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Work Items (Detailed Implementation Plan)

Following the specification requirements, here are the discrete activities needed for the data ingestion pipeline:

### 1. Build robust client connectors for CDD API endpoints
**Purpose**: Establish reliable HTTP connections to all 5 CryptoDataDownload endpoints with proper error handling, timeout configuration, and session management. This forms the foundation for all data acquisition and prevents pipeline failures due to network issues.
**Deliverables**:
- `CDDClient` base class with common authentication, headers, timeout handling
- Specialized clients for each endpoint: `DVOLClient`, `OptionsClient`, `FuturesClient`, `FundingClient`, `OnChainClient`
- Connection pooling and keep-alive configuration for efficiency
- Comprehensive logging of request/response cycles

### 2. Set up authentication and secure handling of API secrets
**Purpose**: Securely manage CryptoDataDownload API credentials to ensure authorized access while protecting sensitive information from exposure in logs, version control, or error messages.
**Deliverables**:
- Environment variable-based credential loading with validation
- API key rotation support (if required by CDD)
- Credential masking in all log outputs and error messages
- Integration with system credential stores (keyring) for production deployment

### 3. Define schemas and write automated validators
**Purpose**: Implement schema validators to ensure that every incoming file conforms to the expected column names, datatypes, and timestamp formats. This prevents downstream errors when features are built and ensures data quality consistency across all pipeline stages.
**Deliverables**:
- Pydantic schemas for all 5 data source response formats
- Field-level validation rules (numeric ranges, timestamp formats, required fields)
- Custom validators for domain-specific constraints (asset symbols, maturity dates)
- Schema version tracking and migration capabilities

### 4. Normalize all timestamps into UTC to respect the global cut-off rule
**Purpose**: Convert all timestamp fields from API responses into UTC timezone to ensure consistent temporal alignment across data sources and strict adherence to the 00:00 UTC modeling cut-off requirement. This prevents data leakage and temporal inconsistencies.
**Deliverables**:
- UTC conversion utilities for Unix timestamps (ms) and ISO date strings
- Timezone validation and normalization pipeline stage
- Date boundary enforcement (reject future timestamps beyond cut-off)
- Audit logging of all timestamp transformations

### 5. Implement incremental fetching logic that avoids re-pulling old data, combined with idempotent writes to Parquet
**Purpose**: Optimize API usage and processing time by only fetching new/updated records while ensuring that re-running the same ingestion produces identical results through idempotent storage operations.
**Deliverables**:
- Last-fetch tracking per data source and asset combination
- Incremental fetch logic with date range parameters
- Parquet file merging and deduplication based on primary keys
- Idempotency verification through checksum comparison

### 6. Add retry and backoff logic for failed API calls
**Purpose**: Implement exponential backoff with jitter for transient failures to handle temporary API downtime, rate limiting, or network issues without data loss, ensuring robust operation in production environments.
**Deliverables**:
- Configurable retry strategies (max attempts, backoff multipliers, jitter)
- Retry decision logic based on HTTP status codes and response patterns
- Circuit breaker pattern for persistent API failures
- Detailed failure logging and alerting integration

### 7. Perform "as-of" join audits to confirm that data from different sources align on the same trading date
**Purpose**: Validate that related data sources (e.g., DVOL, options, futures) maintain temporal consistency within the same trading day, preventing cross-contamination between different market dates.
**Deliverables**:
- Cross-source date alignment validation checks
- Trading day boundary definition and validation
- Gap detection and reporting for missing cross-source data
- Audit reports showing data freshness and alignment status

### 8. Partition Parquet storage by asset and date, with efficient file sizes
**Purpose**: Structure Parquet files by asset and year-month partitions to optimize query performance for downstream modeling while maintaining efficient file sizes (~100MB) for storage and I/O performance.
**Deliverables**:
- Partitioning strategy implementation (asset/year-month hierarchy)
- File size monitoring and optimization (target ~100MB per partition)
- Compression configuration (Snappy for balance of speed/size)
- Index and metadata generation for efficient querying

### 9. Compute and log checksums, row counts, and coverage metrics into a dashboard
**Purpose**: Generate comprehensive data quality and completeness metrics including row-level checksums for reproducibility verification, coverage tracking across all data sources, and operational visibility through monitoring dashboards.
**Deliverables**:
- SHA-256 checksum calculation for individual records and complete datasets
- Row count and completeness tracking per data source and date
- Data quality metrics (missing values, outliers, schema violations)
- Dashboard integration for real-time monitoring and historical trends

### 10. Develop a freshness monitor that alerts if data are missing or stale
**Purpose**: Implement automated monitoring to detect when data ingestion fails or when source data becomes stale beyond acceptable thresholds, ensuring timely alerts for operational intervention.
**Deliverables**:
- Data freshness tracking with configurable staleness thresholds
- Missing data detection across all required data sources and dates
- Alert system integration (email, Slack, PagerDuty) for operational teams
- SLA compliance reporting and trend analysis

## Definition of Done (DoD)

The 01_data_ingest module is considered complete when ALL of the following criteria are met:

### Operational Criteria
- [ ] **Pipeline runs successfully for at least one continuous week**, ingesting all required datasets daily without manual intervention
- [ ] **All 5 data sources (DVOL, options, futures, funding, on-chain) ingest daily** for both BTC and ETH (where applicable)
- [ ] **00:00 UTC cut-off deadline is consistently met** with processing completing before the daily modeling window

### Quality Criteria
- [ ] **All acceptance criteria from the specification (AC-001 through AC-023) are tested automatically and pass** without manual verification
- [ ] **Schema validation catches 100% of malformed API responses** with appropriate error logging and handling
- [ ] **UTC timestamp normalization is verified** for all timestamp fields across all data sources
- [ ] **Checksum verification confirms deterministic processing** - re-ingesting the same date produces identical checksums

### Reproducibility Criteria
- [ ] **Historical data can be re-ingested reproducibly with identical outputs** (deterministic rebuild capability verified)
- [ ] **Incremental and full refresh modes both produce consistent results** for overlapping date ranges
- [ ] **All processing steps are deterministic and reproducible** across different environments (dev, staging, prod)

### Operational Readiness
- [ ] **Operational runbook exists** that explains how to restart, repair, or troubleshoot the pipeline in case of failure
- [ ] **Monitoring dashboards show data freshness, completeness, and quality metrics** with configurable alerting
- [ ] **Failure recovery procedures are documented and tested** including API downtime, partial data scenarios, and storage issues
- [ ] **Performance benchmarks are established** showing processing time and resource usage for historical backfill and daily operations

### Testing Completeness
- [ ] **Integration tests pass against actual CDD API endpoints** using real credentials and live data
- [ ] **Contract tests verify all API endpoint schemas** and handle schema evolution gracefully
- [ ] **End-to-end tests cover the complete pipeline** from API fetch through Parquet storage and checksum verification
- [ ] **Failure scenario tests validate recovery behavior** for network failures, API errors, and storage issues

## Risks and Mitigations

### API and External Dependencies
**Risk**: CryptoDataDownload API downtime or rate limiting blocks daily ingestion
**Impact**: Missing data that cannot be recovered if outside historical availability window
**Mitigation**:
- Implement exponential backoff retry with 24-hour persistence for critical failures
- Cache last successful API responses as fallback data for brief outages
- Establish monitoring alerts for API availability with 15-minute resolution
- Negotiate SLA terms with CryptoDataDownload including historical data recovery guarantees

**Risk**: Schema changes at the data provider break ingestion pipeline
**Impact**: Pipeline failures and potential data corruption if field mappings become invalid
**Mitigation**:
- Version all schema definitions with backward compatibility checks
- Implement schema evolution detection with automatic alerts to engineering team
- Maintain schema version history to support rollback scenarios
- Test schema validation against known good and malformed sample responses

### Data Quality and Temporal Consistency
**Risk**: Timezone misalignment causes data leakage between trading days
**Impact**: Future information contaminates forecasts, invalidating model predictions
**Mitigation**:
- Implement strict UTC enforcement at ingestion boundary with validation checks
- Add audit logging for all timestamp transformations with before/after values
- Create automated tests for timezone edge cases (DST transitions, leap seconds)
- Establish "as-of" join validation across all data sources

**Risk**: Gaps in historical data coverage prevent complete model training datasets
**Impact**: Reduced model accuracy and incomplete backtesting capabilities
**Mitigation**:
- Implement gap detection with categorized reason codes (API downtime, market holidays, data provider issues)
- Maintain inventory of data availability by source and date range
- Establish data recovery procedures with CryptoDataDownload for historical gap-filling
- Create fallback data sources or interpolation strategies for non-critical gaps

### Storage and Performance
**Risk**: Parquet file corruption or storage failures cause data loss
**Impact**: Pipeline failures and inability to recover without re-ingesting from source
**Mitigation**:
- Implement atomic writes with temporary staging and atomic move operations
- Maintain checksums for all Parquet files with integrity verification on read
- Establish backup and replication strategy for critical data partitions
- Test recovery procedures from corrupted or missing Parquet files

**Risk**: Storage space exhaustion blocks new data ingestion
**Impact**: Pipeline failures and accumulating data backlog that may exceed API historical limits
**Mitigation**:
- Monitor disk usage with automated alerts at 80% and 90% capacity thresholds
- Implement data retention policies for non-critical historical data
- Establish storage scaling procedures for rapid capacity expansion
- Create data archival strategy for long-term historical data preservation

### Operational and Monitoring
**Risk**: Pipeline failures go undetected, causing accumulated data gaps
**Impact**: Degraded model performance due to missing training data
**Mitigation**:
- Implement comprehensive monitoring with data freshness and completeness checks
- Create escalation procedures for different failure severities (missing data, quality issues, complete failures)
- Establish 24/7 alerting for critical pipeline failures with clear remediation procedures
- Maintain pipeline health dashboard with SLA compliance tracking

## Owner(s)

**Data Engineer**: Responsible for core pipeline implementation, API integrations, storage design, and monitoring setup
**DevOps Engineer**: Responsible for deployment automation, infrastructure provisioning, monitoring platform integration, and production support
**Quantitative Researcher**: Responsible for data quality validation, schema verification, and acceptance criteria testing from modeling perspective

## Timeline

### Days 1-2: Foundation and API Integration
**Owner**: Data Engineer
**Focus**: Build and test CDD API clients with authentication
**Deliverables**:
- CDD API client library with authentication handling
- Initial contract tests for all 5 endpoints (failing tests first)
- Basic retry logic and error handling framework
- Secure credential management system

**Dependencies**: CryptoDataDownload API credentials and endpoint documentation
**Risk**: API access issues or undocumented rate limits

### Days 3-4: Schema and Data Validation
**Owner**: Data Engineer + Quantitative Researcher
**Focus**: Implement schema validation and timestamp normalization
**Deliverables**:
- Pydantic schemas for all data source response formats
- UTC timestamp normalization with validation
- Schema validation test suite covering edge cases
- Data quality validation rules implementation

**Dependencies**: Complete API response samples from Days 1-2
**Risk**: Schema complexity exceeding initial estimates

### Days 5-6: Storage and Idempotency
**Owner**: Data Engineer
**Focus**: Add retry/backoff logic and idempotent write logic
**Deliverables**:
- Parquet storage with asset/date partitioning
- Incremental fetch logic with deduplication
- Checksum calculation and verification system
- Idempotent write operations with atomic updates

**Dependencies**: Schema validation from Days 3-4
**Risk**: Parquet partitioning performance issues with large datasets

### Days 7-8: Integration and Monitoring
**Owner**: Data Engineer + DevOps Engineer
**Focus**: Set up as-of join audits and Parquet partitioning
**Deliverables**:
- Cross-source temporal alignment validation
- Comprehensive monitoring dashboard
- Data freshness and completeness tracking
- Alert system integration with operational procedures

**Dependencies**: Complete data flow from previous phases
**Risk**: Monitoring integration complexity with existing infrastructure

### Days 9-10: Testing and Production Readiness
**Owner**: All team members
**Focus**: Build monitoring dashboards, run full end-to-end test, and finalize runbook
**Deliverables**:
- Complete end-to-end integration test with historical data
- Operational runbook with troubleshooting procedures
- Performance benchmarking and optimization
- Production deployment and handover to operations team

**Dependencies**: All previous deliverables integrated and tested
**Risk**: Integration issues requiring design changes

**Critical Path**: API authentication → Schema validation → UTC normalization → Parquet storage → Integration testing
**Parallel Work Opportunities**: Schema development can proceed with API integration, monitoring setup can proceed with storage implementation

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

No constitutional violations identified. The design follows simplicity principles with:
- Single project focus (data ingestion only)
- Direct use of pandas/pyarrow without wrapper abstractions
- Library-first architecture with CLI interface
- Comprehensive testing strategy following TDD principles

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none required)

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*