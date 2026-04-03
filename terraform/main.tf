# Terraform configuration for GitHub Activity Batch Pipeline
# Creates GCS bucket and BigQuery partitioned/clustered table

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "europe-west1"
}

variable "bucket_name" {
  description = "GCS Bucket name for raw GitHub data"
  type        = string
  default     = "github-activity-batch-raw"
}

variable "bq_dataset" {
  description = "BigQuery Dataset name"
  type        = string
  default     = "github_activity"
}

variable "bq_table" {
  description = "BigQuery Table name"
  type        = string
  default     = "github_events"
}

# GCS Bucket for raw GitHub activity data
resource "google_storage_bucket" "raw_data" {
  name          = "${var.bucket_name}-${var.project_id}"
  location      = var.region
  force_destroy = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  uniform_bucket_level_access = true
}

# BigQuery Dataset
resource "google_bigquery_dataset" "github" {
  dataset_id    = var.bq_dataset
  friendly_name = "GitHub Activity Data"
  description   = "Dataset for storing GitHub activity events"
  location      = var.region
}

# BigQuery Table - Partitioned by event date, Clustered by repo and actor
resource "google_bigquery_table" "github_events" {
  dataset_id = google_bigquery_dataset.github.dataset_id
  table_id   = var.bq_table

  schema = <<EOF
[
  {"name": "event_id", "type": "STRING", "mode": "REQUIRED"},
  {"name": "event_type", "type": "STRING", "mode": "REQUIRED"},
  {"name": "actor_login", "type": "STRING", "mode": "REQUIRED"},
  {"name": "repo_name", "type": "STRING", "mode": "REQUIRED"},
  {"name": "repo_owner", "type": "STRING", "mode": "REQUIRED"},
  {"name": "created_at", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "event_date", "type": "DATE", "mode": "REQUIRED"},
  {"name": "payload", "type": "JSON", "mode": "NULLABLE"},
  {"name": "public", "type": "BOOLEAN", "mode": "REQUIRED"},
  {"name": "loaded_at", "type": "TIMESTAMP", "mode": "REQUIRED"}
]
EOF

  time_partitioning {
    type                     = "DAY"
    field                    = "event_date"
    expiration_ms            = 7776000000  # 90 days
    require_partition_filter = false
  }

  clustering = ["repo_name", "actor_login", "event_type"]

  labels = {
    environment = "production"
    source      = "github"
  }
}

output "bucket_name" {
  value       = google_storage_bucket.raw_data.name
  description = "GCS Bucket name"
}

output "bq_table_id" {
  value       = "${google_bigquery_dataset.github.dataset_id}.${google_bigquery_table.github_events.table_id}"
  description = "BigQuery table ID"
}
