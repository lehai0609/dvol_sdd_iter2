# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.3
#   kernelspec:
#     display_name: dvol-sdd-iter2-py3.11
#     language: python
#     name: python3
# ---

# %% [markdown]
# # DVOL Pipeline Orchestrator
#
# Control notebook to run the DVOL research pipeline end-to-end using in-repo modules.
# This version fetches raw datasets directly from CryptoDataDownload (CDD) to populate
# the daily DVOL, futures, options, funding, and on-chain tables defined in the data model.

# %%
from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import jsonschema
import pandas as pd
import requests
from dotenv import load_dotenv

def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return start


START_PATH = Path(__file__).resolve() if "__file__" in globals() else Path.cwd()
REPO_ROOT = find_repo_root(START_PATH)
SRC_PATH = REPO_ROOT / "src"
if SRC_PATH.exists() and str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from dvol_data.policy import load_policy
from dvol_data.etl_dvol import parse_dvol_json, normalize_dvol_df
from dvol_data.etl_ohlcv import parse_ohlcv_json, normalize_ohlcv_df
from dvol_data.etl_options import parse_options_json, normalize_options_df
from dvol_data.etl_funding import daily_funding_from_intraday
from dvol_data.etl_onchain import normalize_onchain_daily
from dvol_data.storage import write_partition
from features.build import build_daily_features
from models.walkforward import run_walkforward

pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 20)

CONTRACTS_DIR = REPO_ROOT / "specs" / "001-dvol-forecasting-volatility" / "contracts"
POLICY_PATH = CONTRACTS_DIR / "policy.cutoff.yaml"

RAW_DATA_ROOT = REPO_ROOT / "data"


def persist_partitions(
    df: pd.DataFrame,
    *,
    table: str,
    layer: str = "raw",
    asset_col: str = "asset",
    date_col: str = "date",
) -> list[Path]:
    """Write partitions grouped by asset/date using shared storage layout."""
    if df.empty:
        print(f"No rows to write for {table} ({layer})")
        return []
    written: list[Path] = []
    grouped = df.groupby([asset_col, date_col], dropna=False, sort=False)
    for (asset_value, date_value), part in grouped:
        if asset_value in (None, "") or date_value in (None, ""):
            continue
        asset_str = str(asset_value).upper()
        date_ts = pd.to_datetime(date_value, errors="coerce")
        if pd.isna(date_ts):
            continue
        date_str = date_ts.strftime("%Y-%m-%d")
        path = write_partition(
            part,
            layer=layer,
            table=table,
            asset=asset_str,
            date=date_str,
            root=RAW_DATA_ROOT,
        )
        written.append(path)
    print(f"Wrote {len(written)} partitions for {table} ({layer})")
    return written

# %% [markdown]
# ## Configure CDD Session

# %%
load_dotenv()

raw_base = os.environ.get("CDD_API_BASE_URL", "https://api.cryptodatadownload.com/v1").strip()
if raw_base.endswith("/"):
    raw_base = raw_base[:-1]
if raw_base.lower().endswith("/v1"):
    API_VERSION_PREFIX = "/v1"
    BASE_URL = raw_base[:-3]
else:
    API_VERSION_PREFIX = ""
    BASE_URL = raw_base
if not BASE_URL:
    BASE_URL = "https://api.cryptodatadownload.com"
    API_VERSION_PREFIX = "/v1"
API_KEY = os.environ.get("CDD_API_KEY", "").strip()

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json"})
if API_KEY:
    SESSION.headers["Authorization"] = f"TOKEN {API_KEY}"


def build_url(path: str) -> str:
    if path.startswith("http"):
        return path
    normalized = path if path.startswith("/") else f"/{path}"
    if normalized.lower().startswith("/v1"):
        return f"{BASE_URL}{normalized}"
    return f"{BASE_URL}{API_VERSION_PREFIX}{normalized}"


def fetch_cdd_json(path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = build_url(path)
    response = SESSION.get(url, params=params or {}, timeout=45)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise TypeError(f"Expected mapping payload for {path}, got {type(payload)!r}")
    if "result" not in payload:
        raise KeyError(f"'result' key missing in payload for {path}")
    return payload

print(f"Using CDD base: {BASE_URL}{API_VERSION_PREFIX or ''}")

# %% [markdown]
# ## Run Parameters

# %%
policy = load_policy(POLICY_PATH)
ASSET = "BTC"
LOOKBACK_DAYS = 90
END_DATE = date.today()
START_DATE = END_DATE - timedelta(days=LOOKBACK_DAYS)
LIMIT = LOOKBACK_DAYS + 5

FUTURES_SYMBOL = f"{ASSET}-PERPETUAL"
ONCHAIN_SYMBOL = ASSET.lower()

print(f"Asset: {ASSET} | Range: {START_DATE} -> {END_DATE} | Limit: {LIMIT}")

# %% [markdown]
# ## DVOL OHLC

# %%
dvol_payload = fetch_cdd_json(
    policy["allowed_sources"]["dvol_ohlc"]["endpoint"],
    params={
        "symbol": ASSET,
        "enddate": END_DATE.isoformat(),
        "limit": LIMIT,
        "return": "JSON",
    },
)
dvol_raw = parse_dvol_json(dvol_payload)
dvol_df = normalize_dvol_df(dvol_raw).dropna(subset=["asset", "date", "close"])
dvol_df = dvol_df.sort_values("date").reset_index(drop=True)
dvol_df = dvol_df[dvol_df["asset"].astype(str).str.upper() == ASSET].reset_index(drop=True)

raw_dvol_schema = json.loads((CONTRACTS_DIR / "raw_dvol.schema.json").read_text(encoding="utf-8"))
for record in dvol_df.tail(10).to_dict("records"):
    jsonschema.validate(record, raw_dvol_schema)

print(f"DVOL rows fetched: {len(dvol_df)}")
dvol_df.tail()

# %% [markdown]
# ## Futures OHLCV

# %%
futures_payload = fetch_cdd_json(
    policy["allowed_sources"]["futures_ohlcv"]["endpoint"],
    params={
        "symbol": FUTURES_SYMBOL,
        "enddate": END_DATE.isoformat(),
        "limit": LIMIT,
        "return": "JSON",
    },
)
futures_raw = parse_ohlcv_json(futures_payload)
futures_df = normalize_ohlcv_df(futures_raw)
futures_df = futures_df[futures_df["asset"] == ASSET].sort_values("date").reset_index(drop=True)

raw_ohlcv_schema = json.loads((CONTRACTS_DIR / "raw_ohlcv.schema.json").read_text(encoding="utf-8"))
for record in futures_df.tail(10).to_dict("records"):
    jsonschema.validate(record, raw_ohlcv_schema)

print(f"Futures rows fetched: {len(futures_df)}")
futures_df.tail()

# %% [markdown]
# ## Options Summaries

# %%
options_payload = fetch_cdd_json(
    policy["allowed_sources"]["options_summaries"]["endpoint"],
    params={
        "underlying": ASSET,
        "enddate": END_DATE.isoformat(),
        "limit": LIMIT,
        "return": "JSON",
    },
)
options_raw = parse_options_json(options_payload)
options_df = normalize_options_df(options_raw)
options_df = options_df[options_df["asset"] == ASSET].sort_values(["date", "maturity"]).reset_index(drop=True)

raw_options_schema = json.loads((CONTRACTS_DIR / "raw_options_summary.schema.json").read_text(encoding="utf-8"))
for record in options_df.tail(10).to_dict("records"):
    jsonschema.validate(record, raw_options_schema)

print(f"Options rows fetched: {len(options_df)}")
options_df.tail()

# %% [markdown]
# ## Funding Rates (Daily Aggregation)

# %%
funding_payload = fetch_cdd_json(
    policy["allowed_sources"]["funding"]["endpoint"],
    params={
        "symbol": FUTURES_SYMBOL,
        "enddate": END_DATE.isoformat(),
        "limit": LIMIT,
        "return": "JSON",
    },
)
funding_raw = pd.DataFrame(funding_payload.get("result", []))
if funding_raw.empty:
    funding_df = pd.DataFrame(columns=["asset", "date", "symbol", "interest_8h", "interest_1h", "index_price"])
else:
    funding_df = daily_funding_from_intraday(funding_raw)
    funding_df = funding_df.sort_values("date").reset_index(drop=True)
    funding_df = funding_df[funding_df["asset"].astype(str).str.upper() == ASSET].reset_index(drop=True)

raw_funding_schema = json.loads((CONTRACTS_DIR / "raw_funding.schema.json").read_text(encoding="utf-8"))
for record in funding_df.tail(10).to_dict("records"):
    jsonschema.validate(record, raw_funding_schema)

print(f"Funding rows fetched: {len(funding_df)}")
funding_df.tail()

# %% [markdown]
# ## On-chain Metrics

# %%
onchain_payload = fetch_cdd_json(
    policy["allowed_sources"]["onchain"]["endpoint"],
    params={
        "symbol": ONCHAIN_SYMBOL,
        "enddate": END_DATE.isoformat(),
        "limit": LIMIT,
        "return": "JSON",
    },
)
onchain_raw = pd.DataFrame(onchain_payload.get("result", []))
if onchain_raw.empty:
    onchain_df = pd.DataFrame(
        columns=[
            "asset",
            "date",
            "total_transactions",
            "total_block_cnt",
            "avg_secs_between_blocks",
            "avg_block_size_mb",
            "avg_transactions_count_per_block",
            "base_gas_fee_sum_in_eth",
            "block_utilization",
            "onchain_is_imputed",
        ]
    )
else:
    rename_map = {
        "avg_block_size_MB": "avg_block_size_mb",
        "avg_gas_in_ETH_used_per_block": "base_gas_fee_sum_in_eth",
        "avg_gas_in_eth_used_per_block": "base_gas_fee_sum_in_eth",
    }
    onchain_work = onchain_raw.rename(columns=rename_map).copy()
    onchain_work["asset"] = ASSET
    for col in [
        "total_transactions",
        "total_block_cnt",
        "avg_secs_between_blocks",
        "avg_block_size_mb",
        "avg_transactions_count_per_block",
        "base_gas_fee_sum_in_eth",
        "block_utilization",
    ]:
        if col not in onchain_work.columns:
            onchain_work[col] = pd.NA
    onchain_df = normalize_onchain_daily(onchain_work)
    onchain_df = onchain_df[onchain_df["asset"].astype(str).str.upper() == ASSET].reset_index(drop=True)

raw_onchain_schema = json.loads((CONTRACTS_DIR / "raw_onchain.schema.json").read_text(encoding="utf-8"))
for record in onchain_df.tail(10).to_dict("records"):
    jsonschema.validate(record, raw_onchain_schema)

print(f"On-chain rows fetched: {len(onchain_df)}")
onchain_df.tail()

# %% [markdown]
# ## Persist Raw Tables

# %%
raw_tables = {
    "raw_dvol": dvol_df,
    "raw_ohlcv": futures_df,
    "raw_options_summary": options_df,
    "raw_funding": funding_df,
    "raw_onchain": onchain_df,
}
for table_name, frame in raw_tables.items():
    persist_partitions(frame, table=table_name, layer="raw")

# %% [markdown]
# ## Build Daily Features

# %%
dvol_daily = dvol_df.rename(columns={"close": "dvol_close"})[["asset", "date", "dvol_close", "high", "low"]].copy()
futures_daily = futures_df.rename(columns={"close": "price_close"})[["asset", "date", "price_close"]].copy()
options_daily = (
    options_df.groupby(["asset", "date"], dropna=False)[["usd_volume", "net_vega"]]
    .sum(min_count=1)
    .rename(columns={"usd_volume": "options_usd_volume", "net_vega": "options_net_vega"})
    .reset_index()
)
if "avg_iv" in options_df.columns:
    options_iv = (
        options_df.groupby(["asset", "date"], dropna=False)["avg_iv"]
        .mean()
        .rename("options_avg_iv")
        .reset_index()
    )
    options_daily = options_daily.merge(options_iv, on=["asset", "date"], how="left")
options_daily["options_availability_flag"] = (
    options_daily["options_usd_volume"].fillna(0) > 0
)

funding_daily = (
    funding_df.groupby(["asset", "date"], dropna=False)[["interest_8h", "interest_1h"]]
    .mean()
    .reset_index()
)
if "index_price" in funding_df.columns:
    funding_index = (
        funding_df.groupby(["asset", "date"], dropna=False)["index_price"]
        .mean()
        .rename("index_price")
        .reset_index()
    )
    funding_daily = funding_daily.merge(funding_index, on=["asset", "date"], how="left")

onchain_columns = [
    c
    for c in ["asset", "date", "total_transactions", "onchain_is_imputed"]
    if c in onchain_df.columns
]
onchain_daily = onchain_df[onchain_columns].copy()

daily_inputs = dvol_daily.merge(futures_daily, on=["asset", "date"], how="left")
daily_inputs = daily_inputs.merge(options_daily, on=["asset", "date"], how="left")
daily_inputs = daily_inputs.merge(funding_daily, on=["asset", "date"], how="left")
daily_inputs = daily_inputs.merge(onchain_daily, on=["asset", "date"], how="left")
daily_inputs = daily_inputs.sort_values("date").reset_index(drop=True)

print(f"Daily input rows: {len(daily_inputs)}")
daily_inputs.tail()

features_df = build_daily_features(daily_inputs)
features_df = features_df[features_df["asset"].astype(str).str.upper() == ASSET].copy()
features_df = features_df.dropna(subset=["date"])
features_df = features_df.sort_values("date").reset_index(drop=True)

print(f"Daily features rows: {len(features_df)}")
features_df.tail()

persist_partitions(features_df, table="daily_features", layer="features")

# %% [markdown]
# ## Run Walk-forward Modeling

# %%
initial_window = 30
test_window = 5
step_size = 5

feature_cols = [c for c in features_df.columns if c not in {"asset", "date"}]
features_base = (
    features_df.assign(date_dt=pd.to_datetime(features_df["date"], errors="coerce"))
    .dropna(subset=["date_dt"])
    .set_index("date_dt")
)
feature_matrix = features_base[feature_cols].copy()
bool_like = ["onchain_is_imputed", "options_availability_flag"]
for col in bool_like:
    if col in feature_matrix.columns:
        series = features_base[col].astype("boolean").fillna(False)
        feature_matrix[col] = series.astype(int)
feature_matrix = feature_matrix.apply(pd.to_numeric, errors="coerce")
required_rows = initial_window + test_window
feature_matrix = feature_matrix.dropna(axis=1, how="all")
feature_matrix = feature_matrix.dropna(axis=1, thresh=required_rows)
dropped = sorted(set(feature_cols) - set(feature_matrix.columns))
if dropped:
    print(f"Dropped low coverage features before modeling: {dropped}")

targets = (
    daily_inputs.assign(date_dt=pd.to_datetime(daily_inputs["date"], errors="coerce"))
    .dropna(subset=["date_dt"])
    .set_index("date_dt")["dvol_close"]
    .astype(float)
)

aligned = feature_matrix.join(targets.rename("target")).dropna()
if len(aligned) >= required_rows:
    X_model = aligned.drop(columns=["target"])
    y_model = aligned["target"]
    artifact_dir = REPO_ROOT / "data" / "models" / f"walkforward_{ASSET.lower()}"
    preds = run_walkforward(
        X_model,
        y_model,
        horizons=(1, 7, 14),
        initial=initial_window,
        test_size=test_window,
        step=step_size,
        artifact_dir=str(artifact_dir),
    )
    for horizon, df_pred in preds.items():
        print(f"H{horizon} predictions saved: {len(df_pred)} rows -> {artifact_dir}")
else:
    print(
        f"Insufficient coverage for walk-forward run: have {len(aligned)} rows, need {required_rows}."
    )
aligned.tail()
