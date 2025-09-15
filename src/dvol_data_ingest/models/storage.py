"""Storage data models for normalized records.

Implements T017:
- DVOLRecord
- OptionsSummaryRecord
- OHLCVRecord
- FundingRecord
- OnChainRecord

Each model includes basic metadata fields used during ingestion.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class IngestionMetadata(BaseModel):
    """Common metadata for all ingested records.

    Includes helpers to compute a stable checksum and to construct
    metadata from an arbitrary record-like object.
    """

    data_source: str = Field(description="Source system identifier (e.g., 'cdd_api')")
    ingestion_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="UTC ingestion timestamp"
    )
    checksum: str = Field(description="SHA-256 hash of record content for integrity")
    api_response_timestamp: datetime | None = Field(
        default=None, description="Timestamp from API response headers"
    )
    pipeline_version: str = Field(description="Version of ingestion pipeline")

    @staticmethod
    def calc_checksum(obj: Any) -> str:
        payload = json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def from_obj(
        cls,
        obj: Any,
        *,
        data_source: str,
        pipeline_version: str,
        api_response_timestamp: datetime | None = None,
    ) -> IngestionMetadata:
        return cls(
            data_source=data_source,
            pipeline_version=pipeline_version,
            api_response_timestamp=api_response_timestamp,
            checksum=cls.calc_checksum(obj),
        )


class DVOLRecord(IngestionMetadata):
    """Normalized DVOL record for Parquet storage."""

    asset: Literal["BTC", "ETH"] = Field(description="Cryptocurrency asset")
    date_utc: date = Field(description="Trading date in UTC")
    unix_ms: int = Field(description="Unix timestamp in milliseconds (UTC)")
    symbol: str = Field(description="Original API symbol")
    open: float = Field(gt=0, description="Opening 30-day IV")
    high: float = Field(gt=0, description="Daily high 30-day IV")
    low: float = Field(gt=0, description="Daily low 30-day IV")
    close: float = Field(gt=0, description="Closing 30-day IV")

    # Default metadata values
    data_source: str = Field(default="cdd_dvol")
    pipeline_version: str = Field(default="0.0.0")


class OptionsSummaryRecord(IngestionMetadata):
    """Normalized options summary record for Parquet storage."""

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

    # Default metadata values
    data_source: str = Field(default="cdd_options")
    pipeline_version: str = Field(default="0.0.0")


class OHLCVRecord(IngestionMetadata):
    """Normalized OHLCV record for Parquet storage."""

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

    # Default metadata values
    data_source: str = Field(default="cdd_futures")
    pipeline_version: str = Field(default="0.0.0")


class FundingRecord(IngestionMetadata):
    """Normalized funding record for Parquet storage."""

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

    # Default metadata values
    data_source: str = Field(default="cdd_funding")
    pipeline_version: str = Field(default="0.0.0")


class OnChainRecord(IngestionMetadata):
    """Normalized on-chain record for Parquet storage."""

    asset: Literal["BTC", "ETH"] = Field(description="Blockchain asset")
    date_utc: date = Field(description="Trading date in UTC")
    total_transactions: int = Field(ge=0, description="Daily transaction count")
    total_block_cnt: int = Field(ge=0, description="Daily block count")
    avg_secs_between_blocks: float = Field(gt=0, description="Average block time")
    avg_block_size_mb: float = Field(ge=0, description="Average block size MB")
    hashrate: float = Field(ge=0, description="Network hashrate")
    avg_transactions_count_per_block: float = Field(
        ge=0, description="Avg txns per block"
    )

    # ETH-specific fields (nullable for BTC records)
    avg_gas_limit: float | None = Field(None, description="Average gas limit")
    total_gas_used_in_eth: float | None = Field(None, description="Total gas used")
    block_utilization: float | None = Field(None, description="Block utilization %")
    complexity_score: float | None = Field(None, description="Network complexity")
    first_block: int = Field(description="First block in range")
    last_block: int = Field(description="Last block in range")

    # Default metadata values
    data_source: str = Field(default="cdd_onchain")
    pipeline_version: str = Field(default="0.0.0")


__all__ = [
    "IngestionMetadata",
    "DVOLRecord",
    "OptionsSummaryRecord",
    "OHLCVRecord",
    "FundingRecord",
    "OnChainRecord",
]
