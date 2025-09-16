from __future__ import annotations

import argparse
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


START_PATH = Path(__file__).resolve()
REPO_ROOT = find_repo_root(START_PATH)
SRC_PATH = REPO_ROOT / "src"
if SRC_PATH.exists() and str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from dvol_data.policy import load_policy  # noqa: E402
from dvol_data.etl_options import (  # noqa: E402
    parse_options_json,
    normalize_options_df,
)
from dvol_data.storage import write_partition  # noqa: E402


pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 20)

CONTRACTS_DIR = REPO_ROOT / "specs" / "001-dvol-forecasting-volatility" / "contracts"
POLICY_PATH = CONTRACTS_DIR / "policy.cutoff.yaml"
RAW_DATA_ROOT = REPO_ROOT / "data"


def build_session() -> tuple[requests.Session, str, str]:
    """Configure CDD session and base URL like in notebooks/dvol_pipeline.py."""
    load_dotenv()
    raw_base = os.environ.get("CDD_API_BASE_URL", "https://api.cryptodatadownload.com/v1").strip()
    if raw_base.endswith("/"):
        raw_base = raw_base[:-1]
    if raw_base.lower().endswith("/v1"):
        api_version_prefix = "/v1"
        base_url = raw_base[:-3]
    else:
        api_version_prefix = ""
        base_url = raw_base
    if not base_url:
        base_url = "https://api.cryptodatadownload.com"
        api_version_prefix = "/v1"

    api_key = os.environ.get("CDD_API_KEY", "").strip()

    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    if api_key:
        session.headers["Authorization"] = f"TOKEN {api_key}"

    return session, base_url, api_version_prefix


def build_url(base_url: str, api_version_prefix: str, path: str) -> str:
    if path.startswith("http"):
        return path
    normalized = path if path.startswith("/") else f"/{path}"
    if normalized.lower().startswith("/v1"):
        return f"{base_url}{normalized}"
    return f"{base_url}{api_version_prefix}{normalized}"


def fetch_cdd_json(
    session: requests.Session,
    base_url: str,
    api_version_prefix: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = build_url(base_url, api_version_prefix, path)
    resp = session.get(url, params=params or {}, timeout=45)
    resp.raise_for_status()
    payload = resp.json()
    if not isinstance(payload, dict):
        raise TypeError(f"Expected mapping payload for {path}, got {type(payload)!r}")
    if "result" not in payload:
        raise KeyError(f"'result' key missing in payload for {path}")
    return payload


def persist_partitions(
    df: pd.DataFrame,
    *,
    table: str,
    layer: str = "raw",
    asset_col: str = "asset",
    date_col: str = "date",
) -> list[Path]:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch raw options summaries from CDD and persist partitions.")
    parser.add_argument("--asset", default="BTC", help="Underlying asset symbol (e.g., BTC, ETH)")
    parser.add_argument("--lookback-days", type=int, default=90, help="Lookback window in days")
    parser.add_argument("--end-date", default=date.today().isoformat(), help="End date ISO yyyy-mm-dd")
    parser.add_argument("--limit", type=int, default=None, help="API limit override; defaults to lookback+5")
    args = parser.parse_args()

    policy = load_policy(POLICY_PATH)
    asset = args.asset.upper()
    end_date = date.fromisoformat(args.end_date)
    lookback = args.lookback_days
    limit = args.limit if args.limit is not None else lookback + 5

    session, base_url, api_prefix = build_session()
    print(f"Using CDD base: {base_url}{api_prefix or ''}")
    print(f"Asset: {asset} | Range: {end_date - timedelta(days=lookback)} -> {end_date} | Limit: {limit}")

    payload = fetch_cdd_json(
        session,
        base_url,
        api_prefix,
        policy["allowed_sources"]["options_summaries"]["endpoint"],
        params={
            "underlying": asset,
            "enddate": end_date.isoformat(),
            "limit": limit,
            "return": "JSON",
        },
    )

    # Basic inspection of fetched JSON
    result = payload.get("result", [])
    print(f"Fetched JSON result rows: {len(result)}")
    if result:
        sample_keys = sorted(set().union(*[set(d.keys()) for d in result[:3] if isinstance(d, dict)]))
        print(f"Sample fields: {sample_keys}")

    # Normalize to contract
    raw_df = parse_options_json(payload)
    df = normalize_options_df(raw_df)
    df = df[df["asset"] == asset].sort_values(["date", "maturity"]).reset_index(drop=True)

    # Contract validation
    raw_options_schema = json.loads((CONTRACTS_DIR / "raw_options_summary.schema.json").read_text(encoding="utf-8"))
    for record in df.tail(10).to_dict("records"):
        jsonschema.validate(record, raw_options_schema)

    print(f"Options rows normalized: {len(df)}")

    # Partition accounting (by asset/date)
    if not df.empty:
        part_keys = df[["asset", "date"]].dropna().drop_duplicates()
        print(f"Planned partitions (asset/date): {len(part_keys)}")
    else:
        print("Planned partitions (asset/date): 0")

    # Persist partitions (Parquet) as before
    written = persist_partitions(df, table="raw_options_summary", layer="raw")
    print(f"Persisted partitions: {len(written)}")
    for p in written[-5:]:
        print(f" -> {p}")

    # Additionally, write a consolidated CSV with the full schema and the fetched JSON
    schema_cols = [
        "asset",
        "date",
        "maturity",
        "avg_iv",
        "usd_volume",
        "net_vega",
    ]
    for col in schema_cols:
        if col not in df.columns:
            df[col] = pd.NA
    df_out = df[schema_cols]

    out_dir = RAW_DATA_ROOT / "raw" / "raw_options_summary"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name_csv = f"raw_options_summary_{asset}_{end_date.isoformat()}.csv"
    out_path_csv = out_dir / out_name_csv
    df_out.to_csv(out_path_csv, index=False)
    print(f"Wrote CSV: {out_path_csv} ({len(df_out)} rows, {len(df_out.columns)} cols)")

    out_name_json = f"raw_options_summary_{asset}_{end_date.isoformat()}.json"
    out_path_json = out_dir / out_name_json
    with out_path_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Wrote JSON: {out_path_json}")


if __name__ == "__main__":
    main()
