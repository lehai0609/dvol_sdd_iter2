"""Cost model utilities for backtests (T040 tests).

Real implementation will be added in T079; keep API stable.
"""

from __future__ import annotations
import pandas as pd


def simulate_pnl(
    *, returns: pd.Series, signals: pd.Series, fee_bps: float, slippage_bps: float
) -> pd.DataFrame:
    """
    Compute per-period gross, costs, and net PnL given asset returns and positions.

    Expected by tests:
    - gross uses previous period's position (no lookahead)
    - costs applied when position changes, non-negative
    - net = gross - costs
    """
    r = pd.Series(returns)
    p = pd.Series(signals).astype(float)
    p_prev = p.shift(1).fillna(0.0)
    gross = p_prev * r
    changed = (p != p_prev).astype(int)
    cost_per_flip = (float(fee_bps) + float(slippage_bps)) / 10000.0
    costs = changed * cost_per_flip
    net = gross - costs
    return pd.DataFrame(
        {"gross": gross.values, "costs": costs.values, "net": net.values}, index=r.index
    )
