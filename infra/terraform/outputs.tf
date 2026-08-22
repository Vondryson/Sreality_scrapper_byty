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
