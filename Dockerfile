# ── Base Image ────────────────────────────────────────────────────
# Use official Python 3.11 slim image
# slim = smaller size, faster deployment
FROM python:3.11-slim

# ── Working Directory ─────────────────────────────────────────────
# All commands run from /app inside container
WORKDIR /app

# ── Install System Dependencies ───────────────────────────────────
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Copy Requirements First ───────────────────────────────────────
# Copy requirements before code so Docker caches this layer
# Only rebuilds this layer when requirements change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy Application Code ─────────────────────────────────────────
COPY . .

# ── Environment Variables ─────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# ── Start Command ─────────────────────────────────────────────────
# Cloud Run sets PORT environment variable automatically
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]