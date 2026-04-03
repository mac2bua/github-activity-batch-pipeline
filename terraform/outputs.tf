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
