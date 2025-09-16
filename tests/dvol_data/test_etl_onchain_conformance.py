import json
from pathlib import Path

import jsonschema
import pandas as pd

from dvol_data.etl_onchain import normalize_onchain_daily


SCHEMA_PATH = Path(
    "specs/001-dvol-forecasting-volatility/contracts/raw_onchain.schema.json"
).resolve()


def load_schema():
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_normalize_onchain_matches_contract_and_lag():
    schema = load_schema()
    raw = pd.DataFrame(
        [
            {
                "asset": "BTC",
                "date": "2024-06-01",
                "total_transactions": 100_000,
                "total_block_cnt": 100,
            },
            {
                "asset": "BTC",
                "date": "2024-06-02",
                "total_transactions": 110_000,
                "total_block_cnt": 101,
            },
        ]
    )

    norm = normalize_onchain_daily(raw)
    # After t-1 shift, first day dropped -> one row remains
    assert len(norm) == 1
    row = norm.iloc[0].dropna().to_dict()
    jsonschema.validate(row, schema)

