# ================================================================
# Parallax — Backend Dockerfile
# FastAPI + Playwright + Python
# ================================================================

# Use official Python slim image
FROM python:3.12-slim

# Prevent Python from buffering stdout (important for Cloud Run logs)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies needed by Playwright / Chromium
RUN apt-get update && apt-get install -y \
    # Chromium runtime deps
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 \
    libpangocairo-1.0-0 libgtk-3-0 libx11-xcb1 libxcb-dri3-0 \
    # Fonts
    fonts-liberation fonts-noto-color-emoji \
    # Utilities
    wget curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only to keep image small)
RUN playwright install chromium --with-deps

# Copy application code
COPY agents/     ./agents/
COPY api/        ./api/
COPY models/     ./models/
COPY personas/   ./personas/
COPY tools/      ./tools/
COPY run_navigator.py .
COPY run_pipeline.py .

# Create output directory for screenshots
RUN mkdir -p /app/output

# Cloud Run sets PORT env var; default to 8000 for local
ENV PORT=8000

# Start FastAPI with uvicorn
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
