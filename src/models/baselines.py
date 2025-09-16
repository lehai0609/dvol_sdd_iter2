"""Baseline model placeholders and uncertainty helpers.

T030/T032 tests import these names; implementations arrive in T077.
"""

from __future__ import annotations
from typing import Iterable, List, Sequence

import numpy as np
import pandas as pd


class NaiveLastValue:
    def __init__(self, target_lag_col: str = "y_lag1") -> None:
        self.target_lag_col = target_lag_col

    def fit(self, X: pd.DataFrame, y: Sequence[float] | pd.Series) -> "NaiveLastValue":
        # Intentionally minimal; real logic added in T077
        if self.target_lag_col not in X.columns:
            raise NotImplementedError("NaiveLastValue requires a lag column in X")
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        # Return the lag value as a naive forecast (acceptable minimal behavior)
        if self.target_lag_col not in X.columns:
            raise NotImplementedError("NaiveLastValue requires a lag column in X")
        return X[self.target_lag_col].to_numpy()


class HARModel:
    def __init__(self, feature_cols: Iterable[str] | None = None) -> None:
        self.feature_cols = list(feature_cols) if feature_cols is not None else None
        self._coef: np.ndarray | None = None
        self._intercept: float | None = None

    def fit(self, X: pd.DataFrame, y: Sequence[float] | pd.Series) -> "HARModel":
        Xd = X.copy()
        yd = pd.Series(y).copy()
        if self.feature_cols is not None:
            Xd = Xd[self.feature_cols]
        df = pd.concat([Xd, yd.rename("y")], axis=1).dropna()
        Xm = df.drop(columns=["y"]).to_numpy(dtype=float)
        ym = df["y"].to_numpy(dtype=float)
        # Add intercept
        ones = np.ones((Xm.shape[0], 1))
        A = np.hstack([ones, Xm])
        coef, *_ = np.linalg.lstsq(A, ym, rcond=None)
        self._intercept = float(coef[0])
        self._coef = coef[1:]
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self._coef is None or self._intercept is None:
            raise RuntimeError("Call fit() before predict().")
        Xd = X.copy()
        if self.feature_cols is not None:
            Xd = Xd[self.feature_cols]
        Xm = Xd.to_numpy(dtype=float)
        return self._intercept + Xm @ self._coef


class LinearBaseline:
    def __init__(self, feature_cols: Iterable[str] | None = None) -> None:
        self.feature_cols = list(feature_cols) if feature_cols is not None else None
        self._coef: np.ndarray | None = None
        self._intercept: float | None = None

    def fit(self, X: pd.DataFrame, y: Sequence[float] | pd.Series) -> "LinearBaseline":
        Xd = X.copy()
        yd = pd.Series(y).copy()
        if self.feature_cols is not None:
            Xd = Xd[self.feature_cols]
        df = pd.concat([Xd, yd.rename("y")], axis=1).dropna()
        Xm = df.drop(columns=["y"]).to_numpy(dtype=float)
        ym = df["y"].to_numpy(dtype=float)
        ones = np.ones((Xm.shape[0], 1))
        A = np.hstack([ones, Xm])
        coef, *_ = np.linalg.lstsq(A, ym, rcond=None)
        self._intercept = float(coef[0])
        self._coef = coef[1:]
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self._coef is None or self._intercept is None:
            raise RuntimeError("Call fit() before predict().")
        Xd = X.copy()
        if self.feature_cols is not None:
            Xd = Xd[self.feature_cols]
        Xm = Xd.to_numpy(dtype=float)
        return self._intercept + Xm @ self._coef


class LinearQuantileBaseline:
    def __init__(self, quantiles: List[float] | None = None) -> None:
        self.quantiles = quantiles or [0.1, 0.5, 0.9]
        self._coef: np.ndarray | None = None
        self._intercept: float | None = None
        self._residual_quantiles: dict[float, float] | None = None

    def fit(
        self, X: pd.DataFrame, y: Sequence[float] | pd.Series
    ) -> "LinearQuantileBaseline":
        # Fit a simple OLS model to get a baseline prediction and residuals
        Xd = X.copy()
        yd = pd.Series(y).copy()
        df = pd.concat([Xd, yd.rename("y")], axis=1).dropna()
        Xm = df.drop(columns=["y"]).to_numpy(dtype=float)
        ym = df["y"].to_numpy(dtype=float)
        ones = np.ones((Xm.shape[0], 1))
        A = np.hstack([ones, Xm])
        coef, *_ = np.linalg.lstsq(A, ym, rcond=None)
        self._intercept = float(coef[0])
        self._coef = coef[1:]
        pred = self._intercept + Xm @ self._coef
        resid = ym - pred
        # Pre-compute residual quantiles
        self._residual_quantiles = {
            q: float(np.quantile(resid, q)) for q in self.quantiles
        }
        return self

    def predict_quantiles(self, X: pd.DataFrame) -> pd.DataFrame:
        if (
            self._coef is None
            or self._intercept is None
            or self._residual_quantiles is None
        ):
            raise RuntimeError("Call fit() before predict_quantiles().")
        Xm = X.to_numpy(dtype=float)
        base = self._intercept + Xm @ self._coef
        cols = {}
        for q in sorted(self.quantiles):
            offset = self._residual_quantiles.get(q, 0.0)
            cols[f"q{int(round(q*100))}"] = base + offset
        return pd.DataFrame(cols, index=X.index if hasattr(X, "index") else None)


def quantile_interval_confidence(
    preds: pd.DataFrame, *, lower: str = "q10", upper: str = "q90"
) -> np.ndarray:
    if lower not in preds.columns or upper not in preds.columns:
        raise ValueError("Missing quantile columns in preds.")
    width = preds[upper].to_numpy() - preds[lower].to_numpy()
    # Normalize to [0,1] via max-width scaling; invert so narrower => higher confidence
    maxw = float(np.nanmax(np.abs(width))) if np.any(np.isfinite(width)) else 1.0
    if maxw <= 0 or not np.isfinite(maxw):
        maxw = 1.0
    conf = 1.0 - (np.abs(width) / (maxw + 1e-12))
    conf = np.clip(conf, 0.0, 1.0)
    # Replace NaN with midpoint confidence
    conf = np.where(np.isfinite(conf), conf, 0.5)
    return conf
