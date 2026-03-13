#!/bin/bash
# ================================================================
# Parallax — One-time Secret Manager setup
# Run this ONCE before first deployment to store the API key.
# Usage: ./cloud/setup-secret.sh
# ================================================================

set -euo pipefail

PROJECT_ID="parallax-490117"

# Load API key from local .env
source "$(dirname "$0")/../.env"

if [[ -z "${GOOGLE_API_KEY:-}" ]]; then
  echo "❌ GOOGLE_API_KEY not set in .env"
  exit 1
fi

echo "▶ Setting project to ${PROJECT_ID}..."
gcloud config set project "${PROJECT_ID}"

echo "▶ Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --quiet

echo "▶ Creating secret 'parallax-api-key'..."
gcloud secrets create parallax-api-key \
  --replication-policy="automatic" \
  --quiet 2>/dev/null || echo "  (secret already exists, updating...)"

echo "▶ Adding secret version..."
echo -n "${GOOGLE_API_KEY}" | gcloud secrets versions add parallax-api-key --data-file=-

echo ""
echo "✅ Secret stored successfully!"
echo "   gcloud secrets versions list parallax-api-key"
