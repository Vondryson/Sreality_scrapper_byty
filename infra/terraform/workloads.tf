resource "google_artifact_registry_repository" "workloads" {
  project         = var.project_id
  location        = var.region
  repository_id   = local.name_prefix
  description     = "Immutable production images for Sreality Tracker Cloud Run workloads."
  format          = "DOCKER"
  mode            = "STANDARD_REPOSITORY"
  labels          = local.labels
  deletion_policy = "PREVENT"

  docker_config {
    immutable_tags = true
  }

  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"

    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-old-untagged"
    action = "DELETE"

    condition {
      tag_state  = "UNTAGGED"
      older_than = "1209600s"
    }
  }

  depends_on = [google_project_service.required["artifactregistry.googleapis.com"]]
}

resource "google_cloud_run_v2_service" "frontend" {
  count = var.workload_images == null ? 0 : 1

  project             = var.project_id
  location            = var.region
  name                = "${local.name_prefix}-frontend"
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = true
  labels              = local.labels

  template {
    service_account                  = google_service_account.runtime["frontend"].email
    timeout                          = "60s"
    max_instance_request_concurrency = 40

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      name  = "frontend"
      image = var.workload_images == null ? "" : var.workload_images.frontend

      ports {
        name           = "http1"
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      startup_probe {
        initial_delay_seconds = 0
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 12

        http_get {
          path = "/"
          port = 8080
        }
      }

      liveness_probe {
        initial_delay_seconds = 10
        timeout_seconds       = 3
        period_seconds        = 30
        failure_threshold     = 3

        http_get {
          path = "/"
          port = 8080
        }
      }
    }
  }

  depends_on = [google_project_service.required["run.googleapis.com"]]
}

resource "google_cloud_run_v2_service" "api" {
  count = var.workload_images == null ? 0 : 1

  project             = var.project_id
  location            = var.region
  name                = "${local.name_prefix}-api"
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = true
  labels              = local.labels

  template {
    service_account                  = google_service_account.runtime["api"].email
    timeout                          = "60s"
    max_instance_request_concurrency = 20

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      name  = "api"
      image = var.workload_images == null ? "" : var.workload_images.api

      ports {
        name           = "http1"
        container_port = 8080
      }

      env {
        name  = "SREALITY_ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "SREALITY_STORAGE_BACKEND"
        value = "gcs"
      }
      env {
        name  = "SREALITY_GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "SREALITY_CLOUD_RUN_REGION"
        value = var.region
      }
      env {
        name  = "SREALITY_SCRAPER_JOB_NAME"
        value = google_cloud_run_v2_job.scraper[0].name
      }
      env {
        name  = "SREALITY_STORAGE_BUCKET"
        value = google_storage_bucket.application_data.name
      }
      env {
        name  = "SREALITY_FRONTEND_URL"
        value = google_cloud_run_v2_service.frontend[0].uri
      }
      env {
        name  = "SREALITY_GOOGLE_OAUTH_REDIRECT_URI"
        value = "${google_cloud_run_v2_service.frontend[0].uri}/api/v1/auth/google/callback"
      }

      dynamic "env" {
        for_each = {
          SREALITY_DATABASE_URL               = "database-url"
          SREALITY_GOOGLE_OAUTH_CLIENT_ID     = "google-oauth-client-id"
          SREALITY_GOOGLE_OAUTH_CLIENT_SECRET = "google-oauth-client-secret"
          SREALITY_OWNER_EMAIL                = "owner-email"
          SREALITY_SESSION_SECRET             = "session-secret"
        }
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.runtime[env.value].secret_id
              version = "latest"
            }
          }
        }
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      startup_probe {
        initial_delay_seconds = 0
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 20

        http_get {
          path = "/api/v1/health/live"
          port = 8080
        }
      }

      liveness_probe {
        initial_delay_seconds = 10
        timeout_seconds       = 3
        period_seconds        = 30
        failure_threshold     = 3

        http_get {
          path = "/api/v1/health/live"
          port = 8080
        }
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.production.connection_name]
      }
    }
  }

  depends_on = [google_project_service.required["run.googleapis.com"]]
}

# Cloud Run accepts browser traffic, while FastAPI requires the signed owner
# session for all listing, note, favorite and operational endpoints.
resource "google_cloud_run_v2_service_iam_member" "public_frontend" {
  count = var.workload_images == null ? 0 : 1

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "public_api_transport" {
  count = var.workload_images == null ? 0 : 1

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_job" "scraper" {
  count = var.workload_images == null ? 0 : 1

  project             = var.project_id
  location            = var.region
  name                = "${local.name_prefix}-scraper"
  deletion_protection = true
  labels              = local.labels

  template {
    task_count  = 1
    parallelism = 1

    template {
      service_account = google_service_account.runtime["scraper"].email
      timeout         = "10800s"
      max_retries     = 0

      containers {
        name    = "scraper"
        image   = var.workload_images == null ? "" : var.workload_images.scraper
        command = ["sreality-scrape"]
        args    = ["run", "--trigger", "scheduled"]

        env {
          name  = "SREALITY_ENVIRONMENT"
          value = var.environment
        }
        env {
          name  = "SREALITY_STORAGE_BACKEND"
          value = "gcs"
        }
        env {
          name  = "SREALITY_GCP_PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "SREALITY_STORAGE_BUCKET"
          value = google_storage_bucket.application_data.name
        }
        env {
          name = "SREALITY_DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.runtime["database-url"].secret_id
              version = "latest"
            }
          }
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.production.connection_name]
        }
      }
    }
  }

  depends_on = [google_project_service.required["run.googleapis.com"]]
}
