"""On-chain blocks summary endpoint client.

Implements T024.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from dvol_data_ingest.models.api_responses import OnChainDataApiResponse

from .base import CDDClient

ONCHAIN_PATH = "/data/summary/blockchain/blocks/"


class OnChainClient(CDDClient):
    def fetch(
        self,
        *,
        symbol: Literal["btc", "eth"],
        date: str | None = None,
        enddate: str | None = None,
        limit: int | None = None,
    ) -> list[OnChainDataApiResponse]:
        params: dict[str, Any] = {"symbol": symbol}
        ed = enddate or date
        if ed:
            params["enddate"] = ed
        if limit is not None:
            params["limit"] = limit
        r = self.get(ONCHAIN_PATH, params=params)
        data = r.json()
        items: Iterable[dict[str, Any]]
        if isinstance(data, dict) and isinstance(data.get("result"), list):
            items = data["result"]
        elif isinstance(data, list):  # pragma: no cover
            items = data
        else:  # pragma: no cover
            items = []
        return [OnChainDataApiResponse.model_validate(x) for x in items]


__all__ = ["OnChainClient"]
