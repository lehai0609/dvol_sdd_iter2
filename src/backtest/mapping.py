"""Mapping scores to positions and threshold calibration.

Adds helpers to calibrate per-horizon thresholds and map forecasts to stances.
"""

from __future__ import annotations
from typing import Dict, Iterable, Mapping

import numpy as np
import pandas as pd


def calibrate_thresholds(
    *,
    scores: pd.Series,
    returns: pd.Series,
    fee_bps: float,
    slippage_bps: float,
    grid: Iterable[float],
) -> float:
    """
    Choose a threshold on training data that maximizes a simple net edge proxy.

    The test expects a float threshold from the provided grid.
    """
    s = pd.Series(scores).reset_index(drop=True)
    r = pd.Series(returns).reset_index(drop=True)
    # Align length
    n = min(len(s), len(r))
    s = s.iloc[:n]
    r = r.iloc[:n]
    best_thr = None
    best_net = -np.inf
    cost_per_flip = (float(fee_bps) + float(slippage_bps)) / 10000.0
    for thr in grid:
        pos = map_scores_to_positions(s, threshold=float(thr))
        pos_prev = pos.shift(1).fillna(0.0)
        gross = (pos_prev * r).sum()
        flips = (pos != pos_prev).sum()
        net = float(gross) - float(flips) * cost_per_flip
        if net > best_net:
            best_net = net
            best_thr = float(thr)
    return float(best_thr if best_thr is not None else 0.0)


def map_scores_to_positions(scores: pd.Series, *, threshold: float) -> pd.Series:
    """
    Map continuous scores to discrete positions in {-1, 0, 1} using symmetric threshold.
    """
    s = pd.Series(scores)
    thr = float(threshold)
    pos = s.apply(lambda x: 1.0 if x > thr else (-1.0 if x < -thr else 0.0))
    return pos.astype(float)


def calibrate_per_horizon(
    *,
    scores_by_h: Mapping[int, pd.Series],
    returns_by_h: Mapping[int, pd.Series],
    fee_bps: float,
    slippage_bps: float,
    grid: Iterable[float],
) -> Dict[int, float]:
    """Calibrate a threshold per horizon using `calibrate_thresholds`.

    Returns a dict mapping horizon -> threshold.
    """
    out: Dict[int, float] = {}
    for h, s in scores_by_h.items():
        r = returns_by_h.get(h, pd.Series(index=s.index, dtype=float))
        thr = calibrate_thresholds(
            scores=s, returns=r, fee_bps=fee_bps, slippage_bps=slippage_bps, grid=grid
        )
        out[h] = float(thr)
    return out


def map_forecasts_to_stance(
    forecasts_df: pd.DataFrame, *, thresholds_by_horizon: Mapping[int, float]
) -> pd.DataFrame:
    """Map forecast records to discrete stances per horizon.

    Expects columns: horizon as '{1d,7d,14d}', forecast_dvol.
    Returns a copy with an added 'stance' column in {-1, 0, 1}.
    """
    df = forecasts_df.copy()
    def parse_h(s: str) -> int:
        try:
            return int(str(s).replace("d", "").strip())
        except Exception:
            return 0

    hs = df["horizon"].map(parse_h)
    thr_map = {int(k): float(v) for k, v in thresholds_by_horizon.items()}

    def stance_for_row(val: float, h: int) -> float:
        thr = thr_map.get(h, 0.0)
        if pd.isna(val):
            return 0.0
        return 1.0 if val > thr else (-1.0 if val < -thr else 0.0)

    df["stance"] = [stance_for_row(v, h) for v, h in zip(df["forecast_dvol"], hs)]
    return df
