FROM python:3.10-slim

WORKDIR /app

# Install system-level dependencies needed by some torch builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py worker.py ./

# CMD is intentionally left out here.
# It is overridden per-deployment in the Kubernetes manifest:
#   API pods:    uvicorn app:app --host 0.0.0.0 --port 8000
#   Worker pods: celery -A worker worker --loglevel=info
