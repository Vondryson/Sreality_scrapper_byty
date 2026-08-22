resource "google_sql_database_instance" "production" {
  name             = "${local.name_prefix}-postgres"
  project          = var.project_id
  region           = var.region
  database_version = "POSTGRES_16"

  deletion_protection = true

  settings {
    tier              = "db-f1-micro"
    edition           = "ENTERPRISE"
    availability_type = "ZONAL"

    disk_type             = "PD_SSD"
    disk_size             = 10
    disk_autoresize       = true
    disk_autoresize_limit = 15

    deletion_protection_enabled = true
    connector_enforcement       = "REQUIRED"

    ip_configuration {
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "00:00"
      location                       = var.region
      point_in_time_recovery_enabled = false

      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    maintenance_window {
      day          = 7
      hour         = 1
      update_track = "stable"
    }
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [settings[0].disk_size]
  }

  depends_on = [google_project_service.required["sqladmin.googleapis.com"]]
}

resource "google_sql_database" "application" {
  name            = "sreality_tracker"
  project         = var.project_id
  instance        = google_sql_database_instance.production.name
  charset         = "UTF8"
  deletion_policy = "ABANDON"
}
