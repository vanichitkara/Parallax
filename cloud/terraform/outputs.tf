output "backend_url" {
  description = "Cloud Run backend URL"
  value       = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  description = "Cloud Run frontend URL"
  value       = google_cloud_run_v2_service.frontend.uri
}

output "screenshots_bucket" {
  description = "GCS bucket name for screenshots"
  value       = google_storage_bucket.screenshots.name
}
