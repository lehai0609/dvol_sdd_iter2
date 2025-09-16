"""Reproduce-run orchestrator and forecast record construction.

Provides a minimal walk-forward pipeline using synthetic data for tests,
and utilities to build forecast records aligned to the contract.
"""

from __future__ import annotations
from typing import Dict, Any
from pathlib import Path
import numpy as np
import pandas as pd

from .walkforward import run_walkforward
from .baselines import quantile_interval_confidence


def build_forecast_records(
    *,
    asset: str,
    preds_by_horizon: Dict[int, pd.DataFrame],
) -> pd.DataFrame:
    """Construct forecast records with direction and confidence.

    - forecast_dvol: q50
    - direction: sign of forecast_dvol in {up, flat, down}
    - confidence: from q10–q90 interval width normalization
    """
    records = []
    for h, df in preds_by_horizon.items():
        if df.empty:
            continue
        # Compute confidence once per horizon
        conf = quantile_interval_confidence(df, lower="q10", upper="q90")
        for (ts, row), c in zip(df.iterrows(), conf):
            q50 = float(row.get("q50", np.nan))
            if not np.isfinite(q50):
                continue
            direction = "flat"
            if q50 > 0:
                direction = "up"
            elif q50 < 0:
                direction = "down"
            records.append(
                {
                    "asset": asset.upper(),
                    "date": pd.to_datetime(ts).strftime("%Y-%m-%d"),
                    "horizon": f"{h}d",
                    "forecast_dvol": q50,
                    "direction": direction,
                    "confidence": float(c),
                }
            )
    return pd.DataFrame.from_records(records)


def replay_one_slice(
    *, asset: str, start: str, end: str, config: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Run a tiny synthetic walk-forward slice; return artifacts and metrics.

    Used by tests to validate the pipeline shape without external data.
    """
    cfg = dict(config or {})
    idx = pd.date_range(start, end, freq="D")
    n = len(idx)
    # Synthetic features and target
    rng = np.random.default_rng(0)
    X = pd.DataFrame({"f1": rng.normal(size=n), "f2": rng.normal(size=n)}, index=idx)
    y = 0.7 * X["f1"] - 0.2 * X["f2"] + rng.normal(scale=0.1, size=n)

    run_id = cfg.get("run_id", "mock")
    artifacts_dir = Path(cfg.get("artifacts_dir", f"artifacts/models/{run_id}"))

    preds_by_h = run_walkforward(
        X,
        y,
        horizons=cfg.get("horizons", (1, 7, 14)),
        initial=cfg.get("initial", 20),
        test_size=cfg.get("test_size", 5),
        step=cfg.get("step", 5),
        artifact_dir=str(artifacts_dir),
    )

    forecasts = build_forecast_records(asset=asset, preds_by_horizon=preds_by_h)
    # Simple placeholder metrics
    metrics = {"rows": int(forecasts.shape[0])}
    # Back-compat: expose a predictions Series (q50 for 1d horizon) if available
    pred_series = None
    h1 = preds_by_h.get(1)
    if h1 is not None and not h1.empty and "q50" in h1.columns:
        pred_series = h1["q50"].rename(f"pred_{asset}")
    return {
        "forecasts": forecasts,
        "metrics": metrics,
        "artifacts_dir": artifacts_dir,
        "predictions": pred_series if pred_series is not None else pd.Series(dtype=float),
    }
