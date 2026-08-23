resource "google_service_account" "scheduler" {
  count = var.workload_images == null ? 0 : 1

  project      = var.project_id
  account_id   = "${local.name_prefix}-scheduler"
  display_name = "Sreality weekly scheduler"
  description  = "Identity allowed only to execute the managed scraper Cloud Run job."

  depends_on = [google_project_service.required["iam.googleapis.com"]]
}

resource "google_project_iam_custom_role" "manual_job_runner" {
  count = var.workload_images == null ? 0 : 1

  project     = var.project_id
  role_id     = "srealityManualJobRunner"
  title       = "Sreality manual job runner"
  description = "Run the managed scraper job with an owner-supplied per-execution logical key."
  stage       = "GA"
  permissions = [
    "run.jobs.run",
    "run.jobs.runWithOverrides",
  ]
}

resource "google_cloud_run_v2_job_iam_member" "api_manual_runner" {
  count = var.workload_images == null ? 0 : 1

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.scraper[0].name
  role     = google_project_iam_custom_role.manual_job_runner[0].name
  member   = "serviceAccount:${google_service_account.runtime["api"].email}"
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_runner" {
  count = var.workload_images == null ? 0 : 1

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.scraper[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler[0].email}"
}

resource "google_cloud_scheduler_job" "weekly_scrape" {
  count = var.workload_images == null ? 0 : 1

  project          = var.project_id
  region           = var.region
  name             = "${local.name_prefix}-weekly"
  description      = "Execute the scraper every Monday at 03:00 Europe/Prague."
  schedule         = "0 3 * * 1"
  time_zone        = "Europe/Prague"
  attempt_deadline = "30s"
  paused           = false

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.scraper[0].name}:run"
    body        = base64encode("{}")

    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = google_service_account.scheduler[0].email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  depends_on = [
    google_cloud_run_v2_job_iam_member.scheduler_runner,
    google_project_service.required["cloudscheduler.googleapis.com"],
  ]
}
