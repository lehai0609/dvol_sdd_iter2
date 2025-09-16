from pathlib import Path

import numpy as np
import pandas as pd


def test_walkforward_pipeline_produces_artifacts_and_forecasts(tmp_path: Path):
    from models.walkforward import run_walkforward
    from models.reproduce import build_forecast_records
    from models.trees import QuantileGBDT

    # Synthetic dataset
    idx = pd.date_range("2024-01-01", periods=60, freq="D")
    rng = np.random.default_rng(42)
    X = pd.DataFrame({"x1": rng.normal(size=len(idx)), "x2": rng.normal(size=len(idx))}, index=idx)
    y = 2.0 * X["x1"] - 0.5 * X["x2"] + rng.normal(scale=0.1, size=len(idx))

    outdir = tmp_path / "artifacts" / "models" / "run-test"
    preds_by_h = run_walkforward(
        X,
        y,
        horizons=(1, 7, 14),
        initial=30,
        test_size=5,
        step=5,
        model_factory=lambda: QuantileGBDT(lgbm_params={"n_estimators": 40, "num_leaves": 15}),
        artifact_dir=str(outdir),
    )

    # At least one horizon should have non-empty predictions
    assert any(not df.empty for df in preds_by_h.values())

    # Build forecast records
    forecasts = build_forecast_records(asset="BTC", preds_by_horizon=preds_by_h)
    assert not forecasts.empty
    # Required columns
    for col in ["asset", "date", "horizon", "forecast_dvol", "direction", "confidence"]:
        assert col in forecasts.columns

    # Direction in allowed set; confidence in [0,1]
    assert set(forecasts["direction"]).issubset({"up", "flat", "down"})
    assert ((forecasts["confidence"] >= 0.0) & (forecasts["confidence"] <= 1.0)).all()

    # Artifacts written
    assert outdir.exists()
    files = list(outdir.glob("preds_h*d.csv"))
    assert files, "Expected predictions CSVs per horizon"
