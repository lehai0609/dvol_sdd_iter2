import numpy as np
import pandas as pd


def test_costs_applied_on_position_changes_and_net_matches():
    from backtest.costs import simulate_pnl

    # Synthetic returns and simple flip-flop signals
    returns = pd.Series([0.01, -0.02, 0.015, 0.0, -0.01], name="ret")
    # Positions decided end of day t-1 for day t: start flat, then long, hold, flip short, flat
    signals = pd.Series([0, 1, 1, -1, 0], name="pos")

    fee_bps = 5.0
    slip_bps = 3.0

    res = simulate_pnl(
        returns=returns, signals=signals, fee_bps=fee_bps, slippage_bps=slip_bps
    )

    # Required columns
    for c in ["gross", "costs", "net"]:
        assert c in res.columns

    # Costs are non-negative and only applied when position changes
    pos = signals
    pos_prev = pos.shift(1).fillna(0)
    changed = (pos != pos_prev).astype(int)

    assert (res["costs"] >= 0).all()
    assert ((res["costs"] > 0) == (changed == 1)).all()

    # Net equals gross minus costs
    assert np.allclose(res["net"].values, res["gross"].values - res["costs"].values)

    # Gross PnL uses previous day's position to avoid lookahead
    expected_gross = (pos_prev * returns).values
    assert np.allclose(res["gross"].values, expected_gross)
