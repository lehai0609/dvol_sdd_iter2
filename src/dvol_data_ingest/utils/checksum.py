"""Deterministic checksum utilities.

Implements T026: canonical JSON encoding and SHA-256 hashing.
"""

from __future__ import annotations

import dataclasses as _dc
import hashlib
import json
from collections.abc import Mapping
from typing import Any


def _to_plain(obj: Any) -> Any:
    """Best-effort conversion to plain Python types for stable JSON.

    - Pydantic v2 models: use `model_dump()` if available
    - Dataclasses: `asdict`
    - Sets: convert to sorted list of items
    - Mappings/Sequences: descend recursively
    Fallback to the original object and let `json.dumps(..., default=str)` handle.
    """
    # Pydantic v2
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            return obj.model_dump()  # type: ignore[no-any-return]
        except Exception:  # pragma: no cover - defensive
            pass

    # Dataclasses
    if _dc.is_dataclass(obj):
        try:
            return _dc.asdict(obj)
        except Exception:  # pragma: no cover - defensive
            pass

    # Built-ins
    if isinstance(obj, list | tuple):
        return [_to_plain(x) for x in obj]
    if isinstance(obj, set):
        return sorted(
            (_to_plain(x) for x in obj),
            key=lambda v: json.dumps(v, sort_keys=True, default=str),
        )
    if isinstance(obj, Mapping):
        return {str(k): _to_plain(v) for k, v in obj.items()}

    return obj


def canonical_json(obj: Any) -> str:
    """Render object to canonical JSON for platform-independent hashing.

    - Converts common complex types to plain structures
    - Sorts keys at all levels
    - Uses compact separators
    - Falls back to `str(value)` for non-serializable values
    """
    plain = _to_plain(obj)
    return json.dumps(plain, sort_keys=True, separators=(",", ":"), default=str)


def checksum_sha256(obj: Any) -> str:
    """Compute SHA-256 hex digest over canonical JSON representation."""
    payload = canonical_json(obj)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = ["canonical_json", "checksum_sha256"]
