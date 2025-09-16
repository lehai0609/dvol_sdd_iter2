import numpy as np
import pandas as pd


def test_risk_guardrails_trigger_and_caps_enforced():
    from backtest.risk import apply_guardrails

    # Create a scenario with a volatility jump where signals would go max long
    dates = pd.date_range("2022-01-01", periods=10, freq="D")
    scores = pd.Series([0, 0.1, 0.2, 3.0, 2.5, 0.1, -2.0, -3.5, -0.2, 0.0], index=dates)
    raw_positions = scores.apply(lambda s: 1 if s > 0 else (-1 if s < 0 else 0))

    # Guardrails configuration
    cfg = {
        "max_abs_position": 0.5,  # cap absolute exposure
        "event_guard_threshold": 2.0,  # if score amplitude exceeds, clamp positions
        "daily_stop_loss": 0.03,  # if loss beyond this, flatten next day
    }

    # Synthetic returns include a big negative jump on day 4 to trigger stop-loss
    returns = pd.Series(
        [0.0, 0.01, -0.005, -0.12, 0.02, 0.0, -0.01, 0.03, 0.0, 0.0], index=dates
    )

    guarded = apply_guardrails(positions=raw_positions, returns=returns, config=cfg)

    # Caps enforced
    assert (guarded.abs() <= cfg["max_abs_position"]).all()

    # Event guard should clamp around extreme score days
    assert (
        guarded.loc[dates[3]]
        == np.sign(raw_positions.loc[dates[3]]) * cfg["max_abs_position"]
    )

    # After a large drawdown day, next day should be flattened (<= cap, possibly 0)
    # Given stop-loss, the day after the -12% loss should be 0 exposure
    assert guarded.loc[dates[4]] == 0.0
