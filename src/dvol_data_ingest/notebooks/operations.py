"""
Operations helpers for Notebook Interface (T032).

These functions are intended to be called from the control_center notebook
to orchestrate fetching, validation, storage, monitoring, and troubleshooting.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from loguru import logger
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from dvol_data_ingest.clients.dvol import DVOLClient
from dvol_data_ingest.clients.funding import FundingClient
from dvol_data_ingest.clients.futures import FuturesClient
from dvol_data_ingest.clients.onchain import OnChainClient
from dvol_data_ingest.clients.options import OptionsClient
from dvol_data_ingest.models.api_responses import (
    DVOLApiResponse,
    FundingRatesApiResponse,
    FuturesOHLCVApiResponse,
    OnChainDataApiResponse,
    OptionsSummaryApiResponse,
)
from dvol_data_ingest.models.storage import (
    DVOLRecord,
    FundingRecord,
    OHLCVRecord,
    OnChainRecord,
    OptionsSummaryRecord,
)
from dvol_data_ingest.storage.state import IngestState
from dvol_data_ingest.utils.datetime import to_utc_date
from dvol_data_ingest.validators import quality as v_quality
from dvol_data_ingest.validators import schema as v_schema

console = Console()


@dataclass
class _Cache:
    raw: dict[str, list[Any]]
    records: list[Any]
    issues: list[v_schema.ValidationIssue]


_CACHE = _Cache(raw=defaultdict(list), records=[], issues=[])


def _normalize_dvol(items: list[DVOLApiResponse]) -> list[DVOLRecord]:
    recs: list[DVOLRecord] = []
    for x in items:
        recs.append(
            DVOLRecord(
                asset=x.symbol,
                date_utc=to_utc_date(x.date),
                unix_ms=x.unix,
                symbol=x.symbol,
                open=x.open,
                high=x.high,
                low=x.low,
                close=x.close,
            )
        )
    return recs


def _normalize_options(items: list[OptionsSummaryApiResponse]) -> list[OptionsSummaryRecord]:
    recs: list[OptionsSummaryRecord] = []
    for x in items:
        recs.append(
            OptionsSummaryRecord(
                asset=x.underlying,
                date_utc=to_utc_date(x.date),
                maturity_utc=to_utc_date(x.maturity),
                net_delta=x.net_delta,
                buy_delta=x.buy_delta,
                sell_delta=x.sell_delta,
                net_gamma=x.net_gamma,
                net_vega=x.net_vega,
                net_theta=x.net_theta,
                avg_iv=x.avg_iv,
                volume=int(x.volume),
                buy_volume=int(x.buy_volume),
                sell_volume=int(x.sell_volume),
                usd_volume=float(x.usd_volume),
            )
        )
    return recs


def _normalize_futures(items: list[FuturesOHLCVApiResponse]) -> list[OHLCVRecord]:
    recs: list[OHLCVRecord] = []
    for x in items:
        asset = "BTC" if x.symbol.startswith("BTC") else ("ETH" if x.symbol.startswith("ETH") else "BTC")
        recs.append(
            OHLCVRecord(
                asset=asset,
                symbol=x.symbol,
                date_utc=to_utc_date(x.date),
                unix_ms=x.unix,
                open=x.open,
                high=x.high,
                low=x.low,
                close=x.close,
                volume_base=float(x.volume),
                volume_usd=float(x.base_volume),
            )
        )
    return recs


def _normalize_funding(items: list[FundingRatesApiResponse]) -> list[FundingRecord]:
    # Aggregate by date_utc per symbol to compute daily stats
    by_day: dict[tuple[str, str], list[FundingRatesApiResponse]] = defaultdict(list)
    for x in items:
        asset = "BTC" if x.symbol.startswith("BTC") else ("ETH" if x.symbol.startswith("ETH") else "BTC")
        day = to_utc_date(x.date).isoformat()
        by_day[(asset, day)].append(x)

    recs: list[FundingRecord] = []
    for (asset, day), xs in by_day.items():
        rates = [float(t.interest_8h) for t in xs]
        if rates:
            mean = sum(rates) / float(len(rates))
            var = sum((r - mean) ** 2 for r in rates) / float(len(rates)) if len(rates) > 1 else 0.0
            std = var ** 0.5
        else:
            mean = 0.0
            std = 0.0
        # 5d change cannot be computed locally without history; set to 0.0 as placeholder
        recs.append(
            FundingRecord(
                asset=asset,
                symbol=xs[0].symbol,
                date_utc=to_utc_date(day),
                unix_ms=xs[0].unix,
                index_price=float(xs[0].index_price),
                prev_index_price=float(xs[0].prev_index_price),
                interest_8h=float(xs[0].interest_8h),
                interest_1h=float(xs[0].interest_1h),
                funding_mean=float(mean),
                funding_std=float(std),
                funding_5d_change=0.0,
            )
        )
    return recs


def _normalize_onchain(items: list[OnChainDataApiResponse]) -> list[OnChainRecord]:
    recs: list[OnChainRecord] = []
    for x in items:
        asset = x.symbol.upper()
        recs.append(
            OnChainRecord(
                asset=asset,  # BTC/ETH
                date_utc=to_utc_date(x.date),
                total_transactions=int(x.total_transactions),
                total_block_cnt=int(x.total_block_count),
                avg_secs_between_blocks=(float(x.avg_seconds_between_blocks) if x.avg_seconds_between_blocks is not None else 0.0),
                avg_block_size_mb=(float(x.avg_block_size) if x.avg_block_size is not None else 0.0),
                hashrate=(float(x.hashrate) if x.hashrate is not None else 0.0),
                avg_transactions_count_per_block=(
                    float(x.avg_transaction_count) if x.avg_transaction_count is not None else 0.0
                ),
                avg_gas_limit=None,
                total_gas_used_in_eth=None,
                block_utilization=None,
                complexity_score=None,
                first_block=int(x.first_block or 0),
                last_block=int(x.last_block or 0),
            )
        )
    return recs


def interactive_fetch(*, sources: Iterable[str] | None = None, assets: Iterable[str] | None = None) -> list[Any]:
    """Interactively fetch data for selected sources/assets.

    Parameters
    - sources: iterable of source identifiers ("dvol", "options", "futures", "funding", "onchain").
    - assets: iterable of asset symbols ("BTC", "ETH").

    Returns list of normalized storage records across selected sources.
    Also caches raw responses, issues, and normalized records for later cells.
    """
    srcs = [s.lower() for s in (list(sources) if sources else ["dvol"])]
    asx = [a.upper() for a in (list(assets) if assets else ["BTC"])]

    _CACHE.raw.clear()
    _CACHE.records.clear()
    _CACHE.issues.clear()

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        for src in srcs:
            for asset in asx:
                task = progress.add_task(f"{src}:{asset}", start=False)
                progress.start_task(task)
                try:
                    if src == "dvol":
                        with DVOLClient() as c:
                            items = c.fetch(symbol=asset, limit=200)
                        valid, issues = v_schema.validate_dvol([i.model_dump() for i in items])
                        _CACHE.raw[src].extend(valid)
                        _CACHE.issues.extend(issues)
                        _CACHE.records.extend(_normalize_dvol(valid))
                    elif src == "options":
                        with OptionsClient() as c:
                            items = c.fetch(underlying=asset)
                        valid, issues = v_schema.validate_options([i.model_dump() for i in items])
                        _CACHE.raw[src].extend(valid)
                        _CACHE.issues.extend(issues)
                        _CACHE.records.extend(_normalize_options(valid))
                    elif src == "futures":
                        symbol = f"{asset}-PERPETUAL"
                        with FuturesClient() as c:
                            items = c.fetch(symbol=symbol, limit=200)
                        valid, issues = v_schema.validate_futures([i.model_dump() for i in items])
                        _CACHE.raw[src].extend(valid)
                        _CACHE.issues.extend(issues)
                        _CACHE.records.extend(_normalize_futures(valid))
                    elif src == "funding":
                        symbol = f"{asset}-PERPETUAL"
                        with FundingClient() as c:
                            items = c.fetch(symbol=symbol, limit=200)
                        valid, issues = v_schema.validate_funding([i.model_dump() for i in items])
                        _CACHE.raw[src].extend(valid)
                        _CACHE.issues.extend(issues)
                        _CACHE.records.extend(_normalize_funding(valid))
                    elif src == "onchain":
                        with OnChainClient() as c:
                            items = c.fetch(symbol=asset.lower())
                        valid, issues = v_schema.validate_onchain([i.model_dump() for i in items])
                        _CACHE.raw[src].extend(valid)
                        _CACHE.issues.extend(issues)
                        _CACHE.records.extend(_normalize_onchain(valid))
                    else:
                        logger.warning(f"Unknown source: {src}")
                except Exception as e:  # noqa: BLE001
                    logger.error(f"fetch failed for {src}:{asset}: {e}")
                finally:
                    progress.update(task, advance=1, completed=1)

    console.print({"fetched_records": len(_CACHE.records), "issues": len(_CACHE.issues)})
    return _CACHE.records


def validate_data(*, strict: bool = True) -> dict[str, Any]:
    """Run schema and quality validation on latest fetched raw data.

    Returns a dict summary with counts and basic quality metrics.
    If strict and any schema issues exist, raises ValueError.
    """
    issues = _CACHE.issues
    if strict and issues:
        # Show a brief sample
        sample = [
            {"index": i.index, "message": i.message} for i in issues[:5]
        ]
        raise ValueError(f"Schema validation issues: {len(issues)} (sample: {sample})")

    # Basic quality checks over normalized records where available
    recs = _CACHE.records
    completeness = v_quality.completeness_ratio(recs, ["asset", "date_utc"])
    dates = [getattr(r, "date_utc", None) for r in recs]
    contiguous = v_quality.is_daily_contiguous([d for d in dates if d is not None])

    summary = {
        "schema_issues": len(issues),
        "records": len(recs),
        "completeness": round(completeness, 3),
        "daily_contiguous": contiguous,
    }
    console.print({"validation": summary})
    return summary


def run_backfill(*, start: str | None = None, end: str | None = None, sources: Iterable[str] | None = None, assets: Iterable[str] | None = None) -> list[Any]:
    """Execute backfill operations for given time window (UTC ISO-8601).

    Falls back to incremental window derived from persisted state when
    start/end are not provided.
    """
    srcs = [s.lower() for s in (list(sources) if sources else ["dvol"])]
    asx = [a.upper() for a in (list(assets) if assets else ["BTC"]) ]

    state = IngestState()

    # Determine window per asset if not provided
    windows: dict[tuple[str, str], tuple[str | None, str | None]] = {}
    for src in srcs:
        for asset in asx:
            if start or end:
                windows[(src, asset)] = (start, end)
            else:
                params = state.next_fetch_params(src, asset, default_days=14)
                windows[(src, asset)] = (params.get("start"), params.get("end"))

    with Progress(
        SpinnerColumn(), TextColumn("[bold green]backfill {task.description}"), BarColumn(), TimeElapsedColumn(), console=console
    ) as progress:
        for (src, asset), (s, e) in windows.items():
            task = progress.add_task(f"{src}:{asset}", start=False)
            progress.start_task(task)
            try:
                if src == "futures":
                    symbol = f"{asset}-PERPETUAL"
                    with FuturesClient() as c:
                        items = c.fetch(symbol=symbol, start=s, end=e)
                    valid, issues = v_schema.validate_futures([i.model_dump() for i in items])
                    _CACHE.raw[src].extend(valid)
                    _CACHE.issues.extend(issues)
                    _CACHE.records.extend(_normalize_futures(valid))
                elif src == "funding":
                    symbol = f"{asset}-PERPETUAL"
                    with FundingClient() as c:
                        items = c.fetch(symbol=symbol, start=s, end=e)
                    valid, issues = v_schema.validate_funding([i.model_dump() for i in items])
                    _CACHE.raw[src].extend(valid)
                    _CACHE.issues.extend(issues)
                    _CACHE.records.extend(_normalize_funding(valid))
                elif src == "dvol":
                    with DVOLClient() as c:
                        # DVOL endpoint supports enddate/limit; approximate window via limit
                        items = c.fetch(symbol=asset, enddate=e, limit=500)
                    valid, issues = v_schema.validate_dvol([i.model_dump() for i in items])
                    _CACHE.raw[src].extend(valid)
                    _CACHE.issues.extend(issues)
                    _CACHE.records.extend(_normalize_dvol(valid))
                elif src == "options":
                    with OptionsClient() as c:
                        items = c.fetch(underlying=asset, date=s or e)
                    valid, issues = v_schema.validate_options([i.model_dump() for i in items])
                    _CACHE.raw[src].extend(valid)
                    _CACHE.issues.extend(issues)
                    _CACHE.records.extend(_normalize_options(valid))
                elif src == "onchain":
                    with OnChainClient() as c:
                        items = c.fetch(symbol=asset.lower(), date=s or e)
                    valid, issues = v_schema.validate_onchain([i.model_dump() for i in items])
                    _CACHE.raw[src].extend(valid)
                    _CACHE.issues.extend(issues)
                    _CACHE.records.extend(_normalize_onchain(valid))
                else:
                    logger.warning(f"Unknown source: {src}")
                # Update state best-effort
                if e:
                    state.update(src, asset, last_date=(e.split("T")[0] if "T" in e else e))
            except Exception as exc:  # noqa: BLE001
                logger.error(f"backfill failed for {src}:{asset}: {exc}")
            finally:
                progress.update(task, advance=1, completed=1)

    console.print({"backfill_records": len(_CACHE.records), "issues": len(_CACHE.issues)})
    return _CACHE.records


def show_status() -> dict[str, Any]:
    """Return a status snapshot for the pipeline (state, cache, files)."""
    state = IngestState()
    ok = state.validate()
    data_dir = Path("./data")
    parquet_files = list(data_dir.glob("**/*.parquet")) if data_dir.exists() else []
    status = {
        "state_valid": ok,
        "cached_raw_sources": {k: len(v) for k, v in _CACHE.raw.items()},
        "cached_records": len(_CACHE.records),
        "schema_issues": len(_CACHE.issues),
        "parquet_files": len(parquet_files),
    }
    return status


def display_metrics() -> None:
    """Render basic metrics/plots suitable for notebook visualization.

    Plots a simple DVOL close series per asset if present in cache.
    """
    # Extract DVOL from cached records
    dvol = [r for r in _CACHE.records if isinstance(r, DVOLRecord)]
    if not dvol:
        console.print("[yellow]No DVOL records in cache; run interactive_fetch(['dvol'], ...)[/yellow]")
        return

    by_asset: dict[str, list[DVOLRecord]] = defaultdict(list)
    for r in dvol:
        by_asset[r.asset].append(r)
    for a in by_asset:
        by_asset[a].sort(key=lambda r: r.date_utc)

    plt.figure(figsize=(9, 4))
    for asset, rs in by_asset.items():
        xs = [r.date_utc for r in rs]
        ys = [r.close for r in rs]
        plt.plot(xs, ys, label=f"DVOL {asset}")
    plt.title("DVOL Close by Asset")
    plt.xlabel("Date (UTC)")
    plt.ylabel("Close")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def troubleshoot_pipeline(*, verbose: bool = False) -> None:
    """Run common diagnostics and print actionable hints."""
    hints: list[str] = []

    # 1) Env variables for API
    import os

    for k in ("CDD_API_KEY", "CDD_API_BASE_URL"):
        v = os.getenv(k)
        hints.append(f"env {k}: {'SET' if v else 'MISSING'}")

    # 2) State file validity
    st = IngestState()
    hints.append(f"state valid: {st.validate()}")

    # 3) Can import core libs
    try:
        import pyarrow  # noqa: F401
        hints.append("pyarrow: OK")
    except Exception as e:  # noqa: BLE001
        hints.append(f"pyarrow: MISSING ({e})")

    # 4) Data dir writability
    try:
        p = Path("./data/.probe")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("ok", encoding="utf-8")
        p.unlink(missing_ok=True)
        hints.append("data dir writable: True")
    except Exception as e:  # noqa: BLE001
        hints.append(f"data dir writable: False ({e})")

    # 5) Optional: simple connectivity probe (HEAD)
    try:
        with DVOLClient() as c:
            # use .request for a lightweight probe
            resp = c.request("GET", "/health", params={"ping": "1"})
            hints.append(f"api probe: {resp.status_code}")
    except Exception as e:  # noqa: BLE001
        hints.append(f"api probe failed: {e}")

    if verbose:
        for h in hints:
            console.print(f"- {h}")
    else:
        console.print({"diagnostics": hints})

