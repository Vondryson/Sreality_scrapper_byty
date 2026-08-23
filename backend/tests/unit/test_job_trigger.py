from __future__ import annotations

from unittest.mock import Mock

import pytest

from sreality_tracker.api import job_trigger


def test_cloud_run_trigger_uses_authenticated_per_execution_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credentials = object()
    response = Mock()
    session = Mock()
    session.post.return_value = response
    default = Mock(return_value=(credentials, "sreality-scrapper-504307"))
    authorized_session = Mock(return_value=session)
    monkeypatch.setattr(job_trigger.google.auth, "default", default)
    monkeypatch.setattr(job_trigger, "AuthorizedSession", authorized_session)
    trigger = job_trigger.cloud_run_job_trigger(
        project_id="sreality-scrapper-504307",
        region="europe-west1",
        job_name="sreality-tracker-scraper",
    )

    trigger("manual:owner-20260823")

    default.assert_called_once_with(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    authorized_session.assert_called_once_with(credentials)
    session.post.assert_called_once_with(
        "https://run.googleapis.com/v2/projects/sreality-scrapper-504307/locations/"
        "europe-west1/jobs/sreality-tracker-scraper:run",
        json={
            "overrides": {
                "containerOverrides": [
                    {
                        "name": "scraper",
                        "args": [
                            "run",
                            "--logical-key",
                            "manual:owner-20260823",
                            "--trigger",
                            "manual",
                        ],
                    }
                ]
            }
        },
        timeout=20,
    )
    response.raise_for_status.assert_called_once_with()
    session.close.assert_called_once_with()


def test_cloud_run_trigger_rejects_untrusted_target_and_logical_key() -> None:
    with pytest.raises(ValueError, match="approved project"):
        job_trigger.cloud_run_job_trigger(
            project_id="maiven-lab-dev",
            region="europe-west1",
            job_name="sreality-tracker-scraper",
        )

    trigger = job_trigger.cloud_run_job_trigger(
        project_id="sreality-scrapper-504307",
        region="europe-west1",
        job_name="sreality-tracker-scraper",
    )
    with pytest.raises(ValueError, match="unsupported characters"):
        trigger("manual:invalid key")
