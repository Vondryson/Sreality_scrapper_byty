resource "google_storage_bucket" "application_data" {
  name                        = "${var.project_id}-application-data"
  project                     = var.project_id
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  soft_delete_policy {
    retention_duration_seconds = 604800
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age            = 90
      matches_prefix = ["raw/"]
    }
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.required["storage.googleapis.com"]]
}
