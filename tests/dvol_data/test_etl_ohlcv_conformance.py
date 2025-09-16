import json
from pathlib import Path

import jsonschema
import pandas as pd

from dvol_data.etl_ohlcv import normalize_ohlcv_df


SCHEMA_PATH = Path(
    "specs/001-dvol-forecasting-volatility/contracts/raw_ohlcv.schema.json"
).resolve()


def load_schema():
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_normalize_ohlcv_matches_contract():
    schema = load_schema()
    raw = pd.DataFrame(
        [
            {
                "date": "2024-06-01 00:00:00",
                "unix": "1717200000000",
                "symbol": "BTC-PERPETUAL",
                "open": "70000",
                "high": "70500",
                "low": "69000",
                "close": "69500",
                "base_volume": "500.0",
                "quote_volume": "34750000.0",
            }
        ]
    )

    norm = normalize_ohlcv_df(raw)
    row = norm.iloc[0].dropna().to_dict()
    # Ensure mapping base->volume and quote->volume_usd took place
    assert row["volume"] == 500.0
    assert row["volume_usd"] == 34_750_000.0
    jsonschema.validate(row, schema)

