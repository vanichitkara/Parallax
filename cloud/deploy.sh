#!/bin/bash
# ================================================================
# Parallax — Cloud Run Deployment Script
# Usage: ./cloud/deploy.sh
# ================================================================

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────
PROJECT_ID="parallax-490117"
REGION="us-central1"
REGISTRY="gcr.io/${PROJECT_ID}"
BACKEND_SERVICE="parallax-backend"
FRONTEND_SERVICE="parallax-frontend"

# Load env vars for secrets
source "$(dirname "$0")/../.env" 2>/dev/null || true

echo ""
echo "========================================================"
echo "  🚀 Parallax — Deploying to Google Cloud Run"
echo "  Project : ${PROJECT_ID}"
echo "  Region  : ${REGION}"
echo "========================================================"
echo ""

# ── Step 1: Authenticate & configure project ─────────────────────
echo "▶ Configuring gcloud..."
gcloud config set project "${PROJECT_ID}"
gcloud config set run/region "${REGION}"

# ── Step 2: Enable required APIs ─────────────────────────────────
echo "▶ Enabling GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    containerregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    --quiet

# ── Step 3: Configure Docker for GCR ─────────────────────────────
echo "▶ Configuring Docker for GCR..."
gcloud auth configure-docker --quiet

# ── Step 4: Build & push backend image ───────────────────────────
echo ""
echo "▶ Building backend image..."
BACKEND_IMAGE="${REGISTRY}/${BACKEND_SERVICE}:latest"
docker build -f Dockerfile -t "${BACKEND_IMAGE}" .

echo "▶ Pushing backend image..."
docker push "${BACKEND_IMAGE}"

# ── Step 5: Deploy backend to Cloud Run ──────────────────────────
echo ""
echo "▶ Deploying backend to Cloud Run..."
gcloud run deploy "${BACKEND_SERVICE}" \
    --image="${BACKEND_IMAGE}" \
    --platform=managed \
    --region="${REGION}" \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=2 \
    --timeout=600 \
    --concurrency=5 \
    --min-instances=0 \
    --max-instances=3 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GEMINI_MODEL=${GEMINI_MODEL:-gemini-2.5-flash},GCS_BUCKET=parallax-screenshots" \
    --set-secrets="GOOGLE_API_KEY=parallax-api-key:latest" \
    --quiet

# Get the backend URL
BACKEND_URL=$(gcloud run services describe "${BACKEND_SERVICE}" \
    --region="${REGION}" \
    --format="value(status.url)")
echo "  ✅ Backend deployed: ${BACKEND_URL}"

# ── Step 6: Build & push frontend image ──────────────────────────
echo ""
echo "▶ Building frontend image (API URL: ${BACKEND_URL})..."
FRONTEND_IMAGE="${REGISTRY}/${FRONTEND_SERVICE}:latest"
docker build \
    -f Dockerfile.frontend \
    --build-arg VITE_API_URL="${BACKEND_URL}" \
    -t "${FRONTEND_IMAGE}" .

echo "▶ Pushing frontend image..."
docker push "${FRONTEND_IMAGE}"

# ── Step 7: Deploy frontend to Cloud Run ─────────────────────────
echo ""
echo "▶ Deploying frontend to Cloud Run..."
gcloud run deploy "${FRONTEND_SERVICE}" \
    --image="${FRONTEND_IMAGE}" \
    --platform=managed \
    --region="${REGION}" \
    --allow-unauthenticated \
    --memory=256Mi \
    --cpu=1 \
    --timeout=30 \
    --concurrency=80 \
    --min-instances=0 \
    --max-instances=5 \
    --quiet

FRONTEND_URL=$(gcloud run services describe "${FRONTEND_SERVICE}" \
    --region="${REGION}" \
    --format="value(status.url)")
echo "  ✅ Frontend deployed: ${FRONTEND_URL}"

# ── Done ─────────────────────────────────────────────────────────
echo ""
echo "========================================================"
echo "  ✅ Deployment complete!"
echo "  🎨 Dashboard : ${FRONTEND_URL}"
echo "  🔌 API       : ${BACKEND_URL}"
echo "  📖 API docs  : ${BACKEND_URL}/docs"
echo "========================================================"
echo ""
