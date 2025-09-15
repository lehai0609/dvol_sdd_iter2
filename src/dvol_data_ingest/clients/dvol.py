"""DVOL endpoint client.

Implements T020 using `CDDClient`.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from dvol_data_ingest.models.api_responses import DVOLApiResponse

from .base import CDDClient

DVOL_PATH = "/data/ohlc/deribit/volatility"


class DVOLClient(CDDClient):
    def fetch(
        self,
        *,
        symbol: Literal["BTC", "ETH"],
        enddate: str | None = None,
        limit: int | None = None,
    ) -> list[DVOLApiResponse]:
        params: dict[str, Any] = {"symbol": symbol}
        if enddate:
            params["enddate"] = enddate
        if limit is not None:
            params["limit"] = limit

        r = self.get(DVOL_PATH, params=params)
        data = r.json()
        items: Iterable[dict[str, Any]]
        if isinstance(data, dict) and isinstance(data.get("result"), list):
            items = data["result"]
        elif isinstance(data, list):  # pragma: no cover - fallback
            items = data
        else:  # pragma: no cover - defensive
            items = []
        return [DVOLApiResponse.model_validate(x) for x in items]


__all__ = ["DVOLClient"]

