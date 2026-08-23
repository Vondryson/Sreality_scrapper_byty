"""Authenticated per-execution trigger for the production Cloud Run scraper job."""

from __future__ import annotations

import re
from collections.abc import Callable

import google.auth
from google.auth.transport.requests import AuthorizedSession

_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
_LOGICAL_KEY_PATTERN = re.compile(r"^[A-Za-z0-9:._-]{1,160}$")


def cloud_run_job_trigger(*, project_id: str, region: str, job_name: str) -> Callable[[str], None]:
    if project_id != "sreality-scrapper-504307":
        raise ValueError("Cloud Run trigger requires the approved project")
    if region != "europe-west1":
        raise ValueError("Cloud Run trigger requires the approved region")
    if job_name != "sreality-tracker-scraper":
        raise ValueError("Cloud Run trigger requires the managed scraper job")

    endpoint = (
        f"https://run.googleapis.com/v2/projects/{project_id}/locations/{region}"
        f"/jobs/{job_name}:run"
    )

    def trigger(logical_key: str) -> None:
        if _LOGICAL_KEY_PATTERN.fullmatch(logical_key) is None:
            raise ValueError("logical key contains unsupported characters")
        credentials, _ = google.auth.default(scopes=[_CLOUD_PLATFORM_SCOPE])
        session = AuthorizedSession(credentials)  # type: ignore[no-untyped-call]
        try:
            response = session.post(
                endpoint,
                json={
                    "overrides": {
                        "containerOverrides": [
                            {
                                "name": "scraper",
                                "args": [
                                    "run",
                                    "--logical-key",
                                    logical_key,
                                    "--trigger",
                                    "manual",
                                ],
                            }
                        ]
                    }
                },
                timeout=20,
            )
            response.raise_for_status()
        finally:
            session.close()  # type: ignore[no-untyped-call]

    return trigger
