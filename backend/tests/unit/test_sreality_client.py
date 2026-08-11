from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from sreality_tracker.scraper.client import (
    USER_AGENT,
    ListingKind,
    RequestFailedError,
    ResponseValidationError,
    SrealityClient,
)

SSR_HTML = '<html><script id="__NEXT_DATA__" type="application/json">{}</script></html>'


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def html_response(request: httpx.Request, *, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code,
        headers={"content-type": "text/html; charset=utf-8"},
        text=SSR_HTML,
        request=request,
    )


def make_client(
    handler: Callable[[httpx.Request], httpx.Response],
    fake_time: FakeTime,
    *,
    max_attempts: int = 3,
) -> SrealityClient:
    return SrealityClient(
        transport=httpx.MockTransport(handler),
        min_delay_seconds=0.75,
        max_attempts=max_attempts,
        backoff_base_seconds=0.5,
        jitter_max_seconds=0.25,
        sleep=fake_time.sleep,
        monotonic=fake_time.monotonic,
        random_uniform=lambda _start, _end: 0.1,
    )


def test_one_session_supports_both_filters_and_global_pacing() -> None:
    requests: list[httpx.Request] = []
    fake_time = FakeTime()

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return html_response(request)

    with make_client(handler, fake_time) as client:
        client.fetch_search_page(ListingKind.CHATA)
        client.fetch_search_page(ListingKind.CHALUPA, page=2)

    assert [request.url.path for request in requests] == [
        "/hledani/prodej/domy/chaty",
        "/hledani/prodej/domy/chalupy",
    ]
    assert requests[1].url.params["strana"] == "2"
    assert all(request.url.params["noredirect"] == "1" for request in requests)
    assert all(request.headers["user-agent"] == USER_AGENT for request in requests)
    assert fake_time.sleeps == [0.75]
    assert ListingKind.CHATA.subtype == 33
    assert ListingKind.CHALUPA.subtype == 43


def test_retry_uses_backoff_jitter_and_pacing() -> None:
    fake_time = FakeTime()
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return html_response(request, status_code=503)
        if attempts == 2:
            raise httpx.ConnectError("temporary failure", request=request)
        return html_response(request)

    with make_client(handler, fake_time) as client:
        assert "__NEXT_DATA__" in client.fetch_search_page(ListingKind.CHATA)

    assert attempts == 3
    assert fake_time.sleeps == pytest.approx([0.6, 0.15, 1.1])


def test_non_retryable_status_fails_immediately() -> None:
    fake_time = FakeTime()
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return html_response(request, status_code=404)

    with (
        make_client(handler, fake_time) as client,
        pytest.raises(RequestFailedError, match="non-retryable HTTP 404"),
    ):
        client.fetch_search_page(ListingKind.CHATA)

    assert attempts == 1
    assert fake_time.sleeps == []


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (
            lambda request: httpx.Response(
                200,
                headers={"content-type": "application/json"},
                text="{}",
                request=request,
            ),
            "Content-Type",
        ),
        (
            lambda request: httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<html></html>",
                request=request,
            ),
            "__NEXT_DATA__",
        ),
        (
            lambda request: httpx.Response(
                302,
                headers={"location": "https://example.com/redirected"},
                request=request,
            ),
            "outside",
        ),
    ],
)
def test_response_validation_rejects_invalid_pages(
    response: Callable[[httpx.Request], httpx.Response],
    message: str,
) -> None:
    fake_time = FakeTime()
    with (
        make_client(response, fake_time) as client,
        pytest.raises(ResponseValidationError, match=message),
    ):
        client.fetch_search_page(ListingKind.CHATA)


def test_seznam_autologin_redirect_is_rejected_before_second_request() -> None:
    fake_time = FakeTime()
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            302,
            headers={"location": "https://login.seznam.cz/api/v1/autologin"},
            request=request,
        )

    with (
        make_client(handler, fake_time) as client,
        pytest.raises(ResponseValidationError, match="outside"),
    ):
        client.fetch_search_page(ListingKind.CHATA)

    assert len(requests) == 1


def test_detail_path_cannot_target_another_host() -> None:
    fake_time = FakeTime()
    with (
        make_client(html_response, fake_time) as client,
        pytest.raises(ValueError, match="/detail/"),
    ):
        client.fetch_detail_page("https://example.com/detail/1")
