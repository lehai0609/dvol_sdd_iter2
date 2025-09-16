"""Walk-forward split utilities and runner."""

from __future__ import annotations
from typing import Callable, Dict, Generator, Iterable, List, Tuple

import pandas as pd


def expanding_folds(
    *, index: pd.Index, initial: int, test_size: int, step: int
) -> Generator[Tuple[pd.Index, pd.Index], None, None]:
    """
    Placeholder API for expanding walk-forward folds.

    Yields pairs of (train_index, test_index) where indices are slices of the input index.
    Real implementation will go in T078; tests in T031 validate API and leakage constraints.
    """
    if not isinstance(index, pd.Index):
        raise TypeError("index must be a pandas Index")
    n = len(index)
    if initial <= 0 or test_size <= 0 or step <= 0:
        return
    test_start = initial
    while test_start < n:
        test_end = min(test_start + test_size, n)
        if test_start >= test_end:
            break
        train_idx = index[:test_start]
        test_idx = index[test_start:test_end]
        if len(train_idx) == 0 or len(test_idx) == 0:
            break
        yield (train_idx, test_idx)
        # advance by step while keeping expanding training window (up to next test_start)
        test_start += step


def run_walkforward(
    X: pd.DataFrame,
    y: pd.Series,
    *,
    horizons: Iterable[int] = (1, 7, 14),
    initial: int = 30,
    test_size: int = 5,
    step: int = 5,
    model_factory: Callable[[], object] | None = None,
    artifact_dir: str | None = None,
) -> Dict[int, pd.DataFrame]:
    """Train expanding-fold quantile models and predict per horizon.

    Returns a dict mapping horizon -> DataFrame of quantile predictions
    with index aligned to test dates. If artifact_dir is provided, writes
    CSVs per horizon with quantile predictions.
    """
    from pathlib import Path

    if model_factory is None:
        from .trees import QuantileGBDT

        def _factory() -> object:
            return QuantileGBDT()

        model_factory = _factory

    preds_by_h: Dict[int, pd.DataFrame] = {}
    idx = X.index
    for h in horizons:
        y_h = y.shift(-h)
        all_preds: List[pd.DataFrame] = []
        for train_idx, test_idx in expanding_folds(
            index=idx, initial=initial, test_size=test_size, step=step
        ):
            train_mask = idx.isin(train_idx)
            test_mask = idx.isin(test_idx)

            X_train = X.loc[train_mask]
            y_train = y_h.loc[train_mask]
            df_train = pd.concat([X_train, y_train.rename("y")], axis=1).dropna()
            if df_train.empty:
                continue
            Xtr = df_train.drop(columns=["y"]) 
            ytr = df_train["y"]

            model = model_factory()
            if hasattr(model, "fit"):
                model.fit(Xtr, ytr)
            else:  # pragma: no cover - defensive
                raise TypeError("model_factory must produce an object with fit()")

            X_test = X.loc[test_mask]
            if hasattr(model, "predict_quantiles"):
                qpred = model.predict_quantiles(X_test)
            else:  # pragma: no cover
                raise TypeError("model must support predict_quantiles()")
            qpred.index = X_test.index
            all_preds.append(qpred)

        if all_preds:
            preds = pd.concat(all_preds).sort_index()
        else:
            preds = pd.DataFrame(index=idx, columns=["q10", "q50", "q90"])  # empty fallback
        preds_by_h[h] = preds

        # Persist artifacts if requested
        if artifact_dir:
            outdir = Path(artifact_dir)
            outdir.mkdir(parents=True, exist_ok=True)
            path = outdir / f"preds_h{h}d.csv"
            preds.to_csv(path, index=True)

    return preds_by_h
