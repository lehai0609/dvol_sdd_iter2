import numpy as np
import pandas as pd


def _make_ar_series(
    n: int, phi: float = 0.7, sigma: float = 0.1, seed: int = 42
) -> pd.Series:
    rng = np.random.default_rng(seed)
    y = np.zeros(n, dtype=float)
    eps = rng.normal(0.0, sigma, size=n)
    for t in range(1, n):
        y[t] = phi * y[t - 1] + eps[t]
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    return pd.Series(y, index=idx, name="y")


def _har_features(y: pd.Series) -> pd.DataFrame:
    x = pd.DataFrame(index=y.index)
    x["y_lag1"] = y.shift(1)
    x["y_week"] = y.rolling(5, min_periods=5).mean().shift(1)
    x["y_month"] = y.rolling(22, min_periods=22).mean().shift(1)
    return x


def test_baselines_fit_predict_shapes():
    # Lazy import to avoid hard dependency until implementation exists
    from models.baselines import NaiveLastValue, HARModel, LinearBaseline

    y = _make_ar_series(120)
    X = _har_features(y)

    df = pd.concat([X, y], axis=1).dropna()
    X, y = df.drop(columns=["y"]), df["y"]

    n_train = 80
    X_train, y_train = X.iloc[:n_train], y.iloc[:n_train]
    X_test, y_test = X.iloc[n_train:], y.iloc[n_train:]

    # Naive baseline: should use y_lag1 as prediction proxy
    naive = NaiveLastValue(target_lag_col="y_lag1")
    naive.fit(X_train, y_train)
    p_naive = naive.predict(X_test)

    har = HARModel(
        feature_cols=["y_lag1", "y_week", "y_month"]
    )  # implementation may wrap OLS
    har.fit(X_train, y_train)
    p_har = har.predict(X_test)

    lin = LinearBaseline(feature_cols=["y_lag1", "y_week", "y_month"])  # sklearn-like
    lin.fit(X_train, y_train)
    p_lin = lin.predict(X_test)

    assert len(p_naive) == len(y_test)
    assert len(p_har) == len(y_test)
    assert len(p_lin) == len(y_test)

    # Sanity: predictions finite and errors not explosive
    y_std = float(y_test.std())
    mae_naive = float(np.mean(np.abs(p_naive - y_test.values)))
    mae_har = float(np.mean(np.abs(p_har - y_test.values)))
    mae_lin = float(np.mean(np.abs(p_lin - y_test.values)))

    assert np.isfinite(p_naive).all()
    assert np.isfinite(p_har).all()
    assert np.isfinite(p_lin).all()

    # On this AR(1) synthetic, a reasonable baseline should do better than just the variance scale
    assert mae_naive < 3 * y_std
    assert mae_har < 3 * y_std
    assert mae_lin < 3 * y_std
