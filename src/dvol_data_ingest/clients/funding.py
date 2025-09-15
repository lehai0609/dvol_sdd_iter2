"""Funding rates endpoint client.

Implements T023.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from dvol_data_ingest.models.api_responses import FundingRatesApiResponse

from .base import CDDClient

# Match contract: /v1/data/ohlc/deribit/futures/funding/
FUNDING_PATH = "/data/ohlc/deribit/futures/funding/"


class FundingClient(CDDClient):
    def fetch(
        self,
        *,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        limit: int | None = None,
    ) -> list[FundingRatesApiResponse]:
        params: dict[str, Any] = {"symbol": symbol}
        # Map optional window to CDD-compatible enddate
        enddate = end or start
        if enddate:
            params["enddate"] = enddate
        if limit is not None:
            params["limit"] = limit
        r = self.get(FUNDING_PATH, params=params)
        data = r.json()
        items: Iterable[dict[str, Any]]
        if isinstance(data, dict) and isinstance(data.get("result"), list):
            items = data["result"]
        elif isinstance(data, list):  # pragma: no cover
            items = data
        else:  # pragma: no cover
            items = []
        return [FundingRatesApiResponse.model_validate(x) for x in items]


__all__ = ["FundingClient"]
