locals {
  scraper_log_filter = <<-EOT
    resource.type="cloud_run_job"
    resource.labels.job_name="${local.name_prefix}-scraper"
  EOT

  scraper_counter_metrics = {
    scrape-successes = {
      description = "Completed successful scraper runs."
      filter      = "${local.scraper_log_filter}\njsonPayload.event=\"scrape_run_completed\"\njsonPayload.status=\"succeeded\""
    }
    scrape-failures = {
      description = "Failed, partial, or unexpectedly terminated scraper runs reported by the application."
      filter      = "${local.scraper_log_filter}\n(jsonPayload.event=\"scrape_run_failed\" OR (jsonPayload.event=\"scrape_run_completed\" AND jsonPayload.status!=\"succeeded\"))"
    }
    suspicious-listing-count = {
      description = "Successful scraper runs whose total result count is below the configured production threshold."
      filter      = "${local.scraper_log_filter}\njsonPayload.event=\"scrape_run_completed\"\njsonPayload.listing_count_below_threshold=true"
    }
    sreality-http-retries = {
      description = "Retries issued by the Sreality HTTP client."
      filter      = "${local.scraper_log_filter}\njsonPayload.event=\"http_retry\""
    }
    routes-requests = {
      description = "Requests sent to Google Routes by the scraper."
      filter      = "${local.scraper_log_filter}\njsonPayload.event=\"routes_request\""
    }
    routes-retries = {
      description = "Retries issued by the Google Routes client."
      filter      = "${local.scraper_log_filter}\njsonPayload.event=\"routes_retry\""
    }
  }

  scraper_run_distributions = {
    duration-seconds = {
      description = "End-to-end scraper run duration in seconds."
      field       = "duration_seconds"
      unit        = "s"
      scale       = 30
    }
    found-count = {
      description = "Listings found by a completed scraper run."
      field       = "found_count"
      unit        = "1"
      scale       = 1
    }
    new-count = {
      description = "New listings persisted by a completed scraper run."
      field       = "new_count"
      unit        = "1"
      scale       = 1
    }
    changed-count = {
      description = "Changed listings persisted by a completed scraper run."
      field       = "changed_count"
      unit        = "1"
      scale       = 1
    }
    deactivated-count = {
      description = "Listings deactivated by a completed scraper run."
      field       = "deactivated_count"
      unit        = "1"
      scale       = 1
    }
    error-count = {
      description = "Listing-level errors recorded by a completed scraper run."
      field       = "error_count"
      unit        = "1"
      scale       = 1
    }
  }
}

resource "google_logging_metric" "scraper_counter" {
  for_each = local.scraper_counter_metrics

  project     = var.project_id
  name        = "${local.name_prefix}-${each.key}"
  description = each.value.description
  filter      = each.value.filter

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }

  depends_on = [google_project_service.required["logging.googleapis.com"]]
}

resource "google_logging_metric" "scraper_run_distribution" {
  for_each = local.scraper_run_distributions

  project         = var.project_id
  name            = "${local.name_prefix}-${each.key}"
  description     = each.value.description
  filter          = "${local.scraper_log_filter}\njsonPayload.event=\"scrape_run_completed\""
  value_extractor = "EXTRACT(jsonPayload.${each.value.field})"

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "DISTRIBUTION"
    unit        = each.value.unit
  }

  bucket_options {
    exponential_buckets {
      num_finite_buckets = 16
      growth_factor      = 2
      scale              = each.value.scale
    }
  }

  depends_on = [google_project_service.required["logging.googleapis.com"]]
}

resource "google_logging_metric" "category_found_count" {
  project         = var.project_id
  name            = "${local.name_prefix}-category-found-count"
  description     = "Listings found by each completed Sreality category scrape."
  filter          = "${local.scraper_log_filter}\njsonPayload.event=\"category_scrape_completed\""
  value_extractor = "EXTRACT(jsonPayload.found_count)"
  label_extractors = {
    kind = "EXTRACT(jsonPayload.kind)"
  }

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "DISTRIBUTION"
    unit        = "1"

    labels {
      key         = "kind"
      value_type  = "STRING"
      description = "Listing category: chata or chalupa."
    }
  }

  bucket_options {
    exponential_buckets {
      num_finite_buckets = 16
      growth_factor      = 2
      scale              = 1
    }
  }

  depends_on = [google_project_service.required["logging.googleapis.com"]]
}

resource "google_monitoring_notification_channel" "email" {
  count = var.monitoring_email == null ? 0 : 1

  project      = var.project_id
  display_name = "Sreality Tracker owner e-mail"
  description  = "Production scraper incident notifications. The recipient must confirm the Google verification message."
  type         = "email"
  enabled      = true
  labels = {
    email_address = var.monitoring_email
  }

  force_delete = false

  depends_on = [google_project_service.required["monitoring.googleapis.com"]]
}

resource "google_monitoring_alert_policy" "scraper_application_failure" {
  count = var.monitoring_email == null ? 0 : 1

  project      = var.project_id
  display_name = "Sreality scraper: unsuccessful run"
  combiner     = "OR"
  enabled      = true

  documentation {
    content   = "The scraper reported a partial, failed, or bootstrap-error result. Inspect Cloud Run job logs and the scrape_runs record before retrying."
    mime_type = "text/markdown"
  }

  conditions {
    display_name = "Application failure event"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_job\" AND metric.type = \"logging.googleapis.com/user/${google_logging_metric.scraper_counter["scrape-failures"].name}\""
      comparison      = "COMPARISON_GT"
      duration        = "0s"
      threshold_value = 0

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  alert_strategy {
    auto_close = "86400s"
  }

  notification_channels = google_monitoring_notification_channel.email[*].name
}

resource "google_monitoring_alert_policy" "scraper_platform_failure" {
  count = var.monitoring_email == null ? 0 : 1

  project      = var.project_id
  display_name = "Sreality scraper: Cloud Run execution failed"
  combiner     = "OR"
  enabled      = true

  documentation {
    content   = "Cloud Run finished the scraper execution without success, including failures before the application could emit its final event. Inspect the execution logs and do not blindly retry paid work."
    mime_type = "text/markdown"
  }

  conditions {
    display_name = "Unsuccessful Cloud Run job execution"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_job\" AND resource.labels.job_name = \"${local.name_prefix}-scraper\" AND metric.type = \"run.googleapis.com/job/completed_execution_count\" AND metric.labels.result != \"succeeded\""
      comparison      = "COMPARISON_GT"
      duration        = "0s"
      threshold_value = 0

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  alert_strategy {
    auto_close = "86400s"
  }

  notification_channels = google_monitoring_notification_channel.email[*].name
}

resource "google_monitoring_alert_policy" "suspicious_listing_count" {
  count = var.monitoring_email == null ? 0 : 1

  project      = var.project_id
  display_name = "Sreality scraper: suspicious listing drop"
  combiner     = "OR"
  enabled      = true

  documentation {
    content   = "A technically successful run found fewer than ${var.minimum_expected_listing_count} listings. Treat this as a likely source/parser regression and inspect both category counts before deactivation or another run."
    mime_type = "text/markdown"
  }

  conditions {
    display_name = "Listing count below production threshold"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_job\" AND metric.type = \"logging.googleapis.com/user/${google_logging_metric.scraper_counter["suspicious-listing-count"].name}\""
      comparison      = "COMPARISON_GT"
      duration        = "0s"
      threshold_value = 0

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  alert_strategy {
    auto_close = "86400s"
  }

  notification_channels = google_monitoring_notification_channel.email[*].name
}

resource "google_monitoring_alert_policy" "cloud_sql_disk" {
  count = var.monitoring_email == null ? 0 : 1

  project      = var.project_id
  display_name = "Sreality database: disk utilization high"
  combiner     = "OR"
  enabled      = true

  documentation {
    content   = "Cloud SQL disk utilization stayed above 85%. Investigate growth before the configured 15 GiB autoresize ceiling is reached."
    mime_type = "text/markdown"
  }

  conditions {
    display_name = "Cloud SQL disk above 85%"

    condition_threshold {
      filter          = "resource.type = \"cloudsql_database\" AND resource.labels.database_id = \"${var.project_id}:${google_sql_database_instance.production.name}\" AND metric.type = \"cloudsql.googleapis.com/database/disk/utilization\""
      comparison      = "COMPARISON_GT"
      duration        = "900s"
      threshold_value = 0.85

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  alert_strategy {
    auto_close = "86400s"
  }

  notification_channels = google_monitoring_notification_channel.email[*].name
}

resource "google_monitoring_dashboard" "operations" {
  project = var.project_id

  dashboard_json = jsonencode({
    displayName = "Sreality Tracker operations"
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          width  = 6
          height = 4
          widget = {
            title = "Scraper runs"
            xyChart = {
              dataSets = [
                for metric_name in ["scrape-successes", "scrape-failures"] : {
                  plotType = "LINE"
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloud_run_job\" AND metric.type=\"logging.googleapis.com/user/${google_logging_metric.scraper_counter[metric_name].name}\""
                      aggregation = {
                        alignmentPeriod  = "3600s"
                        perSeriesAligner = "ALIGN_SUM"
                      }
                    }
                  }
                }
              ]
              yAxis = {
                label = "runs"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          width  = 6
          height = 4
          widget = {
            title = "Run duration (p95)"
            xyChart = {
              dataSets = [{
                plotType = "LINE"
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_job\" AND metric.type=\"logging.googleapis.com/user/${google_logging_metric.scraper_run_distribution["duration-seconds"].name}\""
                    aggregation = {
                      alignmentPeriod  = "3600s"
                      perSeriesAligner = "ALIGN_PERCENTILE_95"
                    }
                  }
                }
              }]
              yAxis = {
                label = "seconds"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          width  = 12
          height = 4
          widget = {
            title = "Listings per completed run"
            xyChart = {
              dataSets = [
                for metric_name in ["found-count", "new-count", "changed-count", "deactivated-count", "error-count"] : {
                  plotType = "LINE"
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloud_run_job\" AND metric.type=\"logging.googleapis.com/user/${google_logging_metric.scraper_run_distribution[metric_name].name}\""
                      aggregation = {
                        alignmentPeriod  = "3600s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                }
              ]
              yAxis = {
                label = "listings"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          width  = 6
          height = 4
          widget = {
            title = "HTTP and Routes activity"
            xyChart = {
              dataSets = [
                for metric_name in ["sreality-http-retries", "routes-requests", "routes-retries"] : {
                  plotType = "LINE"
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloud_run_job\" AND metric.type=\"logging.googleapis.com/user/${google_logging_metric.scraper_counter[metric_name].name}\""
                      aggregation = {
                        alignmentPeriod  = "3600s"
                        perSeriesAligner = "ALIGN_SUM"
                      }
                    }
                  }
                }
              ]
              yAxis = {
                label = "events"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          width  = 6
          height = 4
          widget = {
            title = "Cloud SQL utilization"
            xyChart = {
              dataSets = [
                for metric_type in ["cpu/utilization", "disk/utilization"] : {
                  plotType = "LINE"
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloudsql_database\" AND metric.type=\"cloudsql.googleapis.com/database/${metric_type}\""
                      aggregation = {
                        alignmentPeriod  = "300s"
                        perSeriesAligner = "ALIGN_MEAN"
                      }
                    }
                  }
                }
              ]
              yAxis = {
                label = "ratio"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          width  = 12
          height = 4
          widget = {
            title = "Application Storage size and object count"
            xyChart = {
              dataSets = [
                for metric_type in ["total_bytes", "object_count"] : {
                  plotType = "LINE"
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"gcs_bucket\" AND resource.labels.bucket_name=\"${google_storage_bucket.application_data.name}\" AND metric.type=\"storage.googleapis.com/storage/${metric_type}\""
                      aggregation = {
                        alignmentPeriod    = "86400s"
                        perSeriesAligner   = "ALIGN_MEAN"
                        crossSeriesReducer = "REDUCE_SUM"
                        groupByFields      = ["resource.labels.bucket_name"]
                      }
                    }
                  }
                }
              ]
              yAxis = {
                label = "bytes / objects"
                scale = "LOG10"
              }
            }
          }
        }
      ]
    }
  })

  depends_on = [google_project_service.required["monitoring.googleapis.com"]]
}
