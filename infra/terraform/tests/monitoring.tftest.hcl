mock_provider "google" {
  override_during = plan
}

mock_provider "google-beta" {
  override_during = plan
}

variables {
  monitoring_email = "owner@example.com"
  workload_images = {
    api      = "europe-west1-docker.pkg.dev/sreality-scrapper-504307/sreality-tracker/api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    frontend = "europe-west1-docker.pkg.dev/sreality-scrapper-504307/sreality-tracker/frontend@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    scraper  = "europe-west1-docker.pkg.dev/sreality-scrapper-504307/sreality-tracker/scraper@sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
  }
}

run "keeps_monitoring_actionable_and_bounded" {
  command = plan

  assert {
    condition = (
      length(google_logging_metric.scraper_counter) == 6 &&
      length(google_logging_metric.scraper_run_distribution) == 6 &&
      google_logging_metric.category_found_count.metric_descriptor[0].value_type == "DISTRIBUTION"
    )
    error_message = "Monitoring must retain the bounded scraper outcome, count, duration, retry, Routes, and per-category metrics."
  }

  assert {
    condition = (
      google_monitoring_notification_channel.email[0].type == "email" &&
      google_monitoring_notification_channel.email[0].labels.email_address == "owner@example.com" &&
      google_monitoring_notification_channel.email[0].force_delete == false
    )
    error_message = "The production notification channel must be an explicitly configured, deletion-safe e-mail channel."
  }

  assert {
    condition = (
      length(google_monitoring_alert_policy.scraper_application_failure) == 1 &&
      length(google_monitoring_alert_policy.scraper_platform_failure) == 1 &&
      length(google_monitoring_alert_policy.suspicious_listing_count) == 1 &&
      length(google_monitoring_alert_policy.cloud_sql_disk) == 1
    )
    error_message = "Application, platform, suspicious-count, and database disk incidents must all have alert policies."
  }

  assert {
    condition = alltrue([
      google_monitoring_alert_policy.scraper_application_failure[0].enabled,
      google_monitoring_alert_policy.scraper_platform_failure[0].enabled,
      google_monitoring_alert_policy.suspicious_listing_count[0].enabled,
      google_monitoring_alert_policy.cloud_sql_disk[0].enabled,
    ])
    error_message = "All M4-07 incident policies must be enabled."
  }

  assert {
    condition = alltrue([
      length(google_monitoring_alert_policy.scraper_application_failure[0].alert_strategy[0].notification_rate_limit) == 0,
      length(google_monitoring_alert_policy.scraper_platform_failure[0].alert_strategy[0].notification_rate_limit) == 0,
      length(google_monitoring_alert_policy.suspicious_listing_count[0].alert_strategy[0].notification_rate_limit) == 0,
      length(google_monitoring_alert_policy.cloud_sql_disk[0].alert_strategy[0].notification_rate_limit) == 0,
    ])
    error_message = "Metric-threshold policies must not use the log-match-only notification rate limit."
  }

  assert {
    condition = one([
      for environment in google_cloud_run_v2_job.scraper[0].template[0].template[0].containers[0].env :
      environment.value
      if environment.name == "SREALITY_MONITORING_MINIMUM_LISTING_COUNT"
    ]) == "2500"
    error_message = "The production scraper must receive the guarded suspicious-listing threshold."
  }

  assert {
    condition = (
      strcontains(google_monitoring_dashboard.operations.dashboard_json, "Sreality Tracker operations") &&
      strcontains(google_monitoring_dashboard.operations.dashboard_json, "Cloud SQL utilization") &&
      strcontains(google_monitoring_dashboard.operations.dashboard_json, "Application Storage size and object count")
    )
    error_message = "The operations dashboard must cover scraper, database, and storage health."
  }


  assert {
    condition = (
      !strcontains(google_monitoring_dashboard.operations.dashboard_json, "\"x\":") &&
      !strcontains(google_monitoring_dashboard.operations.dashboard_json, "\"y\":") &&
      !strcontains(google_monitoring_dashboard.operations.dashboard_json, "\"xPos\":0") &&
      !strcontains(google_monitoring_dashboard.operations.dashboard_json, "\"yPos\":0") &&
      strcontains(google_monitoring_dashboard.operations.dashboard_json, "\"xPos\":") &&
      strcontains(google_monitoring_dashboard.operations.dashboard_json, "\"yPos\":") &&
      strcontains(google_monitoring_dashboard.operations.dashboard_json, "\"targetAxis\":\"Y1\"")
    )
    error_message = "Dashboard JSON must match API-normalized positions and target axes."
  }
}
