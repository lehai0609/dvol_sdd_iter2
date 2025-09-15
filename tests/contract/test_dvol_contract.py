from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
import requests
from dotenv import load_dotenv
from jsonschema import validate

CONTRACT_PATH = Path("specs/003-data-ingest-module-spec/contracts/dvol_api_contract.json")


def load_contract_schema() -> dict[str, Any]:
    with CONTRACT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def example_payload() -> dict[str, Any]:
    return {
        "result": [
            {
                "date": "2023-08-30",
                "unix": "1693353600000",
                "symbol": "BTC",
                "open": "40.6",
                "high": "40.6",
                "low": "40.18",
                "close": "40.21",
            }
        ]
    }


def test_contract_schema_validates_example():
    doc = load_contract_schema()
    payload = example_payload()
    # Build a root schema that includes components so $ref inside response schema can resolve
    response_schema = (
        doc["paths"]["/v1/data/ohlc/deribit/volatility"]["get"]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]
    )
    full_schema = {"allOf": [response_schema], "components": doc.get("components", {})}
    validate(instance=payload, schema=full_schema)


@pytest.mark.parametrize("symbol", ["BTC", "ETH"])
def test_live_endpoint_matches_contract_when_token_available(symbol: str):
    load_dotenv(override=False)
    token = os.getenv("CDD_API_KEY") or os.getenv("CDD_API_TOKEN")
    if not token:
        pytest.skip("CDD_API_KEY not set; skipping live contract check")

    base_url = os.getenv("CDD_API_BASE_URL", "https://api.cryptodatadownload.com/v1").rstrip("/")
    url = f"{base_url}/data/ohlc/deribit/volatility"

    # Preferred auth via header per docs: Authorization: TOKEN <token>
    headers = {"Authorization": f"TOKEN {token}", "accept": "application/json"}
    params = {"symbol": symbol, "limit": 1, "return": "JSON"}

    r = requests.get(url, headers=headers, params=params, timeout=30)
    if r.status_code == 401:
        # Fallback to query param auth_token
        params["auth_token"] = token
        headers.pop("Authorization", None)
        r = requests.get(url, headers=headers, params=params, timeout=30)

    if r.status_code == 401:
        pytest.xfail("Unauthorized: verify CDD token and auth method")

    assert r.status_code == 200, f"Unexpected status {r.status_code}: {r.text[:200]}"

    data = r.json()
    assert isinstance(data, dict) and "result" in data and isinstance(data["result"], list)

    # Validate first item against schema
    schema = load_contract_schema()
    item_schema_ref = schema["components"]["schemas"]["DVOLItem"]
    if data["result"]:
        full_item_schema = {"allOf": [item_schema_ref], "components": schema.get("components", {})}
        validate(instance=data["result"][0], schema=full_item_schema)
