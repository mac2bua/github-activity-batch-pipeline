# Terraform outputs for GitHub Activity Pipeline

output "bucket_name" {
  value       = google_storage_bucket.raw_data.name
  description = "GCS Bucket name for raw GitHub data"
}

output "bucket_url" {
  value       = "gs://${google_storage_bucket.raw_data.name}"
  description = "GCS Bucket URL"
}

output "bq_dataset_id" {
  value       = google_bigquery_dataset.github.dataset_id
  description = "BigQuery Dataset ID"
}

output "bq_table_id" {
  value       = "${google_bigquery_dataset.github.dataset_id}.${google_bigquery_table.github_events.table_id}"
  description = "BigQuery Table ID (dataset.table format)"
}

output "bq_table_full_id" {
  value       = "${var.project_id}:${google_bigquery_dataset.github.dataset_id}.${google_bigquery_table.github_events.table_id}"
  description = "BigQuery Table full ID (project:dataset.table format)"
}

output "project_id" {
  value       = var.project_id
  description = "GCP Project ID"
}

output "region" {
  value       = var.region
  description = "GCP Region"
}

output "data_retention_days" {
  value       = google_bigquery_table.github_events.time_partitioning[0].expiration_ms / (24 * 60 * 60 * 1000)
  description = "Data retention period in days"
}
