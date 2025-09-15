"""Base API client for CryptoDataDownload.

Implements T019: `CDDClient` with
- session management
- optional authentication header
- timeout configuration
- exponential backoff retry (via urllib3 Retry)
- simple rate limiting (requests/second)
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import requests
from requests import Response, Session
from urllib3.util import Retry
from loguru import logger

DEFAULT_BASE_URL = "https://api.cryptodatadownload.com/v1"


@dataclass
class RetryConfig:
    max_retries: int = 3
    backoff_factor: float = 0.8
    status_forcelist: tuple[int, ...] = (429, 500, 502, 503, 504)
    allowed_methods: tuple[str, ...] = (
        "HEAD",
        "GET",
        "OPTIONS",
    )


class _RateLimiter:
    """Very small, thread-safe rate limiter (requests/second)."""

    def __init__(self, rate_per_sec: float | None):
        self._min_interval = 1.0 / rate_per_sec if rate_per_sec else 0.0
        self._lock = threading.Lock()
        self._last_ts = 0.0

    def wait(self) -> None:
        if self._min_interval <= 0:
            return
        with self._lock:
            now = time.perf_counter()
            delta = now - self._last_ts
            sleep_for = self._min_interval - delta
            if sleep_for > 0:
                time.sleep(sleep_for)
                now = time.perf_counter()
            self._last_ts = now


class CDDClient:
    """Base client for CryptoDataDownload API.

    Usage:
        with CDDClient() as client:
            r = client.get("/data/ohlc/deribit/volatility", params={"symbol": "BTC"})
            data = r.json()
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_s: float | None = None,
        retry: RetryConfig | None = None,
        rate_per_sec: float | None = None,
        session: Session | None = None,
        user_agent: str | None = None,
    ) -> None:
        env_base = os.getenv("CDD_API_BASE_URL")
        self.base_url = (base_url or env_base or DEFAULT_BASE_URL).rstrip("/")
        # Accept multiple env variable names for compatibility
        self.api_key = (
            api_key
            or os.getenv("CDD_API_KEY")
            or os.getenv("CDD_API_TOKEN")
            or os.getenv("CDD_TOKEN")
            or None
        )
        self.timeout_s = float(
            timeout_s or os.getenv("CDD_TIMEOUT_S") or 30
        )
        self.retry = retry or RetryConfig(
            max_retries=int(os.getenv("CDD_MAX_RETRIES", "3")),
            backoff_factor=float(os.getenv("CDD_BACKOFF", "0.8")),
        )
        self._rate = _RateLimiter(rate_per_sec)
        self._session = session or requests.Session()
        self._user_agent = user_agent or "dvol-data-ingest/0.0.0"

        self._configure_session()

    # --- public API -----------------------------------------------------
    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> CDDClient:  # pragma: no cover - convenience
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> Response:
        url = self._build_url(path)
        # Always request JSON format unless explicitly overridden
        merged_params: dict[str, Any] = dict(params) if params else {}
        merged_params.setdefault("return", "JSON")

        # Merge headers; prefer CDD "TOKEN" auth style
        merged_headers = self._merge_headers(headers)
        if self.api_key and merged_headers.get("Authorization", "").startswith("Bearer "):
            # Switch to CDD-preferred scheme
            merged_headers["Authorization"] = f"TOKEN {self.api_key}"

        if os.getenv("CDD_DEBUG") == "1":
            masked = (
                (str(self.api_key)[:4] + "..." + str(self.api_key)[-4:])
                if self.api_key and len(str(self.api_key)) >= 8
                else ("SET" if self.api_key else "MISSING")
            )
            logger.debug(
                f"CDD request {method.upper()} {url} params={merged_params} auth={'yes' if self.api_key else 'no'} token={masked}"
            )

        self._rate.wait()
        resp = self._session.request(
            method=method.upper(),
            url=url,
            params=merged_params,
            headers=merged_headers,
            timeout=timeout or self.timeout_s,
        )
        try:
            # Let Retry handle transient errors; raise remaining HTTP errors
            resp.raise_for_status()
            return resp
        except requests.HTTPError:
            # Fallback once with query param auth_token if unauthorized
            if resp.status_code == 401 and self.api_key:
                params_fb = dict(merged_params)
                params_fb["auth_token"] = self.api_key
                headers_fb = dict(merged_headers)
                headers_fb.pop("Authorization", None)
                if os.getenv("CDD_DEBUG") == "1":
                    logger.debug("401 received; retrying with auth_token query param")
                resp2 = self._session.request(
                    method=method.upper(),
                    url=url,
                    params=params_fb,
                    headers=headers_fb,
                    timeout=timeout or self.timeout_s,
                )
                resp2.raise_for_status()
                return resp2
            raise

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> Response:
        return self.request(
            "GET", path, params=params, headers=headers, timeout=timeout
        )

    # --- internals ------------------------------------------------------
    def _build_url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _default_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": self._user_agent,
        }
        if self.api_key:
            # CryptoDataDownload expects "TOKEN <api_key>" by default
            headers["Authorization"] = f"TOKEN {self.api_key}"
        return headers

    def _merge_headers(self, extra: Mapping[str, str] | None) -> dict[str, str]:
        base = self._default_headers()
        if extra:
            base.update(dict(extra))
        return base

    def _configure_session(self) -> None:
        adapter = requests.adapters.HTTPAdapter(
            max_retries=Retry(
                total=self.retry.max_retries,
                backoff_factor=self.retry.backoff_factor,
                status_forcelist=self.retry.status_forcelist,
                allowed_methods=self.retry.allowed_methods,
                raise_on_status=False,
            )
        )
        self._session.headers.update(self._default_headers())
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)


__all__ = ["CDDClient", "RetryConfig"]
