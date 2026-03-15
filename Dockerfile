# Use official Python slim image (Debian Bookworm)
FROM python:3.12-slim-bookworm

# Prevent Python from buffering stdout
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Set working directory
WORKDIR /app

# 1. Install system utilities and Python dependencies
# We do this in one layer to keep the image small
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir playwright \
    # 2. Install ONLY Chromium and ONLY its required system deps
    && playwright install chromium \
    && playwright install-deps chromium \
    # 3. Clean up APT and temporary files
    && apt-get purge -y --auto-remove wget gnupg \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /root/.cache/pip \
    && rm -rf /tmp/*

# Copy application code
COPY agents/     ./agents/
COPY api/        ./api/
COPY models/     ./models/
COPY personas/   ./personas/
COPY tools/      ./tools/
COPY run_navigator.py .
COPY run_pipeline.py .

# Create output directory
RUN mkdir -p /app/output

# Cloud Run sets PORT env var
ENV PORT=8000

# Start FastAPI
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
