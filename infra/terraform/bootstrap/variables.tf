variable "project_id" {
  type    = string
  default = "sreality-scrapper-504307"

  validation {
    condition     = var.project_id == "sreality-scrapper-504307"
    error_message = "State bootstrap may only target sreality-scrapper-504307."
  }
}

variable "region" {
  type    = string
  default = "europe-west1"

  validation {
    condition     = var.region == "europe-west1"
    error_message = "The approved state bucket region is europe-west1."
  }
}
