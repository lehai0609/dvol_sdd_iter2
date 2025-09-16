import json
from pathlib import Path

import jsonschema
import pandas as pd

from dvol_data.etl_funding import daily_funding_from_intraday


SCHEMA_PATH = Path(
    "specs/001-dvol-forecasting-volatility/contracts/raw_funding.schema.json"
).resolve()


def load_schema():
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_daily_funding_matches_contract():
    schema = load_schema()
    raw = pd.DataFrame(
        [
            {
                "date": "2024-06-01 01:00:00",
                "symbol": "BTC-PERPETUAL",
                "interest_1h": 0.0001,
                "interest_8h": 0.0008,
                "index_price": 70000,
            },
            {
                "date": "2024-06-01 02:00:00",
                "symbol": "BTC-PERPETUAL",
                "interest_1h": 0.00015,
                "interest_8h": 0.0009,
                "index_price": 70200,
            },
        ]
    )

    daily = daily_funding_from_intraday(raw)
    assert len(daily) == 1
    row = daily.iloc[0].dropna().to_dict()
    jsonschema.validate(row, schema)

