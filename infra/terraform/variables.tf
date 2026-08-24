variable "project_id" {
  description = "Dedicated personal Google Cloud project for Sreality Tracker."
  type        = string
  default     = "sreality-scrapper-504307"

  validation {
    condition     = var.project_id == "sreality-scrapper-504307"
    error_message = "This stack may only target sreality-scrapper-504307."
  }
}

variable "region" {
  description = "Primary region for all supported regional resources."
  type        = string
  default     = "europe-west1"

  validation {
    condition     = var.region == "europe-west1"
    error_message = "The approved production region is europe-west1."
  }
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "production"

  validation {
    condition     = var.environment == "production"
    error_message = "This cost-constrained stack manages production only."
  }
}

variable "workload_images" {
  description = "Immutable Artifact Registry image references used by the Cloud Run workloads; null bootstraps the registry only."
  type = object({
    api      = string
    frontend = string
    scraper  = string
  })
  default  = null
  nullable = true

  validation {
    condition = var.workload_images == null || alltrue([
      for image in values(var.workload_images) :
      can(regex("^${var.region}-docker\\.pkg\\.dev/${var.project_id}/sreality-tracker/[a-z0-9-]+@sha256:[0-9a-f]{64}$", image))
    ])
    error_message = "Every workload image must be an immutable sha256 reference in the managed sreality-tracker repository."
  }
}

variable "billing_account_id" {
  description = "Billing account attached to the dedicated personal project; the identifier is not a credential."
  type        = string
  default     = "019FD9-252204-7DCB11"

  validation {
    condition     = var.billing_account_id == "019FD9-252204-7DCB11"
    error_message = "This stack may only manage the approved personal billing account."
  }
}

variable "monitoring_email" {
  description = "Optional e-mail address for scraper incident alerts; set explicitly for production."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition = (
      var.monitoring_email == null ||
      can(regex("^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$", var.monitoring_email))
    )
    error_message = "monitoring_email must be null or a valid normalized e-mail address."
  }
}

variable "minimum_expected_listing_count" {
  description = "Successful full scraper runs below this listing count are treated as suspicious."
  type        = number
  default     = 2500

  validation {
    condition = (
      var.minimum_expected_listing_count >= 1 &&
      var.minimum_expected_listing_count <= 10000 &&
      floor(var.minimum_expected_listing_count) == var.minimum_expected_listing_count
    )
    error_message = "minimum_expected_listing_count must be a whole number between 1 and 10000."
  }
}
