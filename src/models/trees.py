from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


@dataclass
class QuantileGBDT:
    """LightGBM-based quantile regressor wrapper.

    Trains one regressor per requested quantile. Provides point predictions
    via the median (q50) model.
    """

    quantiles: List[float] = field(default_factory=lambda: [0.1, 0.5, 0.9])
    lgbm_params: Optional[Dict] = None
    random_state: int = 42

    def __post_init__(self) -> None:
        self.models: Dict[float, object] = {}

    def fit(self, X: pd.DataFrame, y: Iterable[float]) -> "QuantileGBDT":
        try:
            from lightgbm import LGBMRegressor  # type: ignore
        except Exception as e:  # pragma: no cover - fallback shouldn't be needed in CI
            raise ImportError("lightgbm is required for QuantileGBDT") from e

        Xm = pd.DataFrame(X).to_numpy(dtype=float)
        ym = pd.Series(y).to_numpy(dtype=float)
        params = dict(
            n_estimators=100,
            learning_rate=0.05,
            num_leaves=31,
            min_child_samples=10,
            random_state=self.random_state,
        )
        if self.lgbm_params:
            params.update(self.lgbm_params)

        self.models = {}
        for q in sorted(self.quantiles):
            model = LGBMRegressor(objective="quantile", alpha=q, **params)
            model.fit(Xm, ym)
            self.models[q] = model
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.models:
            raise RuntimeError("Call fit() before predict().")
        # Use median if available; else average across quantiles
        Xm = pd.DataFrame(X).to_numpy(dtype=float)
        if 0.5 in self.models:
            return self.models[0.5].predict(Xm)
        preds = np.column_stack([m.predict(Xm) for _, m in sorted(self.models.items())])
        return np.mean(preds, axis=1)

    def predict_quantiles(self, X: pd.DataFrame) -> pd.DataFrame:
        if not self.models:
            raise RuntimeError("Call fit() before predict_quantiles().")
        Xm = pd.DataFrame(X).to_numpy(dtype=float)
        qs = sorted(self.quantiles)
        cols = {}
        for q in qs:
            p = self.models[q].predict(Xm)
            cols[f"q{int(round(q*100))}"] = p
        df = pd.DataFrame(cols, index=X.index if hasattr(X, "index") else None)
        # Enforce monotonicity per row (q10<=q50<=q90) via cumulative max
        ordered = [f"q{int(round(q*100))}" for q in qs]
        running_max = None
        for col in ordered:
            running_max = df[col] if running_max is None else np.maximum(running_max, df[col])
            df[col] = running_max
        return df

