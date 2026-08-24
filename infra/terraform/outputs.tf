output "project" {
  description = "Validated target project metadata."
  value = {
    id     = data.google_project.current.project_id
    number = data.google_project.current.number
  }
}

output "region" {
  description = "Approved primary region."
  value       = var.region
}

output "labels" {
  description = "Default labels inherited by supported resources."
  value       = local.labels
}

output "cloud_sql" {
  description = "Non-secret connection metadata for the production PostgreSQL instance."
  value = {
    connection_name = google_sql_database_instance.production.connection_name
    database_name   = google_sql_database.application.name
    instance_name   = google_sql_database_instance.production.name
  }
}

output "application_storage" {
  description = "Private shared bucket and stable object prefixes used by application adapters."
  value = {
    bucket_name           = google_storage_bucket.application_data.name
    favorite_image_prefix = "favorite-images/"
    raw_payload_prefix    = "raw/"
  }
}

output "runtime_service_accounts" {
  description = "Dedicated least-privilege identities attached to Cloud Run workloads."
  value = {
    for name, account in google_service_account.runtime : name => account.email
  }
}

output "runtime_secret_ids" {
  description = "Empty Secret Manager containers that must be populated outside Terraform."
  value = {
    for name, secret in google_secret_manager_secret.runtime : name => secret.secret_id
  }
}

output "artifact_registry" {
  description = "Docker repository used for immutable production workload images."
  value = {
    repository_id = google_artifact_registry_repository.workloads.repository_id
    registry_uri  = google_artifact_registry_repository.workloads.registry_uri
  }
}

output "cloud_run" {
  description = "Cloud Run endpoints and scraper job name; null until workload_images are supplied."
  value = var.workload_images == null ? null : {
    api_uri      = google_cloud_run_v2_service.api[0].uri
    frontend_uri = google_cloud_run_v2_service.frontend[0].uri
    scraper_job  = google_cloud_run_v2_job.scraper[0].name
  }
}

output "scheduler" {
  description = "Weekly scraper schedule and its dedicated invocation identity."
  value = var.workload_images == null ? null : {
    job_name              = google_cloud_scheduler_job.weekly_scrape[0].name
    schedule              = google_cloud_scheduler_job.weekly_scrape[0].schedule
    time_zone             = google_cloud_scheduler_job.weekly_scrape[0].time_zone
    service_account_email = google_service_account.scheduler[0].email
  }
}

output "monitoring" {
  description = "Monitoring resources; alert channels and policies are created only when monitoring_email is set."
  value = {
    dashboard_id = google_monitoring_dashboard.operations.id
    email_channel = (
      var.monitoring_email == null
      ? null
      : google_monitoring_notification_channel.email[0].name
    )
    alert_policy_names = var.monitoring_email == null ? [] : [
      google_monitoring_alert_policy.scraper_application_failure[0].name,
      google_monitoring_alert_policy.scraper_platform_failure[0].name,
      google_monitoring_alert_policy.suspicious_listing_count[0].name,
      google_monitoring_alert_policy.cloud_sql_disk[0].name,
    ]
    minimum_expected_listing_count = var.minimum_expected_listing_count
  }
}

output "cost_controls" {
  description = "Production budget, external API quota, and log-retention guardrails."
  value = {
    billing_budget_name        = google_billing_budget.production.name
    budget_amount_czk          = local.monthly_budget_czk
    budget_alert_amounts_czk   = local.budget_alert_amounts_czk
    routes_daily_request_cap   = local.routes_daily_request_quota
    default_log_retention_days = google_logging_project_bucket_config.default.retention_days
  }
}
