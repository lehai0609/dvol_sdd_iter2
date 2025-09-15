from __future__ import annotations

import os
from typing import Any

import pytest
import requests


class FakeResp:
    def __init__(self, status_code: int = 200, json_data: Any | None = None, url: str = "http://test"):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {"result": []}
        self.url = url

    def json(self) -> Any:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("CDD_API_KEY", "XYZ")
    monkeypatch.setenv("CDD_API_BASE_URL", "https://api.cryptodatadownload.com/v1")


def test_dvol_client_path_and_params(mocker):
    from dvol_data_ingest.clients.dvol import DVOLClient, DVOL_PATH

    spy = mocker.patch(
        "requests.Session.request",
        return_value=FakeResp(200, {"result": []}, url=f"https://api.cryptodatadownload.com/v1{DVOL_PATH}"),
    )

    with DVOLClient() as c:
        c.fetch(symbol="BTC", limit=200)

    assert spy.called
    _a, kw = spy.call_args
    assert kw["url"].endswith(DVOL_PATH)
    assert kw["params"]["symbol"] == "BTC"
    assert kw["params"]["limit"] == 200
    assert kw["params"]["return"] == "JSON"


def test_futures_client_maps_end_to_enddate(mocker):
    from dvol_data_ingest.clients.futures import FuturesClient, FUTURES_PATH

    spy = mocker.patch(
        "requests.Session.request",
        return_value=FakeResp(200, {"result": []}, url=f"https://api.cryptodatadownload.com/v1{FUTURES_PATH}"),
    )

    with FuturesClient() as c:
        c.fetch(symbol="BTC-PERPETUAL", end="2024-12-31", limit=100)

    _a, kw = spy.call_args
    assert kw["url"].endswith(FUTURES_PATH)
    assert kw["params"]["symbol"] == "BTC-PERPETUAL"
    assert kw["params"]["enddate"] == "2024-12-31"
    assert kw["params"]["limit"] == 100


def test_funding_client_uses_correct_path_and_enddate(mocker):
    from dvol_data_ingest.clients.funding import FundingClient, FUNDING_PATH

    spy = mocker.patch(
        "requests.Session.request",
        return_value=FakeResp(200, {"result": []}, url=f"https://api.cryptodatadownload.com/v1{FUNDING_PATH}"),
    )

    with FundingClient() as c:
        c.fetch(symbol="BTC-PERPETUAL", start="2024-12-01", end="2024-12-31", limit=50)

    _a, kw = spy.call_args
    assert kw["url"].endswith(FUNDING_PATH)
    assert kw["params"]["symbol"] == "BTC-PERPETUAL"
    # end has precedence for enddate mapping
    assert kw["params"]["enddate"] == "2024-12-31"
    assert kw["params"]["limit"] == 50


def test_options_client_maps_date_to_enddate_and_supports_limit(mocker):
    from dvol_data_ingest.clients.options import OptionsClient, OPTIONS_PATH

    spy = mocker.patch(
        "requests.Session.request",
        return_value=FakeResp(200, {"result": []}, url=f"https://api.cryptodatadownload.com/v1{OPTIONS_PATH}"),
    )

    with OptionsClient() as c:
        c.fetch(underlying="BTC", date="2024-12-31", limit=25)

    _a, kw = spy.call_args
    assert kw["url"].endswith(OPTIONS_PATH)
    assert kw["params"]["underlying"] == "BTC"
    assert kw["params"]["enddate"] == "2024-12-31"
    assert kw["params"]["limit"] == 25


def test_onchain_client_maps_date_to_enddate_and_supports_limit(mocker):
    from dvol_data_ingest.clients.onchain import OnChainClient, ONCHAIN_PATH

    spy = mocker.patch(
        "requests.Session.request",
        return_value=FakeResp(200, {"result": []}, url=f"https://api.cryptodatadownload.com/v1{ONCHAIN_PATH}"),
    )

    with OnChainClient() as c:
        c.fetch(symbol="btc", date="2024-12-31", limit=10)

    _a, kw = spy.call_args
    assert kw["url"].endswith(ONCHAIN_PATH)
    assert kw["params"]["symbol"] == "btc"
    assert kw["params"]["enddate"] == "2024-12-31"
    assert kw["params"]["limit"] == 10

