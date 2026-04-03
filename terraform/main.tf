# GitHub Activity Batch Pipeline - Terraform Configuration
# DE Zoomcamp 2026 Final Project

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
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

locals {
  name_prefix = "gh-activity-${var.environment}"
  labels = {
    project     = "github-activity-pipeline"
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "google_storage_bucket" "archive_bucket" {
  name          = "${local.name_prefix}-archive-${var.project_id}"
  location      = var.region
  force_destroy = true
  labels        = local.labels
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

resource "google_bigquery_dataset" "github_dataset" {
  dataset_id                  = "${local.name_prefix}_github"
  friendly_name               = "GitHub Activity Data"
  description                 = "Dataset for GitHub Archive batch processing pipeline"
  location                    = var.region
  delete_contents_on_destroy  = true
  labels                      = local.labels
  default_table_expiration_ms = 7776000000
}

resource "google_bigquery_table" "github_events" {
  dataset_id = google_bigquery_dataset.github_dataset.dataset_id
  table_id   = "github_events"
  deletion_protection = false

  schema = <<EOF
[
  {"name": "id", "type": "STRING", "mode": "REQUIRED"},
  {"name": "type", "type": "STRING", "mode": "NULLABLE"},
  {"name": "actor_login", "type": "STRING", "mode": "NULLABLE"},
  {"name": "repo_name", "type": "STRING", "mode": "NULLABLE"},
  {"name": "action", "type": "STRING", "mode": "NULLABLE"},
  {"name": "created_at", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "date_partition", "type": "DATE", "mode": "REQUIRED"},
  {"name": "payload", "type": "JSON", "mode": "NULLABLE"},
  {"name": "org_login", "type": "STRING", "mode": "NULLABLE"},
  {"name": "file_url", "type": "STRING", "mode": "NULLABLE"}
]
EOF

  time_partitioning {
    type                     = "DAY"
    field                    = "date_partition"
    expiration_ms            = 7776000000
    require_partition_filter = false
  }

  clustering = ["type", "actor_login", "repo_name"]
  labels     = local.labels
}

resource "google_service_account" "airflow_sa" {
  account_id   = "${local.name_prefix}-airflow"
  display_name = "Airflow Pipeline Service Account"
}

resource "google_storage_bucket_iam_member" "airflow_bucket_access" {
  bucket = google_storage_bucket.archive_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.airflow_sa.email}"
}

resource "google_bigquery_dataset_iam_member" "airflow_dataset_access" {
  dataset_id = google_bigquery_dataset.github_dataset.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.airflow_sa.email}"
}

resource "google_bigquery_dataset_iam_member" "airflow_job_user" {
  dataset_id = google_bigquery_dataset.github_dataset.dataset_id
  role       = "roles/bigquery.jobUser"
  member     = "serviceAccount:${google_service_account.airflow_sa.email}"
}

output "bucket_name" {
  value = google_storage_bucket.archive_bucket.name
}

output "dataset_id" {
  value = google_bigquery_dataset.github_dataset.dataset_id
}

output "table_id" {
  value = google_bigquery_table.github_events.table_id
}

output "service_account_email" {
  value = google_service_account.airflow_sa.email
}
