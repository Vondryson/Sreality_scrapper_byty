from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from google.auth.credentials import Credentials
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request

from sreality_tracker.distances.auth import GoogleAdcAccessTokenProvider
from sreality_tracker.distances.routes import RoutesError


class FakeCredentials(Credentials):
    def __init__(self, *, fail_refresh: bool = False) -> None:
        super().__init__()
        self.fail_refresh = fail_refresh
        self.refresh_count = 0

    def refresh(self, request: Request) -> None:
        del request
        self.refresh_count += 1
        if self.fail_refresh:
            raise RefreshError("sensitive provider response")
        self.token = "short-lived-adc-token"
        # google-auth normalizes credential expiry to a naive UTC datetime.
        self.expiry = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)


def test_adc_provider_refreshes_once_and_reuses_fresh_token() -> None:
    credentials = FakeCredentials()
    provider = GoogleAdcAccessTokenProvider(
        "sreality-scrapper-504307",
        credentials=credentials,
        request=Request(),
    )

    assert provider() == "short-lived-adc-token"
    assert provider() == "short-lived-adc-token"
    assert credentials.refresh_count == 1
    assert credentials.valid


def test_adc_provider_redacts_refresh_failure() -> None:
    credentials = FakeCredentials(fail_refresh=True)
    provider = GoogleAdcAccessTokenProvider(
        "sreality-scrapper-504307",
        credentials=credentials,
        request=Request(),
    )

    with pytest.raises(RoutesError, match="refresh failed") as captured:
        provider()

    assert "sensitive provider response" not in str(captured.value)
