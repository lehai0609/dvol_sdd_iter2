import numpy as np
import pandas as pd


def test_rmse_and_mae_on_toy_data():
    from metrics.eval import rmse, mae

    y_true = np.array([1.0, 1.0])
    y_pred = np.array([2.0, 0.0])

    assert rmse(y_true, y_pred) == 1.0
    assert mae(y_true, y_pred) == 1.0


def test_spearman_on_monotone_and_reverse():
    from metrics.eval import spearman

    a = np.array([1.0, 2.0, 3.0, 4.0])
    b = np.array([10.0, 20.0, 30.0, 40.0])
    c = b[::-1]

    rho_ab = spearman(a, b)
    rho_ac = spearman(a, c)

    assert np.isclose(rho_ab, 1.0)
    assert np.isclose(rho_ac, -1.0)


def test_hit_rate_directional_toy_example():
    from metrics.eval import hit_rate

    y_true = pd.Series([1.0, -2.0, 3.0, -4.0])
    y_pred = pd.Series([0.5, -0.1, -3.0, -5.0])

    # Signs: true [+,-,+,-], pred [+,-,-,-] -> 3/4 correct
    hr = hit_rate(y_true, y_pred)
    assert np.isclose(hr, 0.75)
