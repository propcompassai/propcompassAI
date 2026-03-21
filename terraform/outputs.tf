output "bigquery_dataset" {
  value       = google_bigquery_dataset.prop_compass.dataset_id
  description = "BigQuery dataset ID"
}

output "gcs_bucket" {
  value       = google_storage_bucket.prop_compass.name
  description = "Cloud Storage bucket name"
}

output "service_account_email" {
  value       = google_service_account.prop_compass_sa.email
  description = "Service account email"
}