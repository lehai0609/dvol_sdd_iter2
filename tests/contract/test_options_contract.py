from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
import requests
from dotenv import load_dotenv
from jsonschema import validate

CONTRACT_PATH = Path(
    "specs/003-data-ingest-module-spec/contracts/options_api_contract.json"
)


def load_contract_schema() -> dict[str, Any]:
    with CONTRACT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def example_payload() -> dict[str, Any]:
    return {
        "result": [
            {
                "date": "2024-06-11",
                "underlying": "BTC",
                "maturity": "2025-03-28",
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
        ]
    }


def test_contract_schema_validates_example():
    doc = load_contract_schema()
    payload = example_payload()
    response_schema = (
        doc["paths"][
            "/v1/data/summary/deribit/options/greeks/maturities/"
        ]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    )
    full_schema = {"allOf": [response_schema], "components": doc.get("components", {})}
    validate(instance=payload, schema=full_schema)


@pytest.mark.parametrize("underlying", ["BTC", "ETH"])
def test_live_endpoint_matches_contract_when_token_available(underlying: str):
    load_dotenv(override=False)
    token = os.getenv("CDD_API_KEY") or os.getenv("CDD_API_TOKEN")
    if not token:
        pytest.skip("CDD_API_KEY not set; skipping live contract check")

    base_url = (
        os.getenv("CDD_API_BASE_URL", "https://api.cryptodatadownload.com/v1").rstrip("/")
    )
    url = f"{base_url}/data/summary/deribit/options/greeks/maturities/"

    headers = {"Authorization": f"TOKEN {token}", "accept": "application/json"}
    params = {"underlying": underlying, "limit": 1, "return": "JSON"}

    r = requests.get(url, headers=headers, params=params, timeout=30)
    if r.status_code == 401:
        params["auth_token"] = token
        headers.pop("Authorization", None)
        r = requests.get(url, headers=headers, params=params, timeout=30)

    if r.status_code == 401:
        pytest.xfail("Unauthorized: verify CDD token and auth method")

    assert r.status_code == 200, f"Unexpected status {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, dict) and "result" in data and isinstance(data["result"], list)

    schema = load_contract_schema()
    item_schema_ref = schema["components"]["schemas"]["OptionsSummaryItem"]
    if data["result"]:
        full_item_schema = {"allOf": [item_schema_ref], "components": schema.get("components", {})}
        validate(instance=data["result"][0], schema=full_item_schema)
