"""Futures OHLCV endpoint client.

Implements T022.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from dvol_data_ingest.models.api_responses import FuturesOHLCVApiResponse

from .base import CDDClient

FUTURES_PATH = "/data/ohlc/deribit/futures/"


class FuturesClient(CDDClient):
    def fetch(
        self,
        *,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        limit: int | None = None,
    ) -> list[FuturesOHLCVApiResponse]:
        params: dict[str, Any] = {"symbol": symbol}
        # CDD uses enddate+limit for pagination; map provided window to enddate when possible
        enddate = end or start
        if enddate:
            params["enddate"] = enddate
        if limit is not None:
            params["limit"] = limit
        r = self.get(FUTURES_PATH, params=params)
        data = r.json()
        items: Iterable[dict[str, Any]]
        if isinstance(data, dict) and isinstance(data.get("result"), list):
            items = data["result"]
        elif isinstance(data, list):  # pragma: no cover
            items = data
        else:  # pragma: no cover
            items = []
        return [FuturesOHLCVApiResponse.model_validate(x) for x in items]


__all__ = ["FuturesClient"]
