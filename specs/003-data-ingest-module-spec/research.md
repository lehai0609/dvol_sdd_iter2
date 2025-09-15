# Research: Data Ingestion Technical Decisions

**Feature**: 01_data_ingest - DVOL Data Ingestion Pipeline
**Date**: 2025-09-14
**Status**: Complete

## Research Context

This research resolves technical unknowns for the DVOL data ingestion pipeline, focusing on reliable API integration, efficient time-series storage, robust schema validation, temporal consistency, and reproducible processing.

## Technical Decisions

### 1. CryptoDataDownload API Integration Strategy

**Decision**: Use `requests` library with session pooling, exponential backoff retry logic, and connection keep-alive

**Rationale**:
- Proven reliability for financial data APIs with extensive retry ecosystem
- Built-in timeout and connection pooling for production resilience
- Synchronous execution model fits daily batch processing requirements
- Extensive middleware ecosystem for authentication and monitoring integration

**Alternatives Considered**:
- `httpx`: Async capabilities unnecessary for batch processing, additional complexity
- `urllib3`: Too low-level, requires implementing retry/session logic manually
- `aiohttp`: Async overkill for sequential daily ingestion, complicates error handling

**Implementation Notes**:
- Configure session with `pool_connections=10, pool_maxsize=20` for endpoint variety
- Use `urllib3.Retry` with `backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]`
- Set `timeout=(10, 30)` for connection and read timeouts respectively

### 2. Time-Series Storage Optimization

**Decision**: PyArrow Parquet with row group size ~100MB, Snappy compression, partitioned by asset/year-month

**Rationale**:
- Columnar format optimizes query performance for date range filters typical in financial modeling
- Snappy compression provides optimal balance between compression ratio and read/write speed
- Asset/year-month partitioning aligns with typical analysis patterns (monthly rolling windows)
- PyArrow provides robust metadata handling and schema evolution support

**Alternatives Considered**:
- Delta Lake: Overkill for read-heavy analytical workload, adds operational complexity
- Plain CSV: Poor query performance, no schema enforcement, large storage footprint
- HDF5: Not cloud-native, less ecosystem support, complex hierarchical structure unnecessary

**Implementation Notes**:
- Target row group size: ~100MB (approximately 1M rows for typical financial data)
- Partition hierarchy: `asset=BTC/year=2024/month=01/data.parquet`
- Schema metadata includes ingestion timestamp and checksum for auditing
- Enable dictionary encoding for categorical fields (asset, symbol, data_source)

### 3. Schema Validation Framework

**Decision**: Pydantic v2 for runtime validation with JSON Schema generation for API documentation

**Rationale**:
- Type safety with Python type hints prevents runtime errors
- Validation error reporting provides actionable debugging information
- Automatic JSON Schema generation for API contract documentation
- Performance optimized with Rust core (pydantic-core) for high-throughput validation

**Alternatives Considered**:
- Cerberus: Less type safety, manual schema definition, weaker error reporting
- Marshmallow: More complex setup, slower performance, heavier serialization focus
- Manual validation: Error-prone, maintenance overhead, no automatic documentation

**Implementation Notes**:
- Use `Field(...)` for validation constraints: `Field(gt=0)` for positive values
- Custom validators for domain logic: asset symbol validation, timestamp boundary checks
- Generate JSON Schema with `model.model_json_schema()` for API documentation
- Enable strict mode to reject unexpected fields from API responses

### 4. UTC Timestamp Normalization

**Decision**: `pandas.to_datetime()` with `utc=True` parameter, validate timezone-aware timestamps throughout pipeline

**Rationale**:
- Pandas built-in UTC handling prevents common timezone conversion bugs
- Explicit UTC enforcement ensures consistent temporal alignment across data sources
- Timezone-aware timestamps prevent accidental local time assumptions
- Integration with pandas datetime index for efficient time series operations

**Alternatives Considered**:
- pytz: Now deprecated in favor of zoneinfo, additional dependency
- dateutil: Manual timezone handling, more error-prone than pandas built-ins
- arrow: Extra dependency for minimal benefit over pandas datetime functionality

**Implementation Notes**:
- Convert Unix timestamps: `pd.to_datetime(df['unix_ms'], unit='ms', utc=True)`
- Validate all datetime columns are timezone-aware with `dt.tz` checks
- Enforce UTC timezone: `df['date_utc'] = df['date_utc'].dt.tz_convert('UTC')`
- Reject timestamps after 00:00 UTC cut-off with validation decorator

### 5. Deterministic Checksums for Reproducibility

**Decision**: SHA-256 hash of sorted row dictionary representations for deterministic record-level checksums

**Rationale**:
- Platform-independent hash calculation ensures cross-environment consistency
- Sorted dictionary representation provides deterministic ordering regardless of insertion sequence
- SHA-256 provides sufficient collision resistance for data integrity verification
- Record-level checksums enable precise identification of data changes

**Alternatives Considered**:
- DataFrame hash: Not deterministic across pandas versions, sensitive to ordering
- File hash: Misses logical data equivalence, sensitive to Parquet format changes
- CRC32: Higher collision probability inappropriate for financial data integrity

**Implementation Notes**:
- Sort dictionary keys before hashing: `sorted(record.dict().items())`
- Use JSON canonical representation: `json.dumps(sorted_dict, sort_keys=True)`
- Hash UTF-8 encoded JSON: `hashlib.sha256(json_str.encode('utf-8')).hexdigest()`
- Store checksums in metadata columns for audit trail and validation

### 6. Incremental Data Fetching Strategy

**Decision**: State tracking with last-fetch timestamps per (data_source, asset) combination, using API enddate parameters

**Rationale**:
- Minimizes API calls and processing time by fetching only new data
- Respects API rate limits by avoiding unnecessary historical data re-fetching
- Maintains state persistence to handle pipeline restarts and failures
- Leverages CDD API `enddate` parameter for precise date range control

**Implementation Notes**:
- Store state in `state/last_fetch.json`: `{"{source}_{asset}": "2024-01-15"}`
- Use `enddate` parameter to fetch from last successful date forward
- Handle missing state gracefully by fetching recent history (default 30 days)
- Validate incremental data overlaps with existing data for gap detection

### 7. API Rate Limiting and Circuit Breaker Pattern

**Decision**: Exponential backoff with jitter and circuit breaker for persistent API failures

**Rationale**:
- Prevents API rate limit violations that could result in temporary bans
- Circuit breaker pattern protects against prolonged API outages
- Jitter prevents thundering herd problems in distributed environments
- Configurable backoff allows tuning for different API endpoint characteristics

**Implementation Notes**:
- Initial backoff: 1 second, exponential factor: 2, max backoff: 300 seconds
- Add random jitter: 0-50% of calculated backoff time
- Circuit breaker: fail-fast after 5 consecutive failures, 60-second recovery window
- Different retry strategies per endpoint based on observed reliability patterns

## Risk Assessments

### Data Quality Risks
- **Schema Evolution**: CDD API schema changes could break validation pipeline
  - *Mitigation*: Version schema definitions, implement backward compatibility testing
- **Timezone Handling**: Incorrect timezone assumptions could cause data leakage
  - *Mitigation*: Comprehensive timezone testing including DST transitions and leap seconds

### Performance Risks
- **Storage Scaling**: Large historical datasets may exceed single-machine storage capacity
  - *Mitigation*: Implement data retention policies and archival strategy for old data
- **API Response Time**: Large historical fetches may timeout or be rate-limited
  - *Mitigation*: Implement pagination and chunking for large date ranges

### Operational Risks
- **API Availability**: Extended CDD API outages could create data gaps
  - *Mitigation*: Implement fallback data sources and gap-filling procedures
- **State Corruption**: Corrupted state tracking could cause data duplication
  - *Mitigation*: Atomic state updates and integrity validation on startup

## Next Phase Requirements

The following artifacts are required for Phase 1 (Design & Contracts):

1. **Data Model Schemas**: Pydantic models for all 5 API endpoint responses
2. **API Contract Definitions**: OpenAPI/JSON Schema specifications for each endpoint
3. **Storage Schema**: Parquet table schemas with partitioning strategy
4. **Contract Tests**: Failing tests for each API endpoint and data model
5. **Quickstart Guide**: End-to-end usage examples for development setup

This research provides the technical foundation for implementing a robust, scalable, and maintainable data ingestion pipeline that meets all specification requirements while following established best practices for financial data systems.