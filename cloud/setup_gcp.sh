#!/bin/bash
# ================================================================
# Parallax — GCP Infrastructure Setup (Non-Terraform)
# Provisions: Firestore and GCS bucket via gcloud CLI
# ================================================================

set -euo pipefail

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
BUCKET_NAME="${PROJECT_ID}-parallax-screenshots"

echo "🚀 Setting up GCP resources for project: ${PROJECT_ID}"

echo "▶ 1. Enabling required APIs..."
gcloud services enable firestore.googleapis.com storage.googleapis.com --quiet

echo "▶ 2. Creating GCS bucket: ${BUCKET_NAME}..."
# Check if bucket exists
if gcloud storage buckets describe "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
    echo "  ✅ Bucket already exists."
else
    gcloud storage buckets create "gs://${BUCKET_NAME}" --location="${REGION}"
    echo "  ✅ Bucket created."
fi

echo "▶ 3. Configuring Bucket for public access (for dashboard screenshots)..."
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
    --member="allUsers" \
    --role="roles/storage.objectViewer" \
    --quiet
echo "  ✅ IAM policy updated."

echo "▶ 4. Creating Firestore database (default)..."
# Check if database exists
if gcloud alpha firestore databases describe --database='(default)' >/dev/null 2>&1; then
    echo "  ✅ Firestore already exists."
else
    # Use alpha/beta for firestore commands if GA fails, but usually 'firestore' works.
    # Note: 'nam5' is multi-region US, us-central1 is often easier to start with.
    gcloud alpha firestore databases create --location="${REGION}" --type=firestore-native
    echo "  ✅ Firestore created."
fi

echo ""
echo "========================================================"
echo "  🎉 GCP setup complete!"
echo "  Please update your .env with:"
echo "  GCS_BUCKET=\"${BUCKET_NAME}\""
echo "========================================================"
