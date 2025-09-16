"""Evaluation metrics (T050 tests).

Implementations to be completed later; current functions raise NotImplementedError to enforce TDD.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def rmse(y_true, y_pred) -> float:
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    mask = np.isfinite(yt) & np.isfinite(yp)
    if not np.any(mask):
        return float("nan")
    return float(np.sqrt(np.mean((yt[mask] - yp[mask]) ** 2)))


def mae(y_true, y_pred) -> float:
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    mask = np.isfinite(yt) & np.isfinite(yp)
    if not np.any(mask):
        return float("nan")
    return float(np.mean(np.abs(yt[mask] - yp[mask])))


def spearman(y_true, y_pred) -> float:
    # Rank-transform and compute Pearson correlation of ranks
    a = pd.Series(y_true).rank(method="average").to_numpy(dtype=float)
    b = pd.Series(y_pred).rank(method="average").to_numpy(dtype=float)
    mask = np.isfinite(a) & np.isfinite(b)
    if not np.any(mask):
        return float("nan")
    a = a[mask]
    b = b[mask]
    if a.size < 2:
        return float("nan")
    # Pearson corr
    a = a - a.mean()
    b = b - b.mean()
    denom = np.sqrt((a**2).sum()) * np.sqrt((b**2).sum())
    if denom == 0:
        return float("nan")
    return float((a @ b) / denom)


def hit_rate(y_true: pd.Series, y_pred: pd.Series, *, threshold: float = 0.0) -> float:
    """Directional hit-rate: fraction where sign(y_true - thr) == sign(y_pred - thr)."""
    yt = pd.Series(y_true).to_numpy(dtype=float)
    yp = pd.Series(y_pred).to_numpy(dtype=float)
    s_true = np.sign(yt - threshold)
    s_pred = np.sign(yp - threshold)
    mask = np.isfinite(s_true) & np.isfinite(s_pred)
    if not np.any(mask):
        return float("nan")
    return float(np.mean((s_true[mask]) == (s_pred[mask])))
