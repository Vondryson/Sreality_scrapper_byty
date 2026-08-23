mock_provider "google" {
  override_during = plan
}

variables {
  workload_images = {
    api      = "europe-west1-docker.pkg.dev/sreality-scrapper-504307/sreality-tracker/api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    frontend = "europe-west1-docker.pkg.dev/sreality-scrapper-504307/sreality-tracker/frontend@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    scraper  = "europe-west1-docker.pkg.dev/sreality-scrapper-504307/sreality-tracker/scraper@sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
  }
}

run "keeps_cloud_run_within_mvp_guardrails" {
  command = apply

  assert {
    condition = (
      google_artifact_registry_repository.workloads.format == "DOCKER" &&
      one(google_artifact_registry_repository.workloads.docker_config).immutable_tags &&
      google_artifact_registry_repository.workloads.deletion_policy == "PREVENT"
    )
    error_message = "Artifact Registry must retain immutable, deletion-protected Docker images."
  }

  assert {
    condition = alltrue([
      google_cloud_run_v2_service.api[0].template[0].scaling[0].min_instance_count == 0,
      google_cloud_run_v2_service.frontend[0].template[0].scaling[0].min_instance_count == 0,
      google_cloud_run_v2_service.api[0].template[0].scaling[0].max_instance_count == 1,
      google_cloud_run_v2_service.frontend[0].template[0].scaling[0].max_instance_count == 1,
    ])
    error_message = "Both services must scale from zero and remain capped at one instance."
  }

  assert {
    condition = (
      google_cloud_run_v2_service.api[0].template[0].service_account == google_service_account.runtime["api"].email &&
      google_cloud_run_v2_service.frontend[0].template[0].service_account == google_service_account.runtime["frontend"].email &&
      google_cloud_run_v2_job.scraper[0].template[0].template[0].service_account == google_service_account.runtime["scraper"].email
    )
    error_message = "Every workload must use its dedicated runtime identity."
  }

  assert {
    condition = (
      google_cloud_run_v2_job.scraper[0].template[0].task_count == 1 &&
      google_cloud_run_v2_job.scraper[0].template[0].parallelism == 1 &&
      google_cloud_run_v2_job.scraper[0].template[0].template[0].max_retries == 0
    )
    error_message = "The scraper must run as one non-retrying task to prevent duplicate paid work."
  }

  assert {
    condition = (
      google_cloud_run_v2_service_iam_member.public_frontend[0].member == "allUsers" &&
      google_cloud_run_v2_service_iam_member.public_api_transport[0].member == "allUsers"
    )
    error_message = "Browser transport must reach the frontend and its application-authenticated API proxy target."
  }

  assert {
    condition = (
      google_cloud_scheduler_job.weekly_scrape[0].schedule == "0 3 * * 1" &&
      google_cloud_scheduler_job.weekly_scrape[0].time_zone == "Europe/Prague" &&
      length(google_cloud_scheduler_job.weekly_scrape[0].retry_config) == 0
    )
    error_message = "The authorized scraper schedule must run once on Monday at 03:00 Europe/Prague without retries."
  }

  assert {
    condition = toset(google_project_iam_custom_role.manual_job_runner[0].permissions) == toset([
      "run.jobs.run",
      "run.jobs.runWithOverrides",
    ])
    error_message = "The API manual runner role must contain only the two execution permissions."
  }

  assert {
    condition = (
      google_cloud_run_v2_job_iam_member.scheduler_runner[0].role == "roles/run.invoker" &&
      google_cloud_run_v2_job_iam_member.scheduler_runner[0].member == "serviceAccount:${google_service_account.scheduler[0].email}"
    )
    error_message = "Only the dedicated scheduler identity may invoke the weekly job."
  }
}
