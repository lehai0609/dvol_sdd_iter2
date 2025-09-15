# Quickstart Guide: DVOL Data Ingestion Pipeline

**Feature**: 01_data_ingest - DVOL Data Ingestion Pipeline
**Date**: 2025-09-14
**Audience**: Developers, Data Engineers, Operations Team

## Overview

This guide provides step-by-step instructions for setting up, running, and validating the DVOL data ingestion pipeline. Follow these instructions to get from zero to a working data pipeline that fetches cryptocurrency data from CryptoDataDownload API and stores it in partitioned Parquet format.

## Prerequisites

### System Requirements
- Python 3.11 or later
- 16GB+ RAM (for processing large historical datasets)
- 100GB+ disk space (for Parquet storage with historical data)
- Stable internet connection (for API access)

### API Access
- CryptoDataDownload account (if authentication required)
- API credentials stored securely
- Network access to `api.cryptodatadownload.com`

## Installation

### 1. Clone Repository and Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd dvol_sdd_iter2

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# CryptoDataDownload API Configuration
CDD_API_BASE_URL=https://api.cryptodatadownload.com
CDD_API_KEY=your_api_key_here  # If required
CDD_RATE_LIMIT_PER_MINUTE=60

# Storage Configuration
DATA_ROOT_PATH=./data
PARQUET_COMPRESSION=snappy
PARQUET_ROW_GROUP_SIZE=100000

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Processing Configuration
UTC_CUTOFF_HOUR=0  # 00:00 UTC daily cutoff
BACKFILL_DAYS=30   # Default historical backfill period
MAX_RETRY_ATTEMPTS=5
RETRY_BACKOFF_FACTOR=2
```

### 3. Initialize Storage Directories

```bash
# Create directory structure
dvol-ingest init-storage --data-root ./data

# Expected structure:
# data/
# ├── raw_dvol/
# ├── raw_options_summary/
# ├── raw_ohlcv/
# ├── raw_funding/
# ├── raw_onchain/
# ├── state/
# └── logs/
```

## Basic Usage

### 1. Test API Connectivity

```bash
# Test connection to CDD API
dvol-ingest test-connection --endpoints all

# Expected output:
# ✓ DVOL endpoint: OK (response_time: 245ms)
# ✓ Options endpoint: OK (response_time: 312ms)
# ✓ Futures endpoint: OK (response_time: 198ms)
# ✓ Funding endpoint: OK (response_time: 267ms)
# ✓ OnChain endpoint: OK (response_time: 389ms)
```

### 2. Fetch Sample Data

```bash
# Fetch recent DVOL data for BTC
dvol-ingest fetch --source dvol --asset BTC --days 7

# Expected output:
# 2025-09-14 10:30:15 [INFO] Fetching DVOL data for BTC (last 7 days)
# 2025-09-14 10:30:16 [INFO] Retrieved 7 records from API
# 2025-09-14 10:30:16 [INFO] Validated all records successfully
# 2025-09-14 10:30:16 [INFO] Stored 7 records to data/raw_dvol/asset=BTC/year=2025/month=09/
# 2025-09-14 10:30:16 [INFO] Checksums: VALID (sha256: a1b2c3...)
```

### 3. Validate Data Quality

```bash
# Run data quality checks
dvol-ingest validate --source dvol --asset BTC --date 2025-09-13

# Expected output:
# ✓ Schema validation: PASSED
# ✓ Timestamp normalization: PASSED (UTC enforced)
# ✓ Value ranges: PASSED (OHLC values within expected bounds)
# ✓ Checksum verification: PASSED
# ✓ Cross-source alignment: PASSED (trading day boundaries consistent)
```

### 4. Run Complete Daily Ingestion

```bash
# Execute full daily pipeline
dvol-ingest run-daily --date 2025-09-13

# Expected output:
# 2025-09-14 10:35:00 [INFO] Starting daily ingestion for 2025-09-13
# 2025-09-14 10:35:01 [INFO] Fetching DVOL data for BTC, ETH...
# 2025-09-14 10:35:15 [INFO] Fetching Options summary for BTC, ETH...
# 2025-09-14 10:35:32 [INFO] Fetching Futures OHLCV for BTC, ETH...
# 2025-09-14 10:35:45 [INFO] Fetching Funding rates for BTC, ETH...
# 2025-09-14 10:35:58 [INFO] Fetching OnChain data for BTC, ETH...
# 2025-09-14 10:36:15 [INFO] All sources completed successfully
# 2025-09-14 10:36:15 [INFO] Cross-source validation: PASSED
# 2025-09-14 10:36:16 [INFO] Daily ingestion completed: 47 records stored
```

## Advanced Usage

### Historical Backfill

```bash
# Backfill 3 months of historical data
dvol-ingest backfill --start-date 2024-06-01 --end-date 2024-08-31 --sources all --assets BTC,ETH

# Monitor progress
dvol-ingest status --backfill-id <id>
```

### Incremental Updates

```bash
# Run incremental update (fetches only new data since last run)
dvol-ingest incremental --sources all --assets all

# Schedule with cron (runs at 01:00 UTC daily)
echo "0 1 * * * cd /path/to/project && .venv/bin/dvol-ingest incremental --sources all" | crontab -
```

### Monitoring and Status

```bash
# Check pipeline status
dvol-ingest status --detailed

# Expected output:
# Pipeline Status: HEALTHY
# Last successful run: 2025-09-14 01:00:15 UTC
# Data freshness:
#   - DVOL: 2025-09-13 (1 day old) ✓
#   - Options: 2025-09-13 (1 day old) ✓
#   - Futures: 2025-09-13 (1 day old) ✓
#   - Funding: 2025-09-13 (1 day old) ✓
#   - OnChain: 2025-09-13 (1 day old) ✓
# Storage usage: 2.3GB (12% of allocated)

# Check for data gaps
dvol-ingest gaps --start-date 2024-01-01 --end-date 2024-12-31
```

## Data Access Examples

### Reading Parquet Data

```python
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Read DVOL data for BTC in specific month
dvol_btc = pd.read_parquet('data/raw_dvol/asset=BTC/year=2025/month=09/')
print(f"Loaded {len(dvol_btc)} DVOL records for BTC")

# Read with date filter
table = pq.read_table('data/raw_dvol',
                      filters=[('asset', '=', 'BTC'),
                              ('date_utc', '>=', '2025-09-01')])
df = table.to_pandas()

# Verify data quality
assert df['checksum'].notna().all(), "All records must have checksums"
assert df['date_utc'].dt.tz.name == 'UTC', "All dates must be UTC"
```

### Data Quality Validation

```python
from dvol_data_ingest.validators import validate_record_integrity

# Validate checksum integrity
for _, record in df.iterrows():
    is_valid = validate_record_integrity(record)
    assert is_valid, f"Record {record['date_utc']} failed integrity check"

# Cross-source temporal alignment check
dvol_dates = set(pd.read_parquet('data/raw_dvol/asset=BTC/year=2025/month=09/')['date_utc'])
funding_dates = set(pd.read_parquet('data/raw_funding/asset=BTC/year=2025/month=09/')['date_utc'])
assert dvol_dates == funding_dates, "DVOL and funding data must have same date coverage"
```

## Troubleshooting

### Common Issues

#### 1. API Connection Failures
```bash
# Symptoms: Connection timeouts, 403/401 errors
# Solutions:
dvol-ingest test-connection --debug
# Check API credentials in .env file
# Verify network connectivity to api.cryptodatadownload.com
# Review rate limiting configuration
```

#### 2. Schema Validation Errors
```bash
# Symptoms: Validation errors, type conversion failures
# Solutions:
dvol-ingest validate --source dvol --debug --sample-size 5
# Check API response format changes
# Review Pydantic model definitions
# Update schema contracts if needed
```

#### 3. Storage/Performance Issues
```bash
# Symptoms: Slow writes, disk space errors
# Solutions:
dvol-ingest storage-info --path ./data
# Check available disk space
# Optimize Parquet row group size
# Implement data retention policies
```

#### 4. Data Gaps or Missing Records
```bash
# Symptoms: Missing dates, incomplete datasets
# Solutions:
dvol-ingest gaps --detailed --sources all
# Review API downtime logs
# Check for rate limiting issues
# Run targeted backfill for missing periods
```

### Log Analysis

```bash
# View recent pipeline logs
tail -f data/logs/pipeline.log | jq '.'

# Search for errors in last 24 hours
grep -A 5 -B 5 "ERROR" data/logs/pipeline.log | grep $(date -d "yesterday" +%Y-%m-%d)

# Monitor API response times
grep "response_time" data/logs/pipeline.log | awk '{print $NF}' | sort -n
```

## Production Deployment

### 1. Environment Setup
```bash
# Production environment variables
export ENVIRONMENT=production
export LOG_LEVEL=WARNING
export DATA_ROOT_PATH=/opt/dvol_data
export CDD_API_KEY=production_api_key
```

### 2. Systemd Service (Linux)
```ini
# /etc/systemd/system/dvol-ingest.service
[Unit]
Description=DVOL Data Ingestion Pipeline
After=network.target

[Service]
Type=oneshot
User=dvol
WorkingDirectory=/opt/dvol_data_ingest
ExecStart=/opt/dvol_data_ingest/.venv/bin/dvol-ingest incremental --sources all
EnvironmentFile=/opt/dvol_data_ingest/.env

[Install]
WantedBy=multi-user.target
```

### 3. Systemd Timer
```ini
# /etc/systemd/system/dvol-ingest.timer
[Unit]
Description=Run DVOL ingestion daily at 01:00 UTC

[Timer]
OnCalendar=*-*-* 01:00:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```

### 4. Monitoring Integration
```bash
# Prometheus metrics endpoint
curl http://localhost:8080/metrics

# Key metrics:
# - dvol_ingest_records_processed_total
# - dvol_ingest_api_response_time_seconds
# - dvol_ingest_last_successful_run_timestamp
# - dvol_ingest_data_gaps_detected_total
```

## Success Verification

After following this quickstart, you should have:

1. ✅ **Working API connectivity** - All 5 CDD endpoints responding successfully
2. ✅ **Data ingestion** - Historical data fetched and stored in Parquet format
3. ✅ **Schema validation** - All records pass Pydantic validation rules
4. ✅ **UTC normalization** - All timestamps converted to UTC with validation
5. ✅ **Checksum verification** - Data integrity confirmed with SHA-256 hashes
6. ✅ **Incremental processing** - Pipeline runs efficiently with state tracking
7. ✅ **Monitoring setup** - Status reporting and gap detection working
8. ✅ **Production readiness** - Systemd service configured for daily execution

### Acceptance Test Commands
```bash
# Run acceptance test suite
dvol-ingest test-acceptance --comprehensive

# Expected output: All tests passing
# ✓ AC-001: 100% date coverage achieved
# ✓ AC-005: UTC timestamp normalization verified
# ✓ AC-009: Historical rebuild produces identical checksums
# ✓ AC-013a: Schema parity confirmed across all endpoints
# ✓ AC-021: Idempotent operations verified
```

## Next Steps

1. **Review [data-model.md](./data-model.md)** for detailed schema information
2. **Examine [contracts/](./contracts/)** for API specifications
3. **Configure monitoring** dashboards using provided metrics
4. **Set up alerting** for data freshness and pipeline failures
5. **Plan data retention** policies for long-term storage management
6. **Integration testing** with downstream feature engineering modules

For production deployment questions or troubleshooting assistance, refer to the operational runbook or contact the data engineering team.