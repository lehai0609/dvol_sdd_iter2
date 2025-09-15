# Module Specification: 01\_data\_ingest - DVOL Data Ingestion Pipeline

**Module Branch**: `003-data-ingest-module-spec`
**Created**: 2025-09-14
**Status**: Draft
**Module**: 01\_data\_ingest
**Dependencies**: CryptoDataDownload API, UTC timezone handling, Parquet storage

---

## Purpose

The Data Ingestion Module serves as the foundational data acquis...robust validation, UTC normalization, and "as-of" join controls.

### Business Value

* **Eliminates Data Quality Risk**: Provides clean, validated datasets with comprehensive schema enforcement
* **Prevents Model Leakage**: Strict temporal controls ensure no future information contaminates forecasts
* **Enables Reproducible Research**: Checksums and audit trails support consistent model development
* **Reduces Operational Overhead**: Automated retry and monitoring minimize manual intervention

---

## Inputs

### Primary Data Sources (CryptoDataDownload API)

#### 1. DVOL Daily OHLC

* **Endpoint**: `/v1/data/ohlc/deribit/volatility`
* **Assets**: BTC (required), ETH (optional)
* **Schema**: Date, Open, High, Low, Close (30-day implied volatility index points)
* **Frequency**: Daily
* **SLA**: Available by 23:30 UTC for same trading day

**CDD Details**

* **HTTP**: `GET`
* **Params**: `symbol=BTC|ETH`, `enddate=YYYY-MM-DD` (optional), `limit` (≤2500, default 25), `return=JSON|CSV|XLSX` (default JSON)
* **Fields**: `Date`, `Unix` (ms), `Symbol` (BTC or ETH), `Open`, `High`, `Low`, `Close`
* **Parsing Notes**: Convert `Unix` (ms) → UTC; coerce numeric columns to float64.

#### 2. Deribit Options Daily Summaries

* **Endpoint**: `/v1/data/summary/deribit/options/greeks/maturities/`
* **Content**: NetVega, AvgIV, VolumeUSD, Open Interest proxies
* **Assets**: BTC (required), ETH (optional)
* **Frequency**: Daily aggregated summaries
* **Critical Fields**: Net position sensitivity (vega), average implied volatility, trading volumes

**CDD Details**

* **HTTP**: `GET`
* **Params**: `underlying=BTC|ETH`, `enddate=YYYY-MM-DD` (optional), `limit` (≤2500, default 25), `return=JSON|CSV|XLSX` (default JSON)
* **Fields**: `Date`, `Underlying`, `Maturity`, `Net Delta`, `Buy Delta`, `Sell Delta`, `Net Gamma`, `Net Vega`, `Net Theta`, `Avg IV`, `Volume`, `Buy Volume`, `Sell Volume`, `USD Volume`
* **Notes**: Store per-maturity rows; optional derived daily aggregate = sum of flows (e.g., `Net Vega`) and USD-volume-weighted `Avg IV`.

#### 3. Deribit Futures OHLCV

* **Endpoint**: `/v1/data/ohlc/deribit/futures/`
* **Assets**: BTC (required), ETH (optional)
* **Use**: Futures tape for positioning and liquidity signals
* **Frequency**: Daily

**CDD Details**

* **HTTP**: `GET`
* **Params**: `symbol=BTC-PERPETUAL|<full instrument>`, `enddate=YYYY-MM-DD` (optional), `limit` (≤2500, default 25), `return=JSON|CSV|XLSX` (default JSON)
* **Fields**: `Unix` (ms), `Date`, `Symbol`, `Open`, `High`, `Low`, `Close`, `Volume` (base ccy), `Base Volume` (USD)
* **Notes**: Parse `symbol` prefix to infer asset (BTC/ETH); map `Volume`→`volume_base`, `Base Volume`→`volume_usd`.

#### 4. Deribit Funding Rates

* **Endpoint**: `/v1/data/ohlc/deribit/funding`
* **Assets**: BTC-PERPETUAL (required), ETH-PERPETUAL (optional)
* **Raw Frequency**: 1h/8h intervals → aggregated to daily statistics
* **Processing**: Daily mean, standard deviation, and 5-day change calculations
* **Purpose**: Risk appetite and positioning pressure indicators

**CDD Details**

* **HTTP**: `GET`
* **Params**: `symbol=BTC-PERPETUAL|ETH-PERPETUAL`, `enddate=YYYY-MM-DD` (optional), `limit` (≤2500, default 25), `return=JSON|CSV|XLSX` (default JSON)
* **Fields**: `Date`, `Unix` (ms), `Symbol`, `Index Price`, `Prev Index Price`, `Interest 8H`, `Interest 1H`
* **Aggregation**: Compute daily `funding_mean`, `funding_std`, and 5-day change from sub-daily observations.

#### 5. On-Chain Daily Summaries

* **Endpoint**: `/v1/data/summary/blockchain/blocks/`
* **Assets**: BTC, ETH
* **Content**: Transaction count, total fees, hashrate, average block interval
* **Processing**: Daily totals and 5-day participation change metrics

**CDD Details**

* **HTTP**: `GET`
* **Params**: `symbol=btc|eth`, `enddate=YYYY-MM-DD` (optional), `limit` (≤2500, default 25), `return=JSON|CSV|XLSX` (default JSON)
* **Fields** (subset): `Date`, `Symbol`, `Total Transactions`, `Total Block Count`, `Average Difficulty`, `Avg Seconds Between Blocks`, `Avg Block Size (MB)`, `Hashrate`, `Avg Transactions Count Per Block`, ETH-only: `Avg Gas Limit`, `Total Gas Used in ETH`, `Block Utilization`, `Complexity Score`, plus `First Block`, `Last Block`.
* **Notes**: Keep ETH-only fields as nullable for BTC rows.

### Authentication & Access

* **Method**: Public endpoints require no auth; if account-level API keys are provided, pass per vendor guidance (header or query parameter)
* **Format**: All endpoints support `?return=JSON|CSV|XLSX` (default `JSON`)
* **Rate Limits**: \[NEEDS CLARIFICATION: specific rate limits per endpoint]
* **Retry Policy**: Exponential backoff with jitter for transient failures

---

## Outputs

### Data Contracts (Materialized Tables)

#### 1. raw\_dvol

```
Columns: asset, date_utc, unix_ms, symbol, open, high, low, close, data_source, ingestion_timestamp, checksum
Schema: asset (string), date_utc (date), OHLC (float64), metadata (string/timestamp)
Partitioning: By asset and year-month
Retention: Full history maintained
```

#### 2. raw\_options\_summary

```
Columns: asset (underlying), date_utc, maturity_utc, net_delta, buy_delta, sell_delta, net_gamma, net_vega, net_theta, avg_iv, volume, buy_volume, sell_volume, usd_volume, data_source, ingestion_timestamp, checksum
-- Note: Optionally maintain a derived daily rollup keyed (asset, date_utc) with usd_volume_sum and avg_iv_usd_weighted.
Schema: asset (string), date_utc (date), maturity_utc (date), metrics (float64), metadata (string/timestamp)
Partitioning: By asset and year-month
Retention: Full history maintained
```

#### 3. raw\_ohlcv

```
Columns: asset, symbol, date_utc, unix_ms, open, high, low, close, volume_base, volume_usd, data_source, ingestion_timestamp, checksum
-- Notes: `volume_base` maps from CDD `Volume` (base ccy); `volume_usd` maps from CDD `Base Volume`.
Schema: asset (string), symbol (string), date_utc (date), OHLCV (float64)
Partitioning: By asset and year-month
Retention: Full history maintained
```

#### 4. raw\_funding

```
Columns: asset, symbol, date_utc, unix_ms, index_price, prev_index_price, interest_8h, interest_1h, funding_mean, funding_std, funding_5d_change, data_source, ingestion_timestamp, checksum
-- Notes: The last three columns are daily aggregates derived from sub-daily observations.
Schema: asset (string), symbol (string), date_utc (date), funding_metrics (float64), metadata (string/timestamp)
Partitioning: By asset and year-month
Retention: Full history maintained
```

#### 5. raw\_onchain

```
Columns: asset, date_utc, total_transactions, total_block_cnt, avg_secs_between_blocks, avg_block_size_mb, hashrate, avg_transactions_count_per_block, avg_gas_limit (nullable), total_gas_used_in_eth (nullable), block_utilization (nullable), complexity_score (nullable), first_block, last_block, data_source, ingestion_timestamp, checksum
Schema: asset (string), date_utc (date), blockchain_metrics (float64), metadata (string/timestamp)
Partitioning: By asset and year-month
Retention: Full history maintained
```

### Operational Outputs

#### Success Flags & Status

* **Daily Success Flag**: Boolean indicator for complete ingestion cycle
* **Per-Source Status**: Individual success/failure status for each data endpoint
* **Gap Detection**: Explicit flags for missing dates with reason codes
* **Processing Duration**: Timing metrics for performance monitoring

#### Data Freshness Metrics

* **Last Updated Timestamps**: Per-table metadata showing most recent data availability
* **Latency Measurements**: Time from source publication to local availability
* **SLA Compliance**: Percentage of daily cycles completing before cut-off deadline
* **Staleness Alerts**: Automated notifications for data older than threshold

#### Data Integrity Checksums

* **Row-Level Checksums**: Hash verification for individual records
* **Table-Level Checksums**: Aggregate hash for complete daily datasets
* **Cross-Source Consistency**: Validation that related data sources align temporally
* **Historical Comparison**: Checksums enable detection of retroactive data changes

---

## Acceptance Criteria

### Data Completeness & Coverage

* **AC-001**: System MUST achieve 100% date coverage for all data sources or provide explicit gap flags with reason codes
* **AC-002**: System MUST maintain continuous daily ingestion without gaps exceeding 1 business day
* **AC-003**: All data MUST be available before the 00:00 UTC modeling cut-off on the following day
* **AC-004**: Missing data periods MUST be flagged with categorized reason codes (API downtime, market holidays, etc.)

### Temporal Consistency & Leakage Prevention

* **AC-005**: All timestamps MUST be normalized to UTC before any processing or storage
* **AC-006**: No data records SHALL contain timestamps after the ingestion cut-off for that trading day
* **AC-007**: "As-of" joins MUST align on UTC date boundaries to prevent cross-day contamination
* **AC-008**: System MUST provide audit trail showing exact data availability times for leak detection

### Reproducibility & Idempotence

* **AC-009**: Re-running ingestion for historical dates MUST produce identical results (same checksums)
* **AC-010**: System MUST support incremental updates without data duplication
* **AC-011**: All processing steps MUST be deterministic and reproducible across environments
* **AC-012**: Complete historical rebuild MUST be possible from source data and configuration

### Quality & Validation

* **AC-013a (Schema parity)**: For each CDD endpoint, all documented fields are present and typed; `Volume`→`volume_base`, `Base Volume`→`volume_usd` mappings are verified.
* **AC-021 (Idempotent keys)**: Re-ingesting the same (asset, date\_utc\[, maturity\_utc|symbol]) produces identical checksums.
* **AC-022 (Aggregation parity)**: Daily funding and options rollups recompute deterministically from raw tables (tolerance 1e-9).
* **AC-023 (On-chain scope)**: ETH-only fields are nullable for BTC and preserved for ETH.

### Integration Testing

* **End-to-End Pipeline Tests**: Full ingestion cycle with synthetic data sources
* **API Client Tests**: Integration with CryptoDataDownload endpoints using test credentials
* **Storage System Tests**: Parquet writing and partitioning with various data sizes
* **Cross-Source Consistency Tests**: Validate temporal alignment between related data streams

### Performance Testing

* **Volume Load Tests**: Process historical data volumes to validate scaling behavior
* **Latency Tests**: Measure ingestion timing under normal and stressed conditions
* **Memory Usage Tests**: Monitor resource consumption during large dataset processing
* **Concurrent Access Tests**: Validate behavior when multiple processes access storage

### Operational Testing

* **Failure Recovery Tests**: Simulate various failure scenarios and validate recovery procedures
* **Gap Detection Tests**: Verify missing data identification and flagging mechanisms
* **Alerting System Tests**: Confirm timely notifications for various failure and warning conditions
* **Historical Rebuild Tests**: Validate complete data reconstruction from archived sources

### Business Logic Testing

* **Data Quality Rules**: Test outlier detection, range validation, and consistency checks
* **Cut-off Compliance**: Verify strict adherence to 00:00 UTC processing deadlines
* **Asset Coverage**: Confirm proper handling of BTC (required) and ETH (optional) data flows
* **Audit Trail Validation**: Test completeness and accuracy of processing logs and metadata

---

## Open Items

### Technical Clarifications Required

* Published per-endpoint rate limits (CDD): **TBD**
* Final choice of options daily aggregate weighting (e.g., USD-volume-weighted `avg_iv`): **TBD**
* Confirm whether DVOL endpoint requires explicit `symbol`; examples imply BTC/ETH supported.

---

## Dependencies & Assumptions

### External Dependencies

* **CryptoDataDownload API**: Reliable availability and consistent data quality from primary vendor
* **Network Connectivity**: Stable internet connection for API access during ingestion windows
* **Storage Infrastructure**: Adequate disk space and I/O performance for Parquet storage
* **Compute Resources**: Sufficient CPU/memory for daily processing volumes

### Internal Dependencies

* **Authentication System**: Secure storage and rotation of API credentials
* **Monitoring Platform**: Existing infrastructure for alerts, dashboards, and log aggregation
* **Job Scheduler**: Daily orchestration system for triggering ingestion processes
* **Development Environment**: Consistent Python environment with required libraries

### Key Assumptions

* **Market Data Availability**: CryptoDataDownload will maintain historical data integrity
* **API Stability**: Data source APIs will maintain backward compatibility
* **Processing Window**: Sufficient time between market close and modeling cut-off for complete ingestion
* **Data Volume Growth**: Current processing capacity adequate for projected data growth

---

## Appendix: CDD Endpoint Call Examples

```
DVOL (BTC):
/v1/data/ohlc/deribit/volatility?symbol=BTC&enddate=2024-12-31&limit=2500&return=JSON

Options Greeks by Maturity (BTC):
/v1/data/summary/deribit/options/greeks/maturities/?underlying=BTC&enddate=2024-12-31&limit=2500&return=JSON

Deribit Futures (Perp):
/v1/data/ohlc/deribit/futures/?symbol=BTC-PERPETUAL&enddate=2024-12-31&limit=2500&return=JSON

Funding (Perp):
/v1/data/ohlc/deribit/funding?symbol=BTC-PERPETUAL&enddate=2024-12-31&limit=2500&return=JSON

On-chain (BTC):
/v1/data/summary/blockchain/blocks/?symbol=btc&enddate=2024-12-31&limit=2500&return=JSON
```
