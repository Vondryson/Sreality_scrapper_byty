mock_provider "google" {
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
}
