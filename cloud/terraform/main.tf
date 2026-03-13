# ================================================================
# Parallax — Terraform Infrastructure (Bonus Points)
# Provisions: Cloud Run services, GCS bucket, Firestore, IAM
# ================================================================

terraform {
  required_version = ">= 1.5"
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

# ── Enable APIs ──────────────────────────────────────────────────
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "containerregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "storage.googleapis.com",
    "firestore.googleapis.com",
    "secretmanager.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# ── GCS Bucket for screenshots ───────────────────────────────────
resource "google_storage_bucket" "screenshots" {
  name          = "${var.project_id}-parallax-screenshots"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition { age = 30 }   # Auto-delete screenshots after 30 days
    action    { type = "Delete" }
  }

  cors {
    origin          = ["*"]
    method          = ["GET"]
    response_header = ["Content-Type"]
    max_age_seconds = 3600
  }
}

# Make bucket publicly readable (for screenshots in dashboard)
resource "google_storage_bucket_iam_member" "public_read" {
  bucket = google_storage_bucket.screenshots.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# ── Firestore (Native mode) ──────────────────────────────────────
resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = "nam5"
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.apis]
}

# ── Secret Manager — API Key ─────────────────────────────────────
resource "google_secret_manager_secret" "api_key" {
  secret_id = "parallax-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

# Note: Secret value is set manually or via CI/CD pipeline
# gcloud secrets versions add parallax-api-key --data-file=<(echo -n "$GOOGLE_API_KEY")

# ── Service Account for Cloud Run ────────────────────────────────
resource "google_service_account" "backend_sa" {
  account_id   = "parallax-backend-sa"
  display_name = "Parallax Backend Service Account"
}

resource "google_project_iam_member" "backend_sa_roles" {
  for_each = toset([
    "roles/storage.objectAdmin",         # Write screenshots to GCS
    "roles/datastore.user",              # Read/write Firestore
    "roles/secretmanager.secretAccessor", # Read API key secret
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}

# ── Cloud Run — Backend ──────────────────────────────────────────
resource "google_cloud_run_v2_service" "backend" {
  name     = "parallax-backend"
  location = var.region

  template {
    service_account = google_service_account.backend_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    containers {
      image = "gcr.io/${var.project_id}/parallax-backend:latest"

      resources {
        limits = {
          memory = "2Gi"
          cpu    = "2"
        }
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GEMINI_MODEL"
        value = var.gemini_model
      }
      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.screenshots.name
      }
      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.api_key.secret_id
            version = "latest"
          }
        }
      }

      ports {
        container_port = 8000
      }

      startup_probe {
        http_get { path = "/health" }
        initial_delay_seconds = 10
        period_seconds        = 5
        failure_threshold     = 10
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# Allow unauthenticated invocation of backend
resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Cloud Run — Frontend ─────────────────────────────────────────
resource "google_cloud_run_v2_service" "frontend" {
  name     = "parallax-frontend"
  location = var.region

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    containers {
      image = "gcr.io/${var.project_id}/parallax-frontend:latest"

      resources {
        limits = {
          memory = "256Mi"
          cpu    = "1"
        }
      }

      ports {
        container_port = 80
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
