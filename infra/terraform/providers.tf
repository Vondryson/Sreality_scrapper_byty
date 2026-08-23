provider "google" {
  project               = var.project_id
  region                = var.region
  user_project_override = true

  default_labels = local.labels
}
