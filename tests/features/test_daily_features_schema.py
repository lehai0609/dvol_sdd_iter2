import json
from pathlib import Path

import jsonschema
import numpy as np
import pandas as pd

from features.build import build_daily_features


SCHEMA_PATH = Path(
    "specs/001-dvol-forecasting-volatility/contracts/daily_features.schema.json"
).resolve()


def load_schema():
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_build_daily_features_matches_schema_minimal():
    schema = load_schema()
    dates = pd.date_range("2024-06-01", periods=7, freq="D")
    df = pd.DataFrame(
        {
            "asset": ["ETH"] * len(dates),
            "date": dates,
            "dvol_close": [40, 42, 41, 43, 44, 45, 46],
            "high": [41, 43, 42, 44, 45, 46, 47],
            "low": [39, 41, 40, 42, 43, 44, 45],
            "price_close": [1000, 1005, 1010, 1008, 1012, 1015, 1017],
            "options_net_vega": [np.nan, 10, 12, 11, 15, 13, 16],
            "options_usd_volume": [np.nan, 1_000_000, 1_200_000, 800_000, 1_500_000, 900_000, 2_000_000],
            "interest_8h": [np.nan, 0.0005, 0.0006, 0.0004, 0.0007, 0.0003, 0.0002],
            "total_transactions": [100_000, 105_000, 103_000, 108_000, 110_000, 109_000, 111_000],
            "onchain_is_imputed": [False] * len(dates),
        }
    )

    feats = build_daily_features(df)
    # Validate first non-null rows against schema
    for i in range(2, len(feats)):
        row = feats.iloc[i].dropna().to_dict()
        jsonschema.validate(row, schema)
        break

