variable "project_id" {
  description = "Your GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "bq_dataset_id" {
  description = "BigQuery dataset name"
  type        = string
  default     = "prop_compass"
}

variable "gcs_bucket_name" {
  description = "Cloud Storage bucket name"
  type        = string
}

