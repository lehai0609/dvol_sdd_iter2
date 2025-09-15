"""Options summary endpoint client.

Implements T021.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from dvol_data_ingest.models.api_responses import OptionsSummaryApiResponse

from .base import CDDClient

OPTIONS_PATH = "/data/summary/deribit/options/greeks/maturities/"


class OptionsClient(CDDClient):
    def fetch(
        self,
        *,
        underlying: Literal["BTC", "ETH"],
        date: str | None = None,
        enddate: str | None = None,
        limit: int | None = None,
    ) -> list[OptionsSummaryApiResponse]:
        params: dict[str, Any] = {"underlying": underlying}
        # API expects enddate+limit; support legacy 'date' by mapping to enddate
        ed = enddate or date
        if ed:
            params["enddate"] = ed
        if limit is not None:
            params["limit"] = limit
        r = self.get(OPTIONS_PATH, params=params)
        data = r.json()
        items: Iterable[dict[str, Any]]
        if isinstance(data, dict) and isinstance(data.get("result"), list):
            items = data["result"]
        elif isinstance(data, list):  # pragma: no cover
            items = data
        else:  # pragma: no cover
            items = []
        return [OptionsSummaryApiResponse.model_validate(x) for x in items]


__all__ = ["OptionsClient"]
