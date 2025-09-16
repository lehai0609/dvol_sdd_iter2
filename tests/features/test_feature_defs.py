import numpy as np
import pandas as pd


def test_golden_feature_outputs_deterministic():
    # Golden input
    dates = pd.date_range("2024-06-01", periods=6, freq="D")
    dvol = [40.0, 42.0, 41.0, 43.0, 44.0, 45.0]
    price = [100.0, 99.0, 101.0, 102.0, 101.0, 103.0]
    df = pd.DataFrame(
        {
            "date": dates,
            "dvol_close": dvol,
            "price_close": price,
        }
    )

    # Deterministic feature definitions (no randomness, pure functions)
    df["dvol_lag1"] = df["dvol_close"].shift(1)
    df["dvol_change1"] = df["dvol_close"].shift(1) - df["dvol_close"].shift(2)
    # Realized volatility over 3d window of returns, computed up to t-1
    returns = pd.Series(df["price_close"]).pct_change()
    df["rv_3d"] = returns.shift(1).rolling(3).std() * np.sqrt(252)

    # Expected values computed by hand
    # dvol_lag1: [nan, 40, 42, 41, 43, 44]
    assert np.isnan(df.loc[0, "dvol_lag1"]) or df.loc[0, "dvol_lag1"] is None
    assert df.loc[1, "dvol_lag1"] == 40.0
    assert df.loc[2, "dvol_lag1"] == 42.0
    assert df.loc[3, "dvol_lag1"] == 41.0
    assert df.loc[4, "dvol_lag1"] == 43.0
    assert df.loc[5, "dvol_lag1"] == 44.0

    # dvol_change1: [nan, nan, 2, -1, 2, 1]
    assert np.isnan(df.loc[0, "dvol_change1"]) or df.loc[0, "dvol_change1"] is None
    assert np.isnan(df.loc[1, "dvol_change1"]) or df.loc[1, "dvol_change1"] is None
    assert df.loc[2, "dvol_change1"] == 2.0
    assert df.loc[3, "dvol_change1"] == -1.0
    assert df.loc[4, "dvol_change1"] == 2.0
    assert df.loc[5, "dvol_change1"] == 1.0

    # RV window should be deterministic given the prices
    # returns: [nan, -0.01, 0.02020202, 0.00990099, -0.00980392, 0.01980198]
    # rv_3d at t=3 uses returns[0..2] shifted -> (nan, -0.01, 0.0202) -> still nan until enough obs
    assert np.isnan(df.loc[0, "rv_3d"]) or df.loc[0, "rv_3d"] is None
    assert np.isnan(df.loc[1, "rv_3d"]) or df.loc[1, "rv_3d"] is None
    assert np.isnan(df.loc[2, "rv_3d"]) or df.loc[2, "rv_3d"] is None
    # First non-null occurs at index 4 due to shift and 3-point window
    assert np.isnan(df.loc[3, "rv_3d"]) or df.loc[3, "rv_3d"] is None
    assert df.loc[4, "rv_3d"] > 0
    assert df.loc[5, "rv_3d"] > 0
