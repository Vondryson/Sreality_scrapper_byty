"""Polite synchronous HTTP client for Sreality SSR pages."""

from __future__ import annotations

import logging
import random
import re
import ssl
import time
from collections.abc import Callable
from urllib.parse import urljoin

import httpx
import truststore

from sreality_tracker.domain.listings import ListingKind

SITE_BASE_URL = "https://www.sreality.cz"
SITE_HOST = "www.sreality.cz"
ALLOWED_REDIRECT_HOSTS = frozenset({SITE_HOST})
MAX_REDIRECTS = 2
USER_AGENT = "SrealityChatyTracker/0.1 (+private research project)"
NEXT_DATA_MARKER = re.compile(r"<script\b[^>]*\bid=[\"']__NEXT_DATA__[\"']", re.IGNORECASE)
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


class SrealityClientError(RuntimeError):
    """Base error raised by the Sreality client."""


class RequestFailedError(SrealityClientError):
    """Raised after all safe retry attempts are exhausted."""


class ResponseValidationError(SrealityClientError):
    """Raised when a response is not a valid Sreality SSR HTML page."""


class SrealityClient:
    """Reuse one HTTP session and enforce pacing for all request attempts."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        min_delay_seconds: float = 0.75,
        max_attempts: int = 3,
        backoff_base_seconds: float = 0.5,
        jitter_max_seconds: float = 0.25,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        random_uniform: Callable[[float, float], float] = random.uniform,
        logger: logging.Logger | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if min_delay_seconds < 0.5:
            raise ValueError("min_delay_seconds must be at least 0.5")
        if not 1 <= max_attempts <= 6:
            raise ValueError("max_attempts must be between 1 and 6")
        if backoff_base_seconds < 0 or jitter_max_seconds < 0:
            raise ValueError("backoff and jitter must be nonnegative")

        self._min_delay_seconds = min_delay_seconds
        self._max_attempts = max_attempts
        self._backoff_base_seconds = backoff_base_seconds
        self._jitter_max_seconds = jitter_max_seconds
        self._sleep = sleep
        self._monotonic = monotonic
        self._random_uniform = random_uniform
        self._logger = logger or logging.getLogger("sreality_tracker.scraper.client")
        self._last_request_started: float | None = None
        self._client = httpx.Client(
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": USER_AGENT,
            },
            follow_redirects=False,
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
            verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        )

    def __enter__(self) -> SrealityClient:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def fetch_search_page(self, kind: ListingKind, page: int = 1) -> str:
        """Fetch one confirmed chata/chalupa search result page."""
        if page < 1:
            raise ValueError("page must be positive")
        params = {"noredirect": "1"}
        if page > 1:
            params["strana"] = str(page)
        url = httpx.URL(f"{SITE_BASE_URL}/hledani/prodej/domy/{kind.search_slug}", params=params)
        return self._get_ssr_html(str(url))

    def fetch_detail_page(self, detail_path: str) -> str:
        """Fetch a relative Sreality detail path without allowing arbitrary hosts."""
        if not detail_path.startswith("/detail/"):
            raise ValueError("detail_path must be an absolute /detail/ path")
        url = httpx.URL(urljoin(SITE_BASE_URL, detail_path))
        if url.host != SITE_HOST:
            raise ValueError("detail_path must remain on the Sreality host")
        return self._get_ssr_html(str(url.copy_merge_params({"noredirect": "1"})))

    def _get_ssr_html(self, url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = self._request_with_allowed_redirects(url)
            except httpx.TransportError as error:
                last_error = error
                if attempt == self._max_attempts:
                    break
                self._wait_before_retry(attempt, reason=type(error).__name__)
                continue

            if response.status_code in RETRYABLE_STATUS_CODES:
                last_error = RequestFailedError(f"temporary HTTP {response.status_code}")
                if attempt == self._max_attempts:
                    break
                self._wait_before_retry(attempt, reason=f"http_{response.status_code}")
                continue
            if response.is_error:
                raise RequestFailedError(f"non-retryable HTTP {response.status_code}")
            return self._validate_ssr_response(response)

        reason = type(last_error).__name__ if last_error is not None else "unknown error"
        raise RequestFailedError(
            f"request failed after {self._max_attempts} attempts ({reason})"
        ) from None

    def _request_with_allowed_redirects(self, url: str) -> httpx.Response:
        current_url = httpx.URL(url)
        for _redirect_count in range(MAX_REDIRECTS + 1):
            self._pace()
            response = self._client.get(current_url)
            if not response.is_redirect:
                return response

            location = response.headers.get("location")
            if not location:
                raise ResponseValidationError("redirect response has no Location header")
            target = httpx.URL(urljoin(str(response.url), location))
            if target.scheme != "https" or target.host not in ALLOWED_REDIRECT_HOSTS:
                # A rejected consent/autologin redirect can set cookies that make
                # otherwise valid search pages redirect as well. Keep the safe
                # host boundary and discard that contaminated session state.
                self._client.cookies.clear()
                raise ResponseValidationError(
                    "response attempted to redirect outside the allowed HTTPS hosts"
                )
            current_url = target
        raise ResponseValidationError(f"response exceeded {MAX_REDIRECTS} allowed redirects")

    def _pace(self) -> None:
        now = self._monotonic()
        if self._last_request_started is not None:
            remaining = self._min_delay_seconds - (now - self._last_request_started)
            if remaining > 0:
                self._sleep(remaining)
                now = self._monotonic()
        self._last_request_started = now

    def _wait_before_retry(self, attempt: int, *, reason: str) -> None:
        delay = self._backoff_base_seconds * (2 ** (attempt - 1))
        delay += self._random_uniform(0, self._jitter_max_seconds)
        self._logger.warning(
            "Retrying Sreality request",
            extra={"event": "http_retry", "step": reason},
        )
        if delay > 0:
            self._sleep(delay)

    @staticmethod
    def _validate_ssr_response(response: httpx.Response) -> str:
        if response.url.host != SITE_HOST:
            raise ResponseValidationError("response redirected outside the Sreality host")
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type.lower():
            raise ResponseValidationError("response Content-Type is not text/html")
        if not NEXT_DATA_MARKER.search(response.text):
            raise ResponseValidationError("response has no __NEXT_DATA__ SSR payload")
        return response.text
