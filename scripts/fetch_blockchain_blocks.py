"""
Fetch blockchain summary blocks data and print head.

Usage:
    poetry run python scripts/fetch_blockchain_blocks.py --symbol btc --limit 25

Notes:
    - Reads `CDD_API_BASE_URL` and `CDD_API_KEY` from .env
    - Auth via header: Authorization: TOKEN <key>
    - Always requests JSON and prints a pandas head()
"""

import argparse
import os

import pandas as pd
import requests
from dotenv import load_dotenv


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Fetch blockchain blocks summary and print head")
    p.add_argument(
        "--symbol",
        default="btc",
        help="Blockchain symbol: btc or eth (default: btc)",
    )
    p.add_argument("--limit", type=int, default=25, help="Max rows to return (<= 2500). Default: 25")
    p.add_argument("--enddate", default=None, help="Most recent date YYYY-MM-DD (optional)")
    return p


def main() -> None:
    load_dotenv()

    base_url = os.getenv("CDD_API_BASE_URL", "https://api.cryptodatadownload.com/v1").rstrip("/")
    token = os.getenv("CDD_API_KEY")
    if not token:
        raise SystemExit("CDD_API_KEY not found in environment/.env")

    args = build_parser().parse_args()

    endpoint = f"{base_url}/data/summary/blockchain/blocks/"
    params = {"symbol": args.symbol, "limit": args.limit, "return": "JSON"}
    if args.enddate:
        params["enddate"] = args.enddate

    headers = {"Authorization": f"TOKEN {token}"}

    resp = requests.get(endpoint, params=params, headers=headers, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    result = data.get("result", data)
    df = pd.json_normalize(result)
    print(df.head())


if __name__ == "__main__":
    main()

