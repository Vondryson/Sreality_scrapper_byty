locals {
  name_prefix    = "sreality-tracker"
  project_number = "545468906541"

  labels = {
    application = "sreality-tracker"
    environment = var.environment
    managed_by  = "terraform"
  }

  monthly_budget_czk         = 300
  budget_alert_amounts_czk   = [200, 300]
  routes_daily_request_quota = 300
  default_log_retention_days = 30

  required_services = toset([
    "artifactregistry.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "routes.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "serviceusage.googleapis.com",
    "sqladmin.googleapis.com",
    "storage.googleapis.com",
  ])

  runtime_service_accounts = {
    api = {
      display_name = "Sreality API runtime"
      description  = "Identity used only by the private FastAPI Cloud Run service."
    }
    frontend = {
      display_name = "Sreality frontend runtime"
      description  = "Identity used only by the public login/frontend Cloud Run service."
    }
    scraper = {
      display_name = "Sreality scraper runtime"
      description  = "Identity used only by the scheduled scraper Cloud Run job."
    }
  }

  project_iam_grants = {
    api_cloud_sql = {
      service = "api"
      role    = "roles/cloudsql.client"
    }
    scraper_cloud_sql = {
      service = "scraper"
      role    = "roles/cloudsql.client"
    }
    scraper_service_usage = {
      service = "scraper"
      role    = "roles/serviceusage.serviceUsageConsumer"
    }
  }

  storage_iam_grants = {
    api_create = {
      service = "api"
      role    = "roles/storage.objectCreator"
    }
    api_read = {
      service = "api"
      role    = "roles/storage.objectViewer"
    }
    scraper_create = {
      service = "scraper"
      role    = "roles/storage.objectCreator"
    }
    scraper_read = {
      service = "scraper"
      role    = "roles/storage.objectViewer"
    }
  }

  runtime_secrets = toset([
    "database-url",
    "google-oauth-client-id",
    "google-oauth-client-secret",
    "owner-email",
    "session-secret",
  ])

  secret_access_grants = {
    api_database = {
      service = "api"
      secret  = "database-url"
    }
    api_oauth_client_id = {
      service = "api"
      secret  = "google-oauth-client-id"
    }
    api_oauth_client_secret = {
      service = "api"
      secret  = "google-oauth-client-secret"
    }
    api_owner_email = {
      service = "api"
      secret  = "owner-email"
    }
    api_session_secret = {
      service = "api"
      secret  = "session-secret"
    }
    scraper_database = {
      service = "scraper"
      secret  = "database-url"
    }
  }
}
