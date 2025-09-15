"""
Fetch Deribit options greeks by maturities summary and print head.

Usage:
    poetry run python scripts/fetch_deribit_greeks_maturities.py --underlying BTC --limit 25

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
    p = argparse.ArgumentParser(description="Fetch Deribit greeks maturities summary and print head")
    p.add_argument(
        "--underlying",
        default="BTC",
        help="Option base underlying, BTC or ETH (default: BTC)",
    )
    p.add_argument("--limit", type=int, default=25, help="Max rows to return (<= 2500). Default: 25")
    return p


def main() -> None:
    load_dotenv()

    base_url = os.getenv("CDD_API_BASE_URL", "https://api.cryptodatadownload.com/v1").rstrip("/")
    token = os.getenv("CDD_API_KEY")
    if not token:
        raise SystemExit("CDD_API_KEY not found in environment/.env")

    args = build_parser().parse_args()

    endpoint = f"{base_url}/data/summary/deribit/options/greeks/maturities/"
    params = {"underlying": args.underlying, "limit": args.limit, "return": "JSON"}

    headers = {"Authorization": f"TOKEN {token}"}

    resp = requests.get(endpoint, params=params, headers=headers, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    result = data.get("result", data)
    df = pd.json_normalize(result)
    print(df.head())


if __name__ == "__main__":
    main()

