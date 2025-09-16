import numpy as np
import pandas as pd


def test_threshold_calibration_produces_positive_net_edge_on_validation():
    from backtest.mapping import calibrate_thresholds, map_scores_to_positions

    # Synthetic scores with some predictive power over returns
    rng = np.random.default_rng(0)
    n = 200
    scores = pd.Series(rng.standard_normal(n))
    # Returns correlated with scores
    returns = pd.Series(0.02 * scores + 0.01 * rng.standard_normal(n))

    # Split train/validation
    split = 120
    scores_train, returns_train = scores.iloc[:split], returns.iloc[:split]
    scores_val, returns_val = scores.iloc[split:], returns.iloc[split:]

    fee_bps = 2.0
    slip_bps = 2.0

    thr = calibrate_thresholds(
        scores=scores_train,
        returns=returns_train,
        fee_bps=fee_bps,
        slippage_bps=slip_bps,
        grid=np.linspace(0.0, 1.5, 10),
    )

    # Map validation scores to positions using calibrated threshold
    pos_val = map_scores_to_positions(scores_val, threshold=thr)

    # Simple net edge check: apply naive cost model at flips only
    pos_prev = pos_val.shift(1).fillna(0)
    gross = (pos_prev * returns_val).sum()
    flips = (pos_val != pos_prev).sum()
    cost_per_flip = (fee_bps + slip_bps) / 10000.0
    costs = flips * cost_per_flip
    net_edge = gross - costs

    assert net_edge > 0.0
