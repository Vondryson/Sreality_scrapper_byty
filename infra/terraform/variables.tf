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
