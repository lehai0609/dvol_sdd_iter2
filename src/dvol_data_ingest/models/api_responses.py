"""API response models for CryptoDataDownload endpoints.

Implements T012–T016:
- DVOLApiResponse
- OptionsSummaryApiResponse
- FuturesOHLCVApiResponse
- FundingRatesApiResponse
- OnChainDataApiResponse

Notes:
- Keep parsing permissive (accept str/int for numerics) while enforcing
  core constraints required by tests (e.g., symbol enums, non-negative
  volumes, date ordering for options maturity, etc.).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def _parse_int_ms(value: int | str) -> int:
    if isinstance(value, int):
        return value
    # allow strings containing integer milliseconds
    try:
        iv = int(str(value))
    except (TypeError, ValueError) as e:  # pragma: no cover - defensive
        raise ValueError("unix must be an integer milliseconds timestamp") from e
    if iv < 0:
        raise ValueError("unix must be non-negative milliseconds")
    return iv


def _parse_float(value: float | int | str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as e:  # pragma: no cover - defensive
        raise ValueError("value must be numeric") from e


def _parse_date(value: str) -> date:
    # Accept ISO date format: YYYY-MM-DD
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError("date must be YYYY-MM-DD") from e


def _parse_datetime(value: str) -> datetime:
    # Accept format: YYYY-MM-DD HH:MM:SS
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        raise ValueError("datetime must be YYYY-MM-DD HH:MM:SS") from e


class DVOLApiResponse(BaseModel):
    """DVOL OHLC response item."""

    date: str = Field(..., description="Trading date YYYY-MM-DD")
    unix: int = Field(..., description="Unix timestamp in milliseconds")
    symbol: Literal["BTC", "ETH"]
    open: float
    high: float
    low: float
    close: float

    @field_validator("unix", mode="before")
    @classmethod
    def _coerce_unix(cls, v):
        return _parse_int_ms(v)

    @field_validator("date")
    @classmethod
    def _validate_date(cls, v: str) -> str:
        _ = _parse_date(v)
        return v

    @field_validator("open", "high", "low", "close", mode="before")
    @classmethod
    def _coerce_ohlc(cls, v):
        val = _parse_float(v)
        if val <= 0:
            raise ValueError("OHLC values must be positive")
        return val


class OptionsSummaryApiResponse(BaseModel):
    """Options greeks summary per maturity."""

    date: str = Field(..., description="As-of date YYYY-MM-DD")
    underlying: Literal["BTC", "ETH"]
    maturity: str = Field(..., description="Maturity date YYYY-MM-DD")

    net_delta: float
    buy_delta: float
    sell_delta: float
    net_gamma: float
    net_vega: float
    net_theta: float

    avg_iv: float = Field(..., description="Average IV; non-negative")

    volume: float = Field(..., ge=0)
    buy_volume: float = Field(..., ge=0)
    sell_volume: float = Field(..., ge=0)
    usd_volume: float = Field(..., ge=0)

    @field_validator("date")
    @classmethod
    def _opts_date(cls, v: str) -> str:
        _parse_date(v)
        return v

    @field_validator("maturity")
    @classmethod
    def _opts_maturity_format(cls, v: str) -> str:
        _parse_date(v)
        return v

    @field_validator(
        "net_delta",
        "buy_delta",
        "sell_delta",
        "net_gamma",
        "net_vega",
        "net_theta",
        "avg_iv",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v):
        return _parse_float(v)

    @model_validator(mode="after")
    def _validate_maturity_after_date(self):
        asof = _parse_date(self.date)
        mat = _parse_date(self.maturity)
        if mat < asof:
            raise ValueError("maturity must be on/after date")
        if self.avg_iv < 0:
            raise ValueError("avg_iv must be non-negative")
        return self


class FuturesOHLCVApiResponse(BaseModel):
    """Futures OHLCV response item."""

    unix: int
    date: str = Field(..., description="Candle timestamp YYYY-MM-DD HH:MM:SS")
    symbol: str = Field(..., description="e.g., BTC-PERPETUAL")
    open: float
    high: float
    low: float
    close: float
    volume: float = Field(..., ge=0)
    base_volume: float = Field(..., ge=0)

    @field_validator("unix", mode="before")
    @classmethod
    def _fut_unix(cls, v):
        return _parse_int_ms(v)

    @field_validator("date")
    @classmethod
    def _fut_date(cls, v: str) -> str:
        _parse_datetime(v)
        return v

    @field_validator("open", "high", "low", "close", mode="before")
    @classmethod
    def _fut_ohlc(cls, v):
        val = _parse_float(v)
        if val <= 0:
            raise ValueError("OHLC values must be positive")
        return val

    @field_validator("volume", "base_volume", mode="before")
    @classmethod
    def _fut_volume(cls, v):
        val = _parse_float(v)
        if val < 0:
            raise ValueError("volume must be non-negative")
        return val

    @field_validator("symbol")
    @classmethod
    def _fut_symbol(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("symbol must be a string")
        if "-PERPETUAL" not in v:
            raise ValueError("symbol must include '-PERPETUAL'")
        return v


class FundingRatesApiResponse(BaseModel):
    """Funding rates response item."""

    date: str = Field(..., description="YYYY-MM-DD HH:MM:SS")
    unix: int
    symbol: str = Field(..., description="e.g., BTC-PERPETUAL")
    index_price: float
    prev_index_price: float
    interest_8h: float
    interest_1h: float

    @field_validator("unix", mode="before")
    @classmethod
    def _fund_unix(cls, v):
        return _parse_int_ms(v)

    @field_validator("date")
    @classmethod
    def _fund_date(cls, v: str) -> str:
        _parse_datetime(v)
        return v

    @field_validator("index_price", "prev_index_price", mode="before")
    @classmethod
    def _fund_prices(cls, v):
        val = _parse_float(v)
        if val <= 0:
            raise ValueError("index prices must be positive")
        return val

    @field_validator("interest_8h", "interest_1h", mode="before")
    @classmethod
    def _fund_interest(cls, v):
        return _parse_float(v)

    @field_validator("symbol")
    @classmethod
    def _fund_symbol(cls, v: str) -> str:
        if not isinstance(v, str) or not v.endswith("-PERPETUAL"):
            raise ValueError("symbol must end with -PERPETUAL")
        return v


class OnChainDataApiResponse(BaseModel):
    """On-chain blocks summary response item."""

    date: str = Field(..., description="YYYY-MM-DD")
    symbol: Literal["btc", "eth"]

    total_transactions: int = Field(..., ge=0)
    total_block_count: int = Field(..., ge=0)

    avg_seconds_between_blocks: float | None = None
    avg_block_size: float | None = None
    hashrate: float | None = None
    avg_transaction_count: float | None = None
    first_block: int | None = None
    last_block: int | None = None

    @field_validator("date")
    @classmethod
    def _onchain_date(cls, v: str) -> str:
        _parse_date(v)
        return v

