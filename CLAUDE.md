# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a research-to-production system for forecasting changes in Deribit's 30-day DVOL index (implied volatility) for BTC and ETH over multiple horizons (1d/7d/14d) and monetizing forecasts via DVOL futures or delta-hedged options strategies.

## Recent Changes

**Data Ingestion Module Implementation Planning (Current Focus)**:
- Completed detailed specification for 01_data_ingest module with 5 CryptoDataDownload API endpoints
- Defined contract-first development approach with OpenAPI specifications and Pydantic validation
- Established UTC timezone handling patterns and 00:00 UTC cut-off enforcement
- Specified Parquet storage strategy with asset/year-month partitioning
- Designed `dvol-ingest` CLI tool for operational management (fetch, validate, backfill, status commands)
- Added comprehensive troubleshooting guidance for common API and data quality issues
- Ready to begin implementation of core data pipeline infrastructure

## High-Level Architecture

The system is designed around five core modules with clear interfaces:

### 1. Data Pipeline Module
- **Purpose**: Daily ETL from CryptoDataDownload API
- **Key Endpoints**: DVOL OHLC, options summaries, funding rates, on-chain metrics
- **Critical Constraint**: 00:00 UTC daily cut-off with strict leakage control
- **Storage**: Parquet files partitioned by date, PostgreSQL for metadata

### 2. Feature Engineering Module
- **Feature Categories**:
  - Price/volatility: RV_1/5/22, HAR terms, jump proxies, overnight gaps
  - IV/surface: DVOL levels/changes, net vega, term structure slopes
  - Funding/basis: Perpetual funding statistics and regime changes
  - On-chain: Transaction counts, fees, participation proxies
- **Scaling**: RobustScaler fit on training data only
- **Leakage Controls**: All features lagged and available before prediction target

### 3. Modeling Module
- **Baselines**: HAR-RV, Lasso, LightGBM (must-beat benchmarks)
- **Primary Model**: LSTM with 90-day lookback, dual heads (regression + classification)
- **Architecture**: LSTM(64) → Dropout(0.1) → Dense(32) → Dense(1) for ΔDVOL
- **Training**: Walk-forward validation, Huber loss, early stopping

### 4. Signal Generation Module
- **Outputs**: Forecast value, direction {LONG, SHORT, FLAT}, confidence score
- **Thresholds**: Horizon-specific (τ₁d, τ₁w, τ₂w) calibrated on validation data
- **Regime Filters**: Reduce position size during high jump/funding regimes

### 5. Trade Execution Module
- **Primary Strategy**: DVOL futures (1 contract per signal)
- **Secondary**: Delta-hedged ATM straddles (long vol) or iron condors (short vol)
- **Risk Controls**: Max vega limits, daily stop-loss, event guardrails

## Data Sources & API Integration

**Primary Provider**: CryptoDataDownload (CDD) API
- Authentication via token in headers or query params
- All endpoints support `?format=json&auth_token=YOURTOKEN`

**Key Endpoints**:
```
# DVOL Index (primary target)
GET /v1/data/ohlc/deribit/volatility/?symbol=BTC&interval=1d

# Options Flow Features
GET /v1/data/summary/deribit/options/greeks/?underlying=BTC&interval=1d

# Funding Rates
GET /v1/data/ohlc/deribit/futures/funding/?symbol=BTC-PERPETUAL&interval=1h

# On-Chain Activity
GET /v1/data/summary/blockchain/bchain/?symbol=btc&interval=1d
```

## Data Ingestion Module (01_data_ingest)

This section provides specific guidance for working with the data ingestion module implementation.

### Module Architecture

**Core Components**:
- **API Client Layer**: Handles CryptoDataDownload API interactions with retry logic and circuit breakers
- **Data Pipeline**: Orchestrates fetching, validation, and storage workflows
- **Schema Validation**: Pydantic models for contract enforcement and data quality checks
- **Storage Engine**: Parquet writer with asset/year-month partitioning strategy
- **CLI Interface**: `dvol-ingest` command-line tool for operational tasks

### Key Endpoints Integration

The module handles 5 primary CryptoDataDownload API endpoints:

```python
# DVOL Index Data (target variable)
/v1/data/ohlc/deribit/volatility/?symbol={BTC|ETH}&interval=1d

# Options Greeks & Summary Statistics
/v1/data/summary/deribit/options/greeks/?underlying={BTC|ETH}&interval=1d

# Futures OHLC Data
/v1/data/ohlc/deribit/futures/?symbol={BTC|ETH}-PERPETUAL&interval=1d

# Funding Rate Data (hourly)
/v1/data/ohlc/deribit/futures/funding/?symbol={BTC|ETH}-PERPETUAL&interval=1h

# On-Chain Metrics
/v1/data/summary/blockchain/bchain/?symbol={btc|eth}&interval=1d
```

### Development Patterns

**Contract-First Development**:
1. Define OpenAPI specifications for each endpoint
2. Generate Pydantic models from specifications
3. Implement contract tests to validate API responses
4. Build integration tests with live API calls
5. Add unit tests for business logic

**UTC Timezone Discipline**:
```python
# Always use UTC for timestamps
import pytz
UTC = pytz.UTC

# Convert API timestamps to UTC immediately
df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_convert(UTC)

# Enforce 00:00 UTC daily cut-off for leakage control
cutoff_time = pd.Timestamp('00:00:00', tz=UTC)
```

**Parquet Storage Strategy**:
```python
# Partitioning scheme: /data/{asset}/{endpoint}/year={YYYY}/month={MM}/
partition_path = f"data/{asset}/{endpoint}/year={year}/month={month:02d}/"

# Schema enforcement with pyarrow
schema = pa.schema([
    pa.field("timestamp", pa.timestamp("ns", tz="UTC")),
    pa.field("symbol", pa.string()),
    pa.field("value", pa.float64())
])
```

### CLI Commands

**Primary Operations**:
```bash
# Fetch latest data for all endpoints
dvol-ingest fetch --asset BTC --date 2024-01-15

# Validate stored data against contracts
dvol-ingest validate --asset BTC --start-date 2024-01-01 --end-date 2024-01-31

# Backfill historical data with rate limiting
dvol-ingest backfill --asset BTC --start-date 2023-01-01 --end-date 2023-12-31

# Check pipeline status and data coverage
dvol-ingest status --asset BTC --endpoint dvol
```

### Troubleshooting Guide

**API Connectivity Issues**:
- Check authentication token validity and rate limits
- Verify network connectivity and DNS resolution
- Review circuit breaker status and retry backoff settings
- Validate request parameters match API documentation

**Schema Validation Failures**:
- Compare API response structure against OpenAPI specification
- Check for unexpected null values or data type changes
- Verify timestamp format and timezone handling
- Review field name mappings and case sensitivity

**UTC Timezone Problems**:
- Ensure all timestamps converted to UTC immediately after API fetch
- Validate timezone-aware datetime objects throughout pipeline
- Check for daylight saving time transitions in raw data
- Verify 00:00 UTC cut-off alignment for leakage control

**Parquet Storage Issues**:
- Check disk space and write permissions for data directory
- Verify partition path construction matches expected scheme
- Review schema compatibility for incremental writes
- Validate file naming conventions and metadata consistency

**Data Quality Verification**:
- Run checksum validation on stored Parquet files
- Check for data gaps or duplicate timestamps
- Verify temporal alignment across different endpoints
- Compare row counts against expected daily/hourly frequencies

### Key Dependencies

**Required Libraries**:
- `pandas>=1.5.0` for data manipulation
- `pyarrow>=10.0.0` for Parquet I/O operations
- `pydantic>=1.10.0` for schema validation
- `httpx` for async API client implementation
- `tenacity` for retry logic and circuit breakers
- `typer` for CLI interface construction

**Configuration Management**:
- Environment variables for API authentication
- Config files for endpoint specifications and retry policies
- Logging configuration with structured output for monitoring
- Error tracking integration for production deployments

### Testing Strategy

**Test Hierarchy**:
1. **Contract Tests**: Validate API response schemas against OpenAPI specs
2. **Integration Tests**: End-to-end pipeline testing with live API calls
3. **Unit Tests**: Business logic and data transformation functions
4. **Property Tests**: Data invariant checking with hypothesis library

**Mock Strategy**:
- Use recorded API responses for deterministic testing
- Mock external dependencies but preserve data contracts
- Test error conditions and edge cases systematically
- Validate retry logic and circuit breaker behavior

## Target Variables & Labels

- **Primary Target**: ΔDVOL = Close(DVOL)_t - Close(DVOL)_{t-1}
- **Horizons**: 1d, 7d, 14d changes in DVOL index points
- **Optional Classification**: Up/Flat/Down with dead-zone around zero

## Model Training Pipeline

**Walk-Forward Validation**:
```python
# Expanding window approach
for anchor in rolling_days:
    X_train = features[:anchor-30]
    X_val = features[anchor-30:anchor]

    # Fit scaler on training data only
    scaler.fit(X_train)

    # Convert to 90-day sequences for LSTM
    X_seq = make_sequences(X_scaled, window=90)

    # Train with early stopping on validation
    model.fit(X_seq, y_train, validation_data=(X_val_seq, y_val))
```

## Success Criteria & Metrics

**Research Metrics**:
- Out-of-sample Sharpe ≥ 1.0 (net of costs)
- Maximum drawdown ≤ 20%
- Directional hit rate > 53%
- Positive tail behavior on volatility shock days

**Forecast Quality**:
- RMSE, MAE, Spearman rank correlation
- Walk-forward validation across market regimes

**Trading Performance**:
- Net Sharpe, Sortino, max drawdown, turnover
- P&L attribution by feature regime and instrument choice

## Risk Management

**Position Limits**:
- Max 2 DVOL contracts or equivalent vega exposure
- Hard caps by asset and aggregate portfolio level

**Event Guardrails**:
- Reduce size when jump proxy fires or funding volatility spikes
- Daily stop-loss based on backtest VaR

**Operational Controls**:
- Data freshness monitoring (>95% uptime requirement)
- Feature drift detection with automated alerts
- Kill-switch for model failures or market anomalies

## Development Workflow

**Language**: Python (inferred from .gitignore)
**Data Storage**: Parquet (partitioned by date) + PostgreSQL metadata
**ML Framework**: Expected to use scikit-learn, LightGBM, TensorFlow/PyTorch for LSTM

**Project Phases**:
1. **Weeks 1-2**: Data pipeline and feature engineering
2. **Weeks 3-4**: Baseline models and walk-forward backtesting
3. **Weeks 5-6**: LSTM implementation and hyperparameter optimization
4. **Week 7**: Trading simulation with delta-hedging engine
5. **Week 8**: Paper trading and production readiness

## File Organization

```
.
├── specs/001-dvol-forecasting-system/     # Feature specification
├── .claude/                               # Claude configuration
├── .specify/                              # Specification tooling
├── 0. Initial Idea.md                     # Research context
├── 1. Problem Statement.md                # Problem definition
├── 2. Research Design Plan.md             # Methodology details
├── 01_data_ingest/                        # Data ingestion module
│   ├── src/                               # Source code
│   ├── tests/                             # Test suites
│   ├── contracts/                         # OpenAPI specifications
│   └── cli/                               # CLI implementation
└── [Additional modules to be created]
```

## Key Implementation Notes

- **Strict Timestamp Discipline**: All features must be available before 00:00 UTC cut-off
- **No Leakage**: Use "as-of" joins, fit scalers/encoders only on training windows
- **Cost Modeling**: Include maker/taker fees, slippage via half-spread assumptions
- **Regime Awareness**: Models should handle volatility clustering and structural breaks
- **Reproducibility**: Pin random seeds, version data with checksums, track all experiments

## Common Pitfalls to Avoid

- Forward-looking bias in feature construction
- Training on future information via data leakage
- Under-estimating transaction costs and slippage
- Ignoring funding costs for delta hedging
- Overfitting to short sample periods
- Missing timezone handling across data sources