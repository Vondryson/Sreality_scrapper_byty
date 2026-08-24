mock_provider "google" {
  override_during = plan
}

mock_provider "google-beta" {
  override_during = plan
}

run "keeps_data_foundation_within_mvp_guardrails" {
  command = plan

  assert {
    condition     = google_sql_database_instance.production.settings[0].tier == "db-f1-micro"
    error_message = "Cloud SQL must use the approved db-f1-micro tier."
  }

  assert {
    condition     = google_sql_database_instance.production.settings[0].availability_type == "ZONAL"
    error_message = "Cloud SQL HA is outside the approved MVP budget."
  }

  assert {
    condition     = google_sql_database_instance.production.settings[0].disk_size == 10
    error_message = "Cloud SQL must start with the 10 GiB minimum SSD disk."
  }

  assert {
    condition     = google_sql_database_instance.production.settings[0].disk_autoresize_limit == 15
    error_message = "Cloud SQL automatic growth must stop at 15 GiB."
  }

  assert {
    condition     = google_sql_database_instance.production.settings[0].connector_enforcement == "REQUIRED"
    error_message = "Cloud SQL must reject connections outside an authenticated connector."
  }

  assert {
    condition = (
      google_sql_database_instance.production.deletion_protection &&
      google_sql_database_instance.production.settings[0].deletion_protection_enabled
    )
    error_message = "Cloud SQL must retain both Terraform and API deletion protection."
  }

  assert {
    condition = (
      one(google_sql_database_instance.production.settings[0].backup_configuration).enabled &&
      !one(google_sql_database_instance.production.settings[0].backup_configuration).point_in_time_recovery_enabled &&
      one(one(google_sql_database_instance.production.settings[0].backup_configuration).backup_retention_settings).retained_backups == 7
    )
    error_message = "Cloud SQL must retain seven daily backups without budget-expanding PITR."
  }

  assert {
    condition     = google_storage_bucket.application_data.location == "europe-west1"
    error_message = "Application data must remain in the approved single region."
  }

  assert {
    condition     = google_storage_bucket.application_data.public_access_prevention == "enforced"
    error_message = "The application bucket must prevent public access."
  }

  assert {
    condition = (
      google_storage_bucket.application_data.uniform_bucket_level_access &&
      !google_storage_bucket.application_data.force_destroy &&
      one(google_storage_bucket.application_data.soft_delete_policy).retention_duration_seconds == 604800
    )
    error_message = "The application bucket must retain private access and recovery guardrails."
  }

  assert {
    condition     = one(one(google_storage_bucket.application_data.lifecycle_rule).condition).age == 90
    error_message = "Raw payloads must expire after 90 days."
  }

  assert {
    condition = (
      length(one(one(google_storage_bucket.application_data.lifecycle_rule).condition).matches_prefix) == 1 &&
      contains(one(one(google_storage_bucket.application_data.lifecycle_rule).condition).matches_prefix, "raw/")
    )
    error_message = "The 90-day lifecycle must only target raw payloads."
  }

  assert {
    condition = toset(values(google_service_account.runtime)[*].account_id) == toset([
      "sreality-tracker-api",
      "sreality-tracker-frontend",
      "sreality-tracker-scraper",
    ])
    error_message = "Every Cloud Run workload must have its own runtime identity."
  }

  assert {
    condition = toset(values(google_project_iam_member.runtime)[*].role) == toset([
      "roles/cloudsql.client",
      "roles/serviceusage.serviceUsageConsumer",
    ])
    error_message = "Runtime project roles must remain limited to Cloud SQL and API consumption."
  }

  assert {
    condition = toset(values(google_storage_bucket_iam_member.runtime)[*].role) == toset([
      "roles/storage.objectCreator",
      "roles/storage.objectViewer",
    ])
    error_message = "Runtime bucket access must not include object deletion or bucket administration."
  }

  assert {
    condition = toset(keys(google_secret_manager_secret.runtime)) == toset([
      "database-url",
      "google-oauth-client-id",
      "google-oauth-client-secret",
      "owner-email",
      "session-secret",
    ])
    error_message = "Terraform must create exactly the approved empty runtime secret containers."
  }

  assert {
    condition = alltrue([
      for secret in values(google_secret_manager_secret.runtime) :
      one(one(one(secret.replication).user_managed).replicas).location == "europe-west1"
    ])
    error_message = "Runtime secrets must use only the approved regional replication location."
  }

  assert {
    condition = (
      length(google_secret_manager_secret_iam_member.runtime) == 6 &&
      alltrue([
        for grant in values(google_secret_manager_secret_iam_member.runtime) :
        grant.role == "roles/secretmanager.secretAccessor"
      ])
    )
    error_message = "Only the six explicit runtime secret accessor grants are allowed."
  }
}
