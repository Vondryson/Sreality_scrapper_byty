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
