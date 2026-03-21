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

# ── Enable All APIs ───────────────────────────────────────────────
resource "google_project_service" "bigquery" {
  service            = "bigquery.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "vertex_ai" {
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_build" {
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secret_manager" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_scheduler" {
  service            = "cloudscheduler.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "storage" {
  service            = "storage.googleapis.com"
  disable_on_destroy = false
}

# ── Service Account ───────────────────────────────────────────────
resource "google_service_account" "prop_compass_sa" {
  account_id   = "prop-compass-sa"
  display_name = "PropCompass Service Account"
  description  = "Used by PropCompass pipelines and API"
}

resource "google_project_iam_member" "bq_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.prop_compass_sa.email}"
}

resource "google_project_iam_member" "bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.prop_compass_sa.email}"
}

resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.prop_compass_sa.email}"
}

resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.prop_compass_sa.email}"
}

resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.prop_compass_sa.email}"
}

resource "google_project_iam_member" "cloud_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.prop_compass_sa.email}"
}

# ── Cloud Storage Bucket ──────────────────────────────────────────
resource "google_storage_bucket" "prop_compass" {
  name          = var.gcs_bucket_name
  location      = var.region
  force_destroy = false

  lifecycle_rule {
    condition {
      age    = 90
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = true
  }

  depends_on = [google_project_service.storage]
}

# ── BigQuery Dataset ──────────────────────────────────────────────
resource "google_bigquery_dataset" "prop_compass" {
  dataset_id    = var.bq_dataset_id
  friendly_name = "PropCompass Real Estate Data"
  description   = "Property data, neighborhood scores, deal analysis"
  location      = "US"
  depends_on    = [google_project_service.bigquery]
}

# ── Table 1: Property Facts ───────────────────────────────────────
resource "google_bigquery_table" "property_facts" {
  dataset_id          = google_bigquery_dataset.prop_compass.dataset_id
  table_id            = "property_facts"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "ingested_at"
  }

  clustering = ["zip_code", "property_type"]

  schema = jsonencode([
    { name = "attom_id",        type = "STRING",    mode = "NULLABLE" },
    { name = "address",         type = "STRING",    mode = "NULLABLE" },
    { name = "city",            type = "STRING",    mode = "NULLABLE" },
    { name = "state",           type = "STRING",    mode = "NULLABLE" },
    { name = "zip_code",        type = "STRING",    mode = "NULLABLE" },
    { name = "property_type",   type = "STRING",    mode = "NULLABLE" },
    { name = "bedrooms",        type = "INTEGER",   mode = "NULLABLE" },
    { name = "bathrooms",       type = "FLOAT",     mode = "NULLABLE" },
    { name = "sqft",            type = "INTEGER",   mode = "NULLABLE" },
    { name = "lot_sqft",        type = "INTEGER",   mode = "NULLABLE" },
    { name = "year_built",      type = "INTEGER",   mode = "NULLABLE" },
    { name = "last_sale_price", type = "FLOAT",     mode = "NULLABLE" },
    { name = "last_sale_date",  type = "DATE",      mode = "NULLABLE" },
    { name = "assessed_value",  type = "FLOAT",     mode = "NULLABLE" },
    { name = "tax_annual",      type = "FLOAT",     mode = "NULLABLE" },
    { name = "latitude",        type = "FLOAT",     mode = "NULLABLE" },
    { name = "longitude",       type = "FLOAT",     mode = "NULLABLE" },
    { name = "ingested_at",     type = "TIMESTAMP", mode = "REQUIRED" }
  ])
}

# ── Table 2: Neighborhood ─────────────────────────────────────────
resource "google_bigquery_table" "neighborhood" {
  dataset_id          = google_bigquery_dataset.prop_compass.dataset_id
  table_id            = "neighborhood"
  deletion_protection = false
  clustering          = ["zip_code"]

  schema = jsonencode([
    { name = "zip_code",           type = "STRING",    mode = "REQUIRED" },
    { name = "city",               type = "STRING",    mode = "NULLABLE" },
    { name = "state",              type = "STRING",    mode = "NULLABLE" },
    { name = "median_income",      type = "FLOAT",     mode = "NULLABLE" },
    { name = "population",         type = "INTEGER",   mode = "NULLABLE" },
    { name = "population_growth",  type = "FLOAT",     mode = "NULLABLE" },
    { name = "median_age",         type = "FLOAT",     mode = "NULLABLE" },
    { name = "owner_occupied_pct", type = "FLOAT",     mode = "NULLABLE" },
    { name = "vacancy_rate",       type = "FLOAT",     mode = "NULLABLE" },
    { name = "poverty_rate",       type = "FLOAT",     mode = "NULLABLE" },
    { name = "ingested_at",        type = "TIMESTAMP", mode = "REQUIRED" }
  ])
}

# ── Table 3: Market Rates ─────────────────────────────────────────
resource "google_bigquery_table" "market_rates" {
  dataset_id          = google_bigquery_dataset.prop_compass.dataset_id
  table_id            = "market_rates"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "rate_date"
  }

  schema = jsonencode([
    { name = "rate_date",          type = "DATE",      mode = "REQUIRED" },
    { name = "mortgage_rate_30yr", type = "FLOAT",     mode = "NULLABLE" },
    { name = "mortgage_rate_15yr", type = "FLOAT",     mode = "NULLABLE" },
    { name = "fed_funds_rate",     type = "FLOAT",     mode = "NULLABLE" },
    { name = "inflation_rate",     type = "FLOAT",     mode = "NULLABLE" },
    { name = "ingested_at",        type = "TIMESTAMP", mode = "REQUIRED" }
  ])
}

# ── Table 4: Rent Estimates ───────────────────────────────────────
resource "google_bigquery_table" "rent_estimates" {
  dataset_id          = google_bigquery_dataset.prop_compass.dataset_id
  table_id            = "rent_estimates"
  deletion_protection = false
  clustering          = ["zip_code", "bedrooms"]

  schema = jsonencode([
    { name = "zip_code",    type = "STRING",    mode = "REQUIRED" },
    { name = "bedrooms",    type = "INTEGER",   mode = "REQUIRED" },
    { name = "rent_low",    type = "FLOAT",     mode = "NULLABLE" },
    { name = "rent_median", type = "FLOAT",     mode = "NULLABLE" },
    { name = "rent_high",   type = "FLOAT",     mode = "NULLABLE" },
    { name = "source",      type = "STRING",    mode = "NULLABLE" },
    { name = "ingested_at", type = "TIMESTAMP", mode = "REQUIRED" }
  ])
}

# ── Table 5: Deal Scores ──────────────────────────────────────────
resource "google_bigquery_table" "deal_scores" {
  dataset_id          = google_bigquery_dataset.prop_compass.dataset_id
  table_id            = "deal_scores"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "analyzed_at"
  }

  schema = jsonencode([
    { name = "analysis_id",        type = "STRING",    mode = "REQUIRED" },
    { name = "address",            type = "STRING",    mode = "REQUIRED" },
    { name = "purchase_price",     type = "FLOAT",     mode = "NULLABLE" },
    { name = "down_payment_pct",   type = "FLOAT",     mode = "NULLABLE" },
    { name = "monthly_rent",       type = "FLOAT",     mode = "NULLABLE" },
    { name = "monthly_mortgage",   type = "FLOAT",     mode = "NULLABLE" },
    { name = "monthly_expenses",   type = "FLOAT",     mode = "NULLABLE" },
    { name = "monthly_cashflow",   type = "FLOAT",     mode = "NULLABLE" },
    { name = "cap_rate",           type = "FLOAT",     mode = "NULLABLE" },
    { name = "cash_on_cash",       type = "FLOAT",     mode = "NULLABLE" },
    { name = "gross_rent_mult",    type = "FLOAT",     mode = "NULLABLE" },
    { name = "deal_score",         type = "FLOAT",     mode = "NULLABLE" },
    { name = "neighborhood_score", type = "FLOAT",     mode = "NULLABLE" },
    { name = "recommendation",     type = "STRING",    mode = "NULLABLE" },
    { name = "analyzed_at",        type = "TIMESTAMP", mode = "REQUIRED" }
  ])
}

# ── Artifact Registry ─────────────────────────────────────────────
resource "google_artifact_registry_repository" "prop_compass" {
  location      = var.region
  repository_id = "prop-compass"
  description   = "Docker images for PropCompass API"
  format        = "DOCKER"
  depends_on    = [google_project_service.artifact_registry]
}