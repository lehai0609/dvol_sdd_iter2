# Feature Specification: DVOL Forecasting & Volatility Trading System

**Feature Branch**: `001-dvol-forecasting-system`
**Created**: 2025-09-14
**Status**: Draft
**Input**: Research-to-production system that forecasts changes in Deribit's 30-day DVOL index for BTC (and optionally ETH) over 1d/7d/14d horizons and monetizes via DVOL futures or delta-hedged options

---

## Problem & Objective

Predict next-day/next week or next 2 weeks change in 30-day implied volatility (IV) for BTC (and optionally ETH) and monetize the forecast via long/short volatility trades. Primary target: daily ”DVOL (Deribit 30-day IV index). Translate forecasts into positions in DVOL futures or delta-hedged options structures (long straddles for IV‘, short strangles/iron condors for IV“).

**Primary Research Question**: Can we build a predictive model, using only information available before the daily cut-off, that delivers out-of-sample forecasts of DVOL changes strong enough to sustain a positive, cost-adjusted Sharpe ratio when mapped to real trades?

## Scope

### Assets
- **Primary**: BTC (Bitcoin)
- **Secondary**: ETH (Ethereum) - optional extension

### Instruments
- **Primary**: Deribit DVOL futures (cash-settled in USDC)
- **Secondary**: BTC/ETH listed options for delta-hedged long-volatility or short-volatility structures

### Horizons
- 1 calendar day (t+1d)
- 1 week (t+7d)
- 2 weeks (t+14d)

### Trading Cadence
Daily end-of-day (EOD) signal generation with strict timestamp discipline and fixed daily cut-off at 00:00 UTC.

## Success Criteria

### Research Metrics
- **Out-of-sample Sharpe ratio** e 1.0 (net of realistic trading costs)
- **Maximum drawdown** d 20%
- **Positive skew** in daily P&L distribution
- **Statistically significant directional accuracy** > 53% over independent test period
- **Positive tail behavior** on large volatility shock days

### Operational Metrics
- **Data freshness**: All features available before daily cut-off > 95% uptime
- **Model stability**: Feature drift detection with automated alerts
- **Real-time monitoring**: P&L attribution and risk limit compliance

## Data Sources & Cut-off

### Primary Data Provider
CryptoDataDownload (CDD) API as single data backbone with the following endpoints:

### Core Data Streams
1. **DVOL Index**: Daily OHLC from `v1/data/ohlc/deribit/volatility/`
2. **Options Flow**: Daily summaries from `v1/data/summary/deribit/options/greeks/`
3. **Market Tape**: Spot/futures OHLCV and funding rates from Binance/Deribit endpoints
4. **On-Chain Activity**: Daily blockchain summaries from `v1/data/summary/blockchain/bchain/`

### Cut-off Rules
- **Fixed daily cut-off**: 00:00 UTC
- **Strict leakage control**: All features must be finalized and "frozen" before the DVOL close used as target
- **Timezone normalization**: All timestamps converted to UTC during processing
- **As-of joins**: No forward-fills across cut-off boundaries

## High-Level Architecture & Module Contracts

### Data Pipeline Module
```
Interface: DataPipeline
Methods:
  - ingest_daily_data(date: str) -> Dict[str, DataFrame]
  - validate_data_quality(raw_data: Dict) -> ValidationReport
  - build_feature_table(date: str) -> DataFrame
  - check_data_freshness() -> FreshnessReport

Outputs:
  - daily_features table (asset-date keyed)
  - data_quality_metrics
  - Pipeline success/failure flags
```

### Feature Engineering Module
```
Interface: FeatureEngine
Methods:
  - compute_realized_volatility(prices: Series, windows: List[int]) -> DataFrame
  - compute_har_terms(rv_data: DataFrame) -> DataFrame
  - compute_options_flow_features(options_data: DataFrame) -> DataFrame
  - compute_funding_features(funding_data: DataFrame) -> DataFrame
  - apply_scaling(features: DataFrame, fit_on_train: bool) -> DataFrame

Feature Categories:
  - Price/volatility: RV_1/5/22, HAR terms, overnight gaps, jump proxies
  - IV/surface & flow: DVOL levels/changes, net vega, avg IV vs DVOL
  - Funding/basis: Perpetual funding mean/std, 5-day changes
  - On-chain: Transaction counts, fees, 5-day participation changes
```

### Modeling Module
```
Interface: ModelEngine
Methods:
  - train_baseline_models(X_train: DataFrame, y_train: Series) -> Dict[str, Model]
  - train_lstm_model(X_seq: ndarray, y: ndarray, config: ModelConfig) -> LSTMModel
  - walk_forward_validate(data: DataFrame, model_config: Dict) -> ValidationResults
  - generate_forecast(features: DataFrame, model: Model) -> ForecastResult

Model Specifications:
  - Baselines: HAR-RV, Lasso, LightGBM
  - Primary: LSTM with 90-day lookback, regression + classification heads
  - Loss: Huber loss (regression) + 0.2× cross-entropy (classification)
  - Regularization: Dropout 0.1, early stopping, train-only scaling
```

### Signal Generation Module
```
Interface: SignalGenerator
Methods:
  - generate_signal(forecast: ForecastResult, thresholds: Dict) -> SignalResult
  - calibrate_thresholds(validation_data: DataFrame) -> Dict[str, float]
  - apply_regime_filters(signal: SignalResult, regime_data: Dict) -> SignalResult

Signal Outputs:
  - forecast_value: Predicted ”DVOL
  - direction: {LONG, SHORT, FLAT}
  - confidence: Calibrated uncertainty measure
  - horizon: {1d, 7d, 14d}
```

### Trade Execution Module
```
Interface: TradeExecutor
Methods:
  - map_signal_to_position(signal: SignalResult) -> PositionRequest
  - execute_dvol_future_trade(position: PositionRequest) -> ExecutionResult
  - execute_options_strategy(position: PositionRequest) -> ExecutionResult
  - apply_risk_controls(position: PositionRequest) -> RiskCheckResult

Position Mapping Rules:
  - If w e +Ä ’ Long 1 DVOL future (or long ATM straddle, 7-21d, delta-hedged daily)
  - If w d -Ä ’ Short 1 DVOL future (or short strangle/iron condor, risk-defined)
  - Else ’ Flat

Risk Controls:
  - Max contracts/vega limits
  - Event guardrails (reduce size on jump/funding spikes)
  - Daily stop-loss and kill-switch
```

### Monitoring & Evaluation Module
```
Interface: MonitoringEngine
Methods:
  - track_forecast_metrics(predictions: List, actuals: List) -> ForecastMetrics
  - track_trading_metrics(trades: List, pnl: List) -> TradingMetrics
  - detect_feature_drift(current_features: DataFrame, baseline: DataFrame) -> DriftReport
  - generate_daily_report() -> PerformanceReport

Metrics Tracked:
  - Forecast: RMSE, MAE, Spearman correlation, hit rate
  - Trading: Sharpe, Sortino, max drawdown, turnover, tail loss
  - Operational: Data freshness, model stability, P&L attribution
```

## Open Questions/Risks

### Data & Infrastructure Risks
- **Market risk**: Volatility regime shifts and clustered jumps that can overwhelm short-volatility structures
- **Model risk**: Overfitting to short sample; feature drift where relationships change; under-estimated costs
- **Operational risk**: Data lags, API downtime, incomplete options snapshots, time-zone mishandling

### Technical Uncertainties
- Exact availability and definition of options summary fields (whether net vega can be derived reliably each day)
- Contract specifications and liquidity patterns for DVOL futures across time
- Whether to prefer percentage or absolute changes in DVOL for each horizon
- Inclusion criteria and lags for on-chain metrics to guarantee availability before cut-off

### Regulatory & Compliance
- Clear audit logs and reproducible runs required
- Change-control with approvals before deployment of new models or thresholds
- Hard caps on vega exposure per asset and maximum leverage utilization

## Milestones

### Phase 1: Data Pipeline & Baselines (Weeks 1-2)
- **Deliverable**: Build and validate daily ETL and feature table
- **Success Criteria**: Data quality dashboards operational, feature leakage checks pass
- **Outputs**: Clean datasets, feature dictionary

### Phase 2: Model Development (Weeks 3-4)
- **Deliverable**: Implement baselines (HAR, linear) and tree models
- **Success Criteria**: First expanding-window backtests complete, preliminary threshold calibration
- **Outputs**: Baseline model performance reports

### Phase 3: Advanced Modeling (Weeks 5-6)
- **Deliverable**: Implement LSTM sequence model with uncertainty calibration
- **Success Criteria**: Model beats baselines on validation metrics, robustness tests complete
- **Outputs**: Model comparison reports, hyperparameter optimization results

### Phase 4: Trading Simulation (Week 7)
- **Deliverable**: Options engine with delta-hedging simulator
- **Success Criteria**: Cost curves validated, stress tests complete, DVOL futures vs options comparison
- **Outputs**: Trading simulation reports with Sharpe/drawdown metrics

### Phase 5: Paper Trading & Production Readiness (Week 8)
- **Deliverable**: Paper-trade launch with monitoring infrastructure
- **Success Criteria**: Weekly governance review complete, go/no-go decision for limited production
- **Outputs**: Live signal service, execution notebooks, monitoring dashboards

---

## Review & Acceptance Checklist

### Architecture Completeness
- [ ] All module interfaces defined with clear input/output contracts
- [ ] Data flow between modules specified
- [ ] Error handling and failure modes identified
- [ ] Scalability and performance requirements addressed

### Risk Management
- [ ] Market, model, and operational risks catalogued
- [ ] Risk controls and limits clearly specified
- [ ] Monitoring and alerting systems defined
- [ ] Regulatory and compliance requirements addressed

### Success Criteria Validation
- [ ] Metrics are measurable and testable
- [ ] Thresholds are realistic based on research literature
- [ ] Out-of-sample validation methodology specified
- [ ] Performance benchmarks established

---