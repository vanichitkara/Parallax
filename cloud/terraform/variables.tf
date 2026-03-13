variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "parallax-490117"
}

variable "region" {
  description = "GCP region for Cloud Run"
  type        = string
  default     = "us-central1"
}

variable "gemini_model" {
  description = "Gemini model to use"
  type        = string
  default     = "gemini-2.5-flash"
}
