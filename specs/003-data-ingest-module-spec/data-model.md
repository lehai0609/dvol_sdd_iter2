# Data Model: DVOL Data Ingestion Pipeline

**Feature**: 01_data_ingest - DVOL Data Ingestion Pipeline
**Date**: 2025-09-14
**Version**: 1.0.0

## Overview

This document defines the data models for the DVOL data ingestion pipeline, including API response schemas, internal data structures, and storage table schemas. All models use Pydantic for runtime validation and type safety.

## Common Metadata Schema

All data records include common metadata fields for auditing and reproducibility:

```python
class IngestionMetadata(BaseModel):
    """Common metadata for all ingested records"""
    data_source: str = Field(description="Source system identifier (e.g., 'cdd_api')")
    ingestion_timestamp: datetime = Field(description="UTC timestamp when record was ingested")
    checksum: str = Field(description="SHA-256 hash of record content for integrity verification")
    api_response_timestamp: Optional[datetime] = Field(None, description="Timestamp from API response headers")
    pipeline_version: str = Field(description="Version of ingestion pipeline that processed this record")
```

## API Response Models

### 1. DVOL Daily OHLC Response

**Endpoint**: `/v1/data/ohlc/deribit/volatility`

```python
class DVOLApiResponse(BaseModel):
    """Response schema for CDD DVOL endpoint"""
    Date: str = Field(description="Date in YYYY-MM-DD format")
    Unix: int = Field(description="Unix timestamp in milliseconds")
    Symbol: Literal["BTC", "ETH"] = Field(description="Cryptocurrency symbol")
    Open: float = Field(gt=0, description="Opening 30-day implied volatility")
    High: float = Field(gt=0, description="Daily high 30-day implied volatility")
    Low: float = Field(gt=0, description="Daily low 30-day implied volatility")
    Close: float = Field(gt=0, description="Closing 30-day implied volatility")

    @field_validator('Unix')
    def validate_unix_timestamp(cls, v):
        """Validate Unix timestamp is reasonable (post-2020, pre-future)"""
        min_timestamp = 1577836800000  # 2020-01-01
        max_timestamp = int(time.time() * 1000) + 86400000  # Current time + 1 day
        if not (min_timestamp <= v <= max_timestamp):
            raise ValueError(f"Unix timestamp {v} outside valid range")
        return v
```

### 2. Options Summary Response

**Endpoint**: `/v1/data/summary/deribit/options/greeks/maturities/`

```python
class OptionsSummaryApiResponse(BaseModel):
    """Response schema for CDD Options Summary endpoint"""
    Date: str = Field(description="Date in YYYY-MM-DD format")
    Underlying: Literal["BTC", "ETH"] = Field(description="Underlying asset symbol")
    Maturity: str = Field(description="Option maturity date in YYYY-MM-DD format")
    Net_Delta: float = Field(description="Net delta across all option contracts")
    Buy_Delta: float = Field(ge=0, description="Delta from buy-side option contracts")
    Sell_Delta: float = Field(le=0, description="Delta from sell-side option contracts")
    Net_Gamma: float = Field(description="Net gamma across all option contracts")
    Net_Vega: float = Field(description="Net vega exposure in USD")
    Net_Theta: float = Field(description="Net theta decay in USD per day")
    Avg_IV: float = Field(ge=0, le=5, description="Average implied volatility")
    Volume: int = Field(ge=0, description="Total option volume")
    Buy_Volume: int = Field(ge=0, description="Buy-side option volume")
    Sell_Volume: int = Field(ge=0, description="Sell-side option volume")
    USD_Volume: float = Field(ge=0, description="Total volume in USD")

    @field_validator('Maturity')
    def validate_maturity_date(cls, v, info):
        """Validate maturity is after trade date"""
        trade_date = datetime.strptime(info.data['Date'], '%Y-%m-%d').date()
        maturity_date = datetime.strptime(v, '%Y-%m-%d').date()
        if maturity_date <= trade_date:
            raise ValueError(f"Maturity {v} must be after trade date {info.data['Date']}")
        return v
```

### 3. Futures OHLCV Response

**Endpoint**: `/v1/data/ohlc/deribit/futures/`

```python
class FuturesOHLCVApiResponse(BaseModel):
    """Response schema for CDD Futures OHLCV endpoint"""
    Unix: int = Field(description="Unix timestamp in milliseconds")
    Date: str = Field(description="Date in YYYY-MM-DD format")
    Symbol: str = Field(description="Full futures contract symbol")
    Open: float = Field(gt=0, description="Opening price")
    High: float = Field(gt=0, description="Daily high price")
    Low: float = Field(gt=0, description="Daily low price")
    Close: float = Field(gt=0, description="Closing price")
    Volume: float = Field(ge=0, description="Volume in base currency")
    Base_Volume: float = Field(ge=0, description="Volume in USD")

    @computed_field
    @property
    def asset(self) -> str:
        """Extract asset (BTC/ETH) from symbol"""
        if self.Symbol.startswith('BTC'):
            return 'BTC'
        elif self.Symbol.startswith('ETH'):
            return 'ETH'
        else:
            raise ValueError(f"Cannot determine asset from symbol: {self.Symbol}")
```

### 4. Funding Rates Response

**Endpoint**: `/v1/data/ohlc/deribit/funding`

```python
class FundingRatesApiResponse(BaseModel):
    """Response schema for CDD Funding Rates endpoint"""
    Date: str = Field(description="Date in YYYY-MM-DD format")
    Unix: int = Field(description="Unix timestamp in milliseconds")
    Symbol: Literal["BTC-PERPETUAL", "ETH-PERPETUAL"] = Field(description="Perpetual contract symbol")
    Index_Price: float = Field(gt=0, description="Index price at observation time")
    Prev_Index_Price: float = Field(gt=0, description="Previous index price")
    Interest_8H: float = Field(description="8-hour funding interest rate")
    Interest_1H: float = Field(description="1-hour funding interest rate")

    @computed_field
    @property
    def asset(self) -> str:
        """Extract asset from perpetual symbol"""
        return self.Symbol.split('-')[0]  # BTC-PERPETUAL -> BTC
```

### 5. On-Chain Data Response

**Endpoint**: `/v1/data/summary/blockchain/blocks/`

```python
class OnChainDataApiResponse(BaseModel):
    """Response schema for CDD On-Chain Data endpoint"""
    Date: str = Field(description="Date in YYYY-MM-DD format")
    Symbol: Literal["btc", "eth"] = Field(description="Blockchain symbol (lowercase)")
    Total_Transactions: int = Field(ge=0, description="Total transactions in blocks")
    Total_Block_Count: int = Field(ge=0, description="Number of blocks mined")
    Average_Difficulty: float = Field(ge=0, description="Average block difficulty")
    Avg_Seconds_Between_Blocks: float = Field(gt=0, description="Average block time")
    Avg_Block_Size_MB: float = Field(ge=0, description="Average block size in MB")
    Hashrate: float = Field(ge=0, description="Network hashrate")
    Avg_Transactions_Count_Per_Block: float = Field(ge=0, description="Average transactions per block")

    # ETH-specific fields (nullable for BTC)
    Avg_Gas_Limit: Optional[float] = Field(None, ge=0, description="Average gas limit (ETH only)")
    Total_Gas_Used_in_ETH: Optional[float] = Field(None, ge=0, description="Total gas used in ETH (ETH only)")
    Block_Utilization: Optional[float] = Field(None, ge=0, le=1, description="Block utilization percentage (ETH only)")
    Complexity_Score: Optional[float] = Field(None, ge=0, description="Network complexity score (ETH only)")
    First_Block: int = Field(description="First block number in daily range")
    Last_Block: int = Field(description="Last block number in daily range")

    @field_validator('Avg_Gas_Limit', 'Total_Gas_Used_in_ETH', 'Block_Utilization', 'Complexity_Score')
    def validate_eth_fields(cls, v, info):
        """ETH-specific fields should only be present for ETH data"""
        if info.data.get('Symbol') == 'btc' and v is not None:
            raise ValueError(f"ETH-specific field should be null for BTC data")
        if info.data.get('Symbol') == 'eth' and v is None:
            raise ValueError(f"ETH-specific field should not be null for ETH data")
        return v

    @computed_field
    @property
    def asset(self) -> str:
        """Normalize symbol to uppercase asset"""
        return self.Symbol.upper()  # btc -> BTC, eth -> ETH
```

## Internal Storage Models

### 1. DVOL Records

```python
class DVOLRecord(BaseModel):
    """Normalized DVOL record for Parquet storage"""
    asset: Literal["BTC", "ETH"] = Field(description="Cryptocurrency asset")
    date_utc: date = Field(description="Trading date in UTC")
    unix_ms: int = Field(description="Unix timestamp in milliseconds (UTC)")
    symbol: str = Field(description="Original API symbol")
    open: float = Field(gt=0, description="Opening 30-day IV")
    high: float = Field(gt=0, description="Daily high 30-day IV")
    low: float = Field(gt=0, description="Daily low 30-day IV")
    close: float = Field(gt=0, description="Closing 30-day IV")

    # Metadata
    data_source: str = Field(default="cdd_dvol")
    ingestion_timestamp: datetime = Field(description="UTC ingestion time")
    checksum: str = Field(description="Record integrity hash")

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }
```

### 2. Options Summary Records

```python
class OptionsSummaryRecord(BaseModel):
    """Normalized options summary record for Parquet storage"""
    asset: Literal["BTC", "ETH"] = Field(description="Underlying asset")
    date_utc: date = Field(description="Trading date in UTC")
    maturity_utc: date = Field(description="Option maturity date in UTC")
    net_delta: float = Field(description="Net delta position")
    buy_delta: float = Field(ge=0, description="Buy-side delta")
    sell_delta: float = Field(le=0, description="Sell-side delta")
    net_gamma: float = Field(description="Net gamma exposure")
    net_vega: float = Field(description="Net vega in USD")
    net_theta: float = Field(description="Net theta decay USD/day")
    avg_iv: float = Field(ge=0, le=5, description="Volume-weighted average IV")
    volume: int = Field(ge=0, description="Total contract volume")
    buy_volume: int = Field(ge=0, description="Buy-side volume")
    sell_volume: int = Field(ge=0, description="Sell-side volume")
    usd_volume: float = Field(ge=0, description="USD notional volume")

    # Metadata
    data_source: str = Field(default="cdd_options")
    ingestion_timestamp: datetime = Field(description="UTC ingestion time")
    checksum: str = Field(description="Record integrity hash")
```

### 3. OHLCV Records

```python
class OHLCVRecord(BaseModel):
    """Normalized OHLCV record for Parquet storage"""
    asset: Literal["BTC", "ETH"] = Field(description="Base asset")
    symbol: str = Field(description="Full contract symbol")
    date_utc: date = Field(description="Trading date in UTC")
    unix_ms: int = Field(description="Unix timestamp in milliseconds (UTC)")
    open: float = Field(gt=0, description="Opening price")
    high: float = Field(gt=0, description="Daily high price")
    low: float = Field(gt=0, description="Daily low price")
    close: float = Field(gt=0, description="Closing price")
    volume_base: float = Field(ge=0, description="Volume in base currency")
    volume_usd: float = Field(ge=0, description="Volume in USD")

    # Metadata
    data_source: str = Field(default="cdd_futures")
    ingestion_timestamp: datetime = Field(description="UTC ingestion time")
    checksum: str = Field(description="Record integrity hash")
```

### 4. Funding Records

```python
class FundingRecord(BaseModel):
    """Normalized funding record for Parquet storage"""
    asset: Literal["BTC", "ETH"] = Field(description="Asset symbol")
    symbol: str = Field(description="Perpetual contract symbol")
    date_utc: date = Field(description="Trading date in UTC")
    unix_ms: int = Field(description="Unix timestamp in milliseconds (UTC)")
    index_price: float = Field(gt=0, description="Index price")
    prev_index_price: float = Field(gt=0, description="Previous index price")
    interest_8h: float = Field(description="8-hour funding rate")
    interest_1h: float = Field(description="1-hour funding rate")

    # Derived daily aggregates (computed from sub-daily data)
    funding_mean: float = Field(description="Daily mean funding rate")
    funding_std: float = Field(ge=0, description="Daily funding rate volatility")
    funding_5d_change: float = Field(description="5-day change in funding rate")

    # Metadata
    data_source: str = Field(default="cdd_funding")
    ingestion_timestamp: datetime = Field(description="UTC ingestion time")
    checksum: str = Field(description="Record integrity hash")
```

### 5. On-Chain Records

```python
class OnChainRecord(BaseModel):
    """Normalized on-chain record for Parquet storage"""
    asset: Literal["BTC", "ETH"] = Field(description="Blockchain asset")
    date_utc: date = Field(description="Trading date in UTC")
    total_transactions: int = Field(ge=0, description="Daily transaction count")
    total_block_cnt: int = Field(ge=0, description="Daily block count")
    avg_secs_between_blocks: float = Field(gt=0, description="Average block time")
    avg_block_size_mb: float = Field(ge=0, description="Average block size MB")
    hashrate: float = Field(ge=0, description="Network hashrate")
    avg_transactions_count_per_block: float = Field(ge=0, description="Avg txns per block")

    # ETH-specific fields (nullable for BTC records)
    avg_gas_limit: Optional[float] = Field(None, description="Average gas limit")
    total_gas_used_in_eth: Optional[float] = Field(None, description="Total gas used")
    block_utilization: Optional[float] = Field(None, description="Block utilization %")
    complexity_score: Optional[float] = Field(None, description="Network complexity")
    first_block: int = Field(description="First block in range")
    last_block: int = Field(description="Last block in range")

    # Metadata
    data_source: str = Field(default="cdd_onchain")
    ingestion_timestamp: datetime = Field(description="UTC ingestion time")
    checksum: str = Field(description="Record integrity hash")
```

## Parquet Table Schemas

### Storage Partitioning Strategy

All tables use the following partitioning scheme:
- **Primary partition**: `asset` (BTC, ETH)
- **Secondary partition**: `year` (extracted from date_utc)
- **Tertiary partition**: `month` (extracted from date_utc)

Example path: `data/raw_dvol/asset=BTC/year=2024/month=01/data_001.parquet`

### Schema Evolution

All schemas support backward-compatible evolution:
- New optional fields can be added without breaking existing readers
- Field renames require migration procedures
- Type changes require major version increments
- Schema version stored in Parquet metadata

### Data Validation Rules

1. **Temporal Consistency**: All dates must be UTC and align with trading day boundaries
2. **Cross-Reference Validation**: Asset symbols must be consistent between related tables
3. **Range Validation**: All financial values must pass domain-specific range checks
4. **Completeness Validation**: Required fields must be non-null
5. **Checksum Validation**: Record checksums must be valid SHA-256 hashes

## Entity Relationships

```
DVOLRecord ──┐
OptionsSummaryRecord ──┼── [asset, date_utc] ── Trading Day
OHLCVRecord ──┤
FundingRecord ──┤
OnChainRecord ──┘

IngestionMetadata ── [1:1] ── All Records
```

## Usage Examples

```python
# API Response Parsing
response_data = api_client.fetch_dvol_data("BTC")
validated_response = DVOLApiResponse.model_validate(response_data)

# Conversion to Storage Format
dvol_record = DVOLRecord(
    asset=validated_response.Symbol,
    date_utc=datetime.strptime(validated_response.Date, '%Y-%m-%d').date(),
    unix_ms=validated_response.Unix,
    symbol=validated_response.Symbol,
    open=validated_response.Open,
    high=validated_response.High,
    low=validated_response.Low,
    close=validated_response.Close,
    data_source="cdd_dvol",
    ingestion_timestamp=datetime.utcnow(),
    checksum=calculate_checksum(validated_response.dict())
)

# Parquet Storage
df = pd.DataFrame([dvol_record.dict()])
df.to_parquet('data/raw_dvol/asset=BTC/year=2024/month=01/data_001.parquet')
```

This data model provides type-safe, validated data structures that ensure data quality and consistency throughout the ingestion pipeline while supporting schema evolution and operational requirements.