import json
from pathlib import Path

import jsonschema
import pandas as pd

from dvol_data.etl_options import normalize_options_df


SCHEMA_PATH = Path(
    "specs/001-dvol-forecasting-volatility/contracts/raw_options_summary.schema.json"
).resolve()


def load_schema():
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_normalize_options_matches_contract():
    schema = load_schema()
    raw = pd.DataFrame(
        [
            {
                "date": "2024-06-01",
                "maturity": "2024-06-28",
                "underlying": "ETH",
                "avg_iv": 0.5,
                "usd_volume": 2_000_000.0,
                "net_vega": 12345.6,
            }
        ]
    )

    norm = normalize_options_df(raw)
    row = norm.iloc[0].dropna().to_dict()
    jsonschema.validate(row, schema)

