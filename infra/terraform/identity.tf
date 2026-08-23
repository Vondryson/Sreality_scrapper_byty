resource "google_service_account" "runtime" {
  for_each = local.runtime_service_accounts

  account_id   = "${local.name_prefix}-${each.key}"
  project      = var.project_id
  display_name = each.value.display_name
  description  = each.value.description

  depends_on = [google_project_service.required["iam.googleapis.com"]]
}

resource "google_project_iam_member" "runtime" {
  for_each = local.project_iam_grants

  project = var.project_id
  role    = each.value.role
  member  = "serviceAccount:${google_service_account.runtime[each.value.service].email}"
}

resource "google_storage_bucket_iam_member" "runtime" {
  for_each = local.storage_iam_grants

  bucket = google_storage_bucket.application_data.name
  role   = each.value.role
  member = "serviceAccount:${google_service_account.runtime[each.value.service].email}"
}
