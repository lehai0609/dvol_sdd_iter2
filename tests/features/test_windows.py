import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


def test_rolling_windows_stop_before_cutoff():
    # Simulate DVOL close series
    dates = pd.date_range("2024-06-01", periods=10, freq="D")
    close = pd.Series([10, 11, 12, 13, 12, 11, 10, 9, 8, 7], index=dates)

    df = pd.DataFrame({"date": dates, "dvol_close": close.values})

    # Feature should not include same-day value — enforce via shift(1)
    window = 3
    df["ma3_prev"] = df["dvol_close"].shift(1).rolling(window).mean()

    # Pick a day in the middle
    i = 5
    feat_before = df.loc[i, "ma3_prev"]

    # Perturb same-day close; feature must remain unchanged
    df2 = df.copy()
    df2.loc[i, "dvol_close"] += 1000.0
    df2["ma3_prev"] = df2["dvol_close"].shift(1).rolling(window).mean()
    assert df2.loc[i, "ma3_prev"] == feat_before

    # Sanity: window uses only dates strictly before t
    used = df.loc[i - window : i - 1, "dvol_close"].values  # previous 3 values
    assert not np.isnan(feat_before)
    assert np.isclose(feat_before, used.mean())


def test_scaler_fit_only_on_training_window():
    # Create simple feature
    rng = np.random.default_rng(0)
    X = pd.DataFrame(
        {
            "f1": rng.normal(loc=0.0, scale=2.0, size=100),
            "f2": rng.normal(loc=5.0, scale=5.0, size=100),
        }
    )
    train = X.iloc[:70].copy()
    val = X.iloc[70:].copy()

    scaler = StandardScaler()
    scaler.fit(train)
    Xt = pd.DataFrame(scaler.transform(train), columns=X.columns)
    _ = scaler.transform(val)

    # Train normalized to ~0 mean and unit variance
    assert np.allclose(Xt.mean().values, [0, 0], atol=1e-1)
    assert np.allclose(Xt.std(ddof=0).values, [1, 1], atol=1e-1)

    # Val not used for fitting; check that re-fitting on val would change params
    scaler_val = StandardScaler().fit(val)
    # Ensure parameters differ in general (probabilistic check)
    diff = sum(abs(scaler.mean_ - scaler_val.mean_)) + sum(
        abs(scaler.scale_ - scaler_val.scale_)
    )
    assert diff > 1e-3
