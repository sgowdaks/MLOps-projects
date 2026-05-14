# =============================================================================
# DOCKERFILE — FastAPI Sentiment Analysis Service
# =============================================================================
# Each instruction below creates a NEW LAYER in the image. Docker caches layers
# and only rebuilds from the first changed layer downward. This is why we copy
# requirements.txt BEFORE copying source code — dependencies change rarely,
# so that expensive pip-install layer stays cached across most rebuilds.
# =============================================================================

# --- LAYER 1: Base image ---
# Pulls the official Python 3.11 slim variant (~130 MB vs ~1 GB for the full image).
# "slim" excludes build tools, docs, and test suites we don't need at runtime.
FROM python:3.11-slim

# --- LAYER 2: System-level dependencies ---
# Install only what's needed for torch/transformers (e.g. libgomp for OpenMP).
# Combine all apt commands in ONE RUN to avoid creating extra intermediate layers.
# `--no-install-recommends` keeps the layer small; `rm -rf /var/lib/apt/lists/*`
# removes the package index cache that is no longer needed.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# --- LAYER 3: Working directory ---
# All subsequent COPY/RUN commands are relative to /app inside the container.
WORKDIR /app

# --- LAYER 4: Python dependencies (the "cache-friendly" layer) ---
# Copy ONLY the requirements file first.
# As long as requirements.txt doesn't change, Docker reuses this cached layer
# even when main.py changes — saving minutes on every code-only rebuild.
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# --- LAYER 5: Application source code ---
# Copied last so that frequent code edits invalidate only this thin layer,
# not the heavy dependency layer above.
COPY main.py .

# --- Metadata: document the port the app listens on ---
# EXPOSE is documentation only; it does NOT publish the port to the host.
# Actual publishing happens at `docker run` time via -p (see README).
EXPOSE 8000

# --- Default command ---
# Use the exec form (JSON array) so the process receives OS signals correctly
# (e.g. SIGTERM for graceful shutdown), unlike shell form which spawns a shell.
# 0.0.0.0 makes the server reachable from outside the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
