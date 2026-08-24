resource "google_billing_budget" "production" {
  billing_account = var.billing_account_id
  display_name    = "Sreality Tracker production monthly budget"
  deletion_policy = "PREVENT"

  budget_filter {
    projects               = ["projects/${data.google_project.current.number}"]
    calendar_period        = "MONTH"
    credit_types_treatment = "INCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      currency_code = "CZK"
      units         = tostring(local.monthly_budget_czk)
    }
  }

  dynamic "threshold_rules" {
    for_each = toset(local.budget_alert_amounts_czk)

    content {
      threshold_percent = threshold_rules.value / local.monthly_budget_czk
      spend_basis       = "CURRENT_SPEND"
    }
  }

  all_updates_rule {
    monitoring_notification_channels = google_monitoring_notification_channel.email[*].name
    disable_default_iam_recipients   = var.monitoring_email != null
    enable_project_level_recipients  = var.monitoring_email == null
  }

  depends_on = [google_project_service.required["billingbudgets.googleapis.com"]]
}

# The existing production override is imported before the first M4-08 apply.
# Keeping it in Terraform prevents an accidental return to the unlimited default.
resource "google_service_usage_consumer_quota_override" "routes_daily_requests" {
  provider = google-beta

  project         = local.project_number
  service         = "routes.googleapis.com"
  metric          = urlencode("routes.googleapis.com/compute_routes_requests")
  limit           = urlencode("/d/project")
  override_value  = tostring(local.routes_daily_request_quota)
  force           = true
  deletion_policy = "PREVENT"

  depends_on = [
    google_project_service.required["routes.googleapis.com"],
    google_project_service.required["serviceusage.googleapis.com"],
  ]
}

# _Default already exists in every project and is imported before apply.
resource "google_logging_project_bucket_config" "default" {
  project         = "projects/${var.project_id}"
  location        = "global"
  bucket_id       = "_Default"
  retention_days  = local.default_log_retention_days
  deletion_policy = "PREVENT"

  depends_on = [google_project_service.required["logging.googleapis.com"]]
}
