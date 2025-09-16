from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


DEFAULT_POLICY_PATH = Path(
    "specs/001-dvol-forecasting-volatility/contracts/policy.cutoff.yaml"
)


def load_policy(path: str | Path | None = None) -> Dict[str, Any]:
    """Load the cutoff policy YAML as a dict.

    Defaults to the repository policy path under specs/…/contracts.
    """
    p = Path(path) if path is not None else DEFAULT_POLICY_PATH
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

