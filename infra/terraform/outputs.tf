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
