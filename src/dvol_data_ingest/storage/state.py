"""Simple ingestion state management.

Implements T030:
- Track last fetch per (data_source, asset)
- Persist state in JSON with atomic writes
- Provide incremental fetch helpers and validation/recovery

Design goals: tiny, readable, dependency-light.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

UTC = UTC


@dataclass
class StateEntry:
    last_date: str | None = None  # YYYY-MM-DD (UTC trading date)
    last_unix_ms: int | None = None


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class IngestState:
    def __init__(
        self, path: str | os.PathLike[str] = "./data/state/ingest_state.json"
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # --- persistence -----------------------------------------------------
    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "updated_at": _now_iso(), "entries": {}}
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, content: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, self.path)

    # --- keys ------------------------------------------------------------
    @staticmethod
    def _key(data_source: str, asset: str) -> str:
        return f"{data_source}:{asset}".upper()

    # --- API -------------------------------------------------------------
    def get(self, data_source: str, asset: str) -> StateEntry | None:
        doc = self._read()
        key = self._key(data_source, asset)
        raw = doc.get("entries", {}).get(key)
        if not raw:
            return None
        return StateEntry(**raw)

    def set(self, data_source: str, asset: str, entry: StateEntry) -> None:
        doc = self._read()
        doc.setdefault("entries", {})[self._key(data_source, asset)] = asdict(entry)
        doc["updated_at"] = _now_iso()
        self._write(doc)

    def update(
        self,
        data_source: str,
        asset: str,
        *,
        last_date: str | None = None,
        last_unix_ms: int | None = None,
    ) -> StateEntry:
        current = self.get(data_source, asset) or StateEntry()
        if last_date is not None:
            current.last_date = last_date
        if last_unix_ms is not None:
            current.last_unix_ms = last_unix_ms
        self.set(data_source, asset, current)
        return current

    # --- incremental helpers --------------------------------------------
    @staticmethod
    def _next_date_str(prev: str | None) -> str | None:
        if not prev:
            return None
        d = datetime.strptime(prev, "%Y-%m-%d").date() + timedelta(days=1)
        return d.isoformat()

    def next_fetch_params(
        self,
        data_source: str,
        asset: str,
        *,
        default_days: int = 7,
    ) -> dict[str, str]:
        """Return simple incremental params.

        - If we have a last_date: start = last_date + 1 day
        - Else: start = today - default_days
        """
        today = datetime.now(tz=UTC).date()
        entry = self.get(data_source, asset)
        if entry and entry.last_date:
            start = self._next_date_str(entry.last_date)
        else:
            start = (today - timedelta(days=default_days)).isoformat()
        return {"start": start, "end": today.isoformat()}

    # --- validation and recovery ----------------------------------------
    def validate(self) -> bool:
        try:
            doc = self._read()
        except Exception:
            return False
        if not isinstance(doc, dict):
            return False
        if "entries" not in doc or not isinstance(doc["entries"], dict):
            return False
        # spot-check values
        for k, v in doc["entries"].items():
            if not isinstance(k, str) or not isinstance(v, dict):
                return False
            ld = v.get("last_date")
            if ld is not None:
                try:
                    datetime.strptime(ld, "%Y-%m-%d")
                except Exception:
                    return False
            lu = v.get("last_unix_ms")
            if lu is not None and (not isinstance(lu, int) or lu < 0):
                return False
        return True

    def recover(self) -> None:
        """If state file is invalid, back it up and create a fresh one."""
        if self.validate():
            return
        if self.path.exists():
            stamp = datetime.now(tz=UTC).strftime("%Y%m%d%H%M%S")
            backup = self.path.with_suffix(self.path.suffix + f".bad-{stamp}")
            os.replace(self.path, backup)
        self._write({"version": 1, "updated_at": _now_iso(), "entries": {}})


__all__ = ["StateEntry", "IngestState"]
