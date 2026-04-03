# Additional Terraform variables for GitHub Activity Pipeline

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

variable "data_retention_days" {
  description = "Number of days to retain data in BigQuery"
  type        = number
  default     = 90
}

variable "enable_bucket_versioning" {
  description = "Enable versioning on GCS bucket"
  type        = bool
  default     = true
}

variable "bucket_lifecycle_age" {
  description = "Delete objects older than this many days"
  type        = number
  default     = 90
}

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default = {
    environment = "production"
    source      = "github"
    managed_by  = "terraform"
  }
}
