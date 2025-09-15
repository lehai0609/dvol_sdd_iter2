from __future__ import annotations

import pytest


# Helper to import within tests so missing models cause a clean FAIL (not ImportError at collection)
def _import_models():
    try:
        from dvol_data_ingest.models.api_responses import (
            DVOLApiResponse,
            FundingRatesApiResponse,
            FuturesOHLCVApiResponse,
            OnChainDataApiResponse,
            OptionsSummaryApiResponse,
        )
    except Exception as e:  # pragma: no cover
        pytest.fail(f"API response models not implemented or import failed: {e}")
    return (
        DVOLApiResponse,
        OptionsSummaryApiResponse,
        FuturesOHLCVApiResponse,
        FundingRatesApiResponse,
        OnChainDataApiResponse,
    )


def test_dvol_api_response_valid():
    (DVOLApiResponse, *_rest) = _import_models()
    payload = {
        "date": "2024-06-30",
        "unix": "1719705600000",
        "symbol": "BTC",
        "open": "40.6",
        "high": "41.0",
        "low": "39.9",
        "close": "40.2",
    }
    model = DVOLApiResponse(**payload)  # type: ignore[arg-type]
    assert model.symbol in ("BTC", "ETH")


def test_dvol_api_response_invalid_symbol():
    (DVOLApiResponse, *_rest) = _import_models()
    bad = {
        "date": "2024-06-30",
        "unix": "1719705600000",
        "symbol": "DOGE",
        "open": "40.6",
        "high": "41.0",
        "low": "39.9",
        "close": "40.2",
    }
    with pytest.raises(Exception):
        DVOLApiResponse(**bad)  # type: ignore[arg-type]


def test_options_summary_api_response_valid():
    (_dvol, OptionsSummaryApiResponse, *_rest) = _import_models()
    payload = {
        "date": "2024-06-11",
        "underlying": "BTC",
        "maturity": "2024-12-27",
        "net_delta": -9.07,
        "buy_delta": 3.28,
        "sell_delta": -12.35,
        "net_gamma": 0,
        "net_vega": 5468.11,
        "net_theta": -522.42,
        "avg_iv": 67.93,
        "volume": 134.3,
        "buy_volume": 89,
        "sell_volume": 45.3,
        "usd_volume": 1742711,
    }
    model = OptionsSummaryApiResponse(**payload)  # type: ignore[arg-type]
    assert model.underlying in ("BTC", "ETH")


def test_options_summary_api_response_invalid_maturity():
    (_dvol, OptionsSummaryApiResponse, *_rest) = _import_models()
    bad = {
        "date": "2024-06-11",
        "underlying": "BTC",
        "maturity": "2024-06-10",  # maturity before date
        "net_delta": 0,
        "buy_delta": 0,
        "sell_delta": 0,
        "net_gamma": 0,
        "net_vega": 0,
        "net_theta": 0,
        "avg_iv": 10,
        "volume": 0,
        "buy_volume": 0,
        "sell_volume": 0,
        "usd_volume": 0,
    }
    with pytest.raises(Exception):
        OptionsSummaryApiResponse(**bad)  # type: ignore[arg-type]


def test_futures_ohlcv_api_response_valid():
    (_dvol, _opt, FuturesOHLCVApiResponse, *_rest) = _import_models()
    payload = {
        "unix": 1693209600000,
        "date": "2023-08-28 08:00:00",
        "symbol": "BTC-PERPETUAL",
        "open": "25912.0",
        "high": "26231.5",
        "low": "25847.5",
        "close": "25994.5",
        "volume": "5492.31432737",
        "base_volume": "143083810.0",
    }
    model = FuturesOHLCVApiResponse(**payload)  # type: ignore[arg-type]
    assert model.symbol.startswith(("BTC", "ETH"))


def test_funding_rates_api_response_valid():
    (_dvol, _opt, _fut, FundingRatesApiResponse, _onchain) = _import_models()
    payload = {
        "date": "2023-08-30 00:00:00",
        "unix": "1693353600000",
        "symbol": "BTC-PERPETUAL",
        "index_price": "27720.56",
        "prev_index_price": "27642.6",
        "interest_8h": "-1.4691613145727188e-05",
        "interest_1h": "-1.03824239374694e-08",
    }
    model = FundingRatesApiResponse(**payload)  # type: ignore[arg-type]
    assert model.symbol.endswith("-PERPETUAL")


def test_onchain_data_api_response_valid():
    (_dvol, _opt, _fut, _fund, OnChainDataApiResponse) = _import_models()
    payload = {
        "date": "2024-06-11",
        "symbol": "btc",
        "total_transactions": 123,
        "total_block_count": 12,
    }
    model = OnChainDataApiResponse(**payload)  # type: ignore[arg-type]
    assert model.symbol in ("btc", "eth")

