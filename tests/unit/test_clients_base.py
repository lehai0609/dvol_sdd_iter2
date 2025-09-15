from __future__ import annotations

import os
from typing import Any

import pytest
import requests


class FakeResp:
    def __init__(self, status_code: int = 200, json_data: Any | None = None, url: str = "http://test"):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {"ok": True}
        self.url = url

    def json(self) -> Any:  # noqa: D401
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)


def test_request_sets_token_auth_and_json_param(monkeypatch, mocker):
    from dvol_data_ingest.clients.base import CDDClient

    monkeypatch.setenv("CDD_API_KEY", "XYZ")
    monkeypatch.setenv("CDD_API_BASE_URL", "https://api.example.com/v1")

    call_spy = mocker.patch(
        "requests.Session.request",
        return_value=FakeResp(200, {"result": []}, url="https://api.example.com/v1/data/foo"),
    )

    with CDDClient() as c:
        c.request("GET", "/data/foo", params={"symbol": "BTC"})

    assert call_spy.call_count == 1
    args, kwargs = call_spy.call_args
    assert kwargs["url"] == "https://api.example.com/v1/data/foo"
    # Authorization header uses TOKEN scheme
    assert kwargs["headers"]["Authorization"] == "TOKEN XYZ"
    # "return" defaults to JSON unless provided
    assert kwargs["params"]["return"] == "JSON"
    assert kwargs["params"]["symbol"] == "BTC"


def test_unauthorized_fallbacks_to_auth_token_query(monkeypatch, mocker):
    from dvol_data_ingest.clients.base import CDDClient

    monkeypatch.setenv("CDD_API_KEY", "XYZ")
    monkeypatch.setenv("CDD_API_BASE_URL", "https://api.example.com/v1")

    # First call returns 401; second succeeds
    call_spy = mocker.patch(
        "requests.Session.request",
        side_effect=[
            FakeResp(401, url="https://api.example.com/v1/data/foo"),
            FakeResp(200, {"result": []}, url="https://api.example.com/v1/data/foo"),
        ],
    )

    with CDDClient() as c:
        out = c.request("GET", "/data/foo", params={})
        assert out.status_code == 200

    # Verify two calls: first with Authorization header, second without header but with auth_token param
    assert call_spy.call_count == 2
    _args1, kwargs1 = call_spy.call_args_list[0]
    _args2, kwargs2 = call_spy.call_args_list[1]

    assert kwargs1["headers"].get("Authorization", "").startswith("TOKEN ")
    assert "auth_token" not in kwargs1["params"]

    assert "Authorization" not in kwargs2["headers"]
    assert kwargs2["params"].get("auth_token") == "XYZ"

