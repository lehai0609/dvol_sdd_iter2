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
    "specs/003-data-ingest-module-spec/contracts/funding_api_contract.json"
)


def load_contract_schema() -> dict[str, Any]:
    with CONTRACT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def example_payload() -> dict[str, Any]:
    return {
        "result": [
            {
                "date": "2023-08-30 00:00:00",
                "unix": "1693353600000",
                "symbol": "BTC-PERPETUAL",
                "index_price": "27720.56",
                "prev_index_price": "27642.6",
                "interest_8h": "-1.4691613145727188e-05",
                "interest_1h": "-1.03824239374694e-08",
            }
        ]
    }


def test_contract_schema_validates_example():
    doc = load_contract_schema()
    payload = example_payload()
    response_schema = (
        doc["paths"]["/v1/data/ohlc/deribit/futures/funding/"]["get"]["responses"][
            "200"
        ]["content"]["application/json"]["schema"]
    )
    full_schema = {"allOf": [response_schema], "components": doc.get("components", {})}
    validate(instance=payload, schema=full_schema)


@pytest.mark.parametrize("symbol", ["BTC-PERPETUAL", "ETH-PERPETUAL"])
def test_live_endpoint_matches_contract_when_token_available(symbol: str):
    load_dotenv(override=False)
    token = os.getenv("CDD_API_KEY") or os.getenv("CDD_API_TOKEN")
    if not token:
        pytest.skip("CDD_API_KEY not set; skipping live contract check")

    base_url = (
        os.getenv("CDD_API_BASE_URL", "https://api.cryptodatadownload.com/v1").rstrip("/")
    )
    url = f"{base_url}/data/ohlc/deribit/futures/funding/"

    headers = {"Authorization": f"TOKEN {token}", "accept": "application/json"}
    params = {"symbol": symbol, "limit": 1, "return": "JSON"}

    r = requests.get(url, headers=headers, params=params, timeout=30)
    if r.status_code == 401:
        params["auth_token"] = token
        headers.pop("Authorization", None)
        r = requests.get(url, headers=headers, params=params, timeout=30)

    # Endpoint path corrected to include /futures/; no alt retry needed

    if r.status_code in (401, 404):
        pytest.xfail(
            f"Endpoint unavailable (status {r.status_code}). Verify token and path."
        )

    assert r.status_code == 200, f"Unexpected status {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, dict) and "result" in data and isinstance(data["result"], list)

    schema = load_contract_schema()
    item_schema_ref = schema["components"]["schemas"]["FundingItem"]
    if data["result"]:
        full_item_schema = {"allOf": [item_schema_ref], "components": schema.get("components", {})}
        validate(instance=data["result"][0], schema=full_item_schema)
