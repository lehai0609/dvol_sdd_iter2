import json
from pathlib import Path

import jsonschema
import pandas as pd

from dvol_data.etl_dvol import normalize_dvol_df, write_raw_dvol


SCHEMA_PATH = Path(
    "specs/001-dvol-forecasting-volatility/contracts/raw_dvol.schema.json"
).resolve()


def load_schema():
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_normalize_dvol_matches_contract_and_write(tmp_path: Path):
    schema = load_schema()
    raw = pd.DataFrame(
        [
            {
                "date": "2024-06-01",
                "unix": "1717200000000",  # ms
                "symbol": "BTC",
                "open": "45.1",
                "high": "46.2",
                "low": "44.8",
                "close": "45.7",
            }
        ]
    )

    norm = normalize_dvol_df(raw)
    row = norm.iloc[0].dropna().to_dict()
    jsonschema.validate(row, schema)

    # Write partition using helper
    p = write_raw_dvol(norm, asset="BTC", date="2024-06-01", root=tmp_path)
    assert p.exists()
    assert p.parent.name == "date=2024-06-01"
    assert p.parent.parent.name == "asset=BTC"

