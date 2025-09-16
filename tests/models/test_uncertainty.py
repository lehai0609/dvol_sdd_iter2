import numpy as np
import pandas as pd


def _make_linear(n: int = 120, seed: int = 123):
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    noise = rng.normal(scale=0.1, size=n)
    y = 2.0 * x1 - 0.5 * x2 + noise
    X = pd.DataFrame({"x1": x1, "x2": x2})
    return X, pd.Series(y, name="y")


def test_quantile_outputs_monotone_and_confidence_bounded():
    from models.baselines import LinearQuantileBaseline, quantile_interval_confidence

    X, y = _make_linear()
    n_train = 90
    X_train, y_train = X.iloc[:n_train], y.iloc[:n_train]
    X_test = X.iloc[n_train:]

    model = LinearQuantileBaseline(quantiles=[0.1, 0.5, 0.9])
    model.fit(X_train, y_train)
    qpred = model.predict_quantiles(X_test)

    # Expect standard column names for quantiles
    for col in ["q10", "q50", "q90"]:
        assert col in qpred.columns

    # Monotone per-row: q10 <= q50 <= q90
    qvals = qpred[["q10", "q50", "q90"]].values
    assert np.all(qvals[:, 0] <= qvals[:, 1])
    assert np.all(qvals[:, 1] <= qvals[:, 2])

    # Confidence derived from interval width should be in [0,1]
    conf = quantile_interval_confidence(qpred, lower="q10", upper="q90")
    assert conf.shape[0] == qpred.shape[0]
    assert np.all(conf >= 0.0) and np.all(conf <= 1.0)
