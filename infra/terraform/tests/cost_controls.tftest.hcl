mock_provider "google" {
  override_during = plan
}

mock_provider "google-beta" {
  override_during = plan
}

variables {
  monitoring_email = "owner@example.com"
}

run "keeps_cost_controls_bounded_and_actionable" {
  command = plan

  assert {
    condition = (
      google_billing_budget.production.billing_account == "019FD9-252204-7DCB11" &&
      google_billing_budget.production.deletion_policy == "PREVENT" &&
      one(google_billing_budget.production.amount).specified_amount[0].currency_code == "CZK" &&
      one(google_billing_budget.production.amount).specified_amount[0].units == "300"
    )
    error_message = "The protected production budget must be scoped to the approved CZK billing account and capped at CZK 300 per month."
  }

  assert {
    condition = (
      length(google_billing_budget.production.threshold_rules) == 2 &&
      toset([
        for rule in google_billing_budget.production.threshold_rules :
        rule.threshold_percent * 300
      ]) == toset([200, 300]) &&
      alltrue([
        for rule in google_billing_budget.production.threshold_rules :
        rule.spend_basis == "CURRENT_SPEND"
      ])
    )
    error_message = "The monthly budget must alert on actual spend at exactly CZK 200 and CZK 300."
  }

  assert {
    condition = (
      length(one(google_billing_budget.production.all_updates_rule).monitoring_notification_channels) == 1 &&
      one(google_billing_budget.production.all_updates_rule).disable_default_iam_recipients
    )
    error_message = "Production budget notifications must use the explicitly configured owner e-mail channel without duplicate IAM-recipient mail."
  }

  assert {
    condition = (
      google_service_usage_consumer_quota_override.routes_daily_requests.project == "545468906541" &&
      google_service_usage_consumer_quota_override.routes_daily_requests.service == "routes.googleapis.com" &&
      google_service_usage_consumer_quota_override.routes_daily_requests.metric == "routes.googleapis.com%2Fcompute_routes_requests" &&
      google_service_usage_consumer_quota_override.routes_daily_requests.limit == "%2Fd%2Fproject" &&
      google_service_usage_consumer_quota_override.routes_daily_requests.override_value == "300" &&
      google_service_usage_consumer_quota_override.routes_daily_requests.deletion_policy == "PREVENT"
    )
    error_message = "ComputeRoutes must retain its protected project-wide limit of 300 requests per day."
  }

  assert {
    condition = (
      google_logging_project_bucket_config.default.bucket_id == "_Default" &&
      google_logging_project_bucket_config.default.project == "projects/sreality-scrapper-504307" &&
      google_logging_project_bucket_config.default.location == "global" &&
      google_logging_project_bucket_config.default.retention_days == 30 &&
      google_logging_project_bucket_config.default.deletion_policy == "PREVENT"
    )
    error_message = "The protected _Default log bucket must retain production logs for exactly 30 days."
  }

  assert {
    condition = contains(
      toset([for service in google_project_service.required : service.service]),
      "billingbudgets.googleapis.com",
    )
    error_message = "The Cloud Billing Budget API must be enabled declaratively."
  }
}
