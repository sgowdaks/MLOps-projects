# Docker — FastAPI Sentiment Analysis

A hands-on walkthrough of core Docker concepts using the FastAPI sentiment analysis service.

---

## Folder structure

```
docker/
├── Dockerfile          # Build instructions (read this first)
├── requirements.txt    # Python dependencies
├── .dockerignore       # Files excluded from the build context
├── main.py             # FastAPI application
└── README.md           # This file
```

---

## Concept 1 — Image Layers & Caching

A Docker image is a **stack of read-only layers**. Every instruction in the Dockerfile (`FROM`, `RUN`, `COPY`, etc.) produces exactly one layer. Layers are identified by a content hash, so Docker can **reuse a cached layer** if nothing upstream has changed.

```
┌──────────────────────────────────────┐  ← LAYER 5: COPY main.py  (changes often)
├──────────────────────────────────────┤  ← LAYER 4: pip install   (cached if requirements.txt unchanged)
├──────────────────────────────────────┤  ← LAYER 3: COPY requirements.txt
├──────────────────────────────────────┤  ← LAYER 2: apt-get install libgomp1
└──────────────────────────────────────┘  ← LAYER 1: python:3.11-slim  (base, always cached after first pull)
```

**Why order matters for caching:**  
If you copy `main.py` before installing dependencies, every code change forces a full re-install. Copying `requirements.txt` first keeps the expensive layer cached for code-only changes.

```dockerfile
# GOOD — dependencies layer is cache-stable
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .            # changing this only rebuilds from here

# BAD — any code change busts the pip-install cache
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
```

---

## Concept 2 — Building an Image

```bash
# Build and tag the image
# -t name:tag   give the image a human-readable name
# .             build context = current directory (sent to Docker daemon)
docker build -t sentiment-api:latest .
```

Watch the output — lines that say `CACHED` are layers Docker reused.  
After the first build, change only `main.py` and rebuild — layers 1–4 will all be `CACHED`.

```bash
# Inspect the layers that make up the image
docker history sentiment-api:latest

# List all local images
docker images
```

---

## Concept 3 — Running a Container

A **container** is a running instance of an image — like a process spawned from an executable.

```bash
# Basic run (container stops when you Ctrl-C)
docker run sentiment-api:latest
```

Useful flags:

| Flag | Purpose | Example |
|------|---------|---------|
| `-d` | Detached (background) mode | `docker run -d ...` |
| `--name` | Give the container a name | `--name sentiment` |
| `--rm` | Auto-remove container on exit | `docker run --rm ...` |
| `-e` | Set environment variable | `-e LOG_LEVEL=info` |

```bash
# Run detached with a name
docker run -d --name sentiment-api sentiment-api:latest

# See running containers
docker ps

# See all containers (including stopped)
docker ps -a

# Tail logs from the running container
docker logs -f sentiment-api

# Stop and remove
docker stop sentiment-api
docker rm sentiment-api
```

---

## Concept 4 — Port Mapping

The container has its **own isolated network namespace**. The app listens on port `8000` *inside* the container, but that port is invisible to your host by default.

`-p <host_port>:<container_port>` publishes (maps) a container port to a port on your machine.

```
Your laptop          Container
─────────────────────────────────────────────
localhost:8000  ───►  container:8000   (1-to-1)
localhost:9000  ───►  container:8000   (different host port)
```

```bash
# Map host 8000 → container 8000
docker run -d --name sentiment-api -p 8000:8000 sentiment-api:latest

# Map host 9000 → container 8000 (useful when 8000 is already taken locally)
docker run -d --name sentiment-api -p 9000:8000 sentiment-api:latest
```

Now curl the running service from your host:

```bash
# Health check
curl http://localhost:8000/

# Real-time prediction
curl -X POST http://localhost:8000/predict/realtime \
     -H "Content-Type: application/json" \
     -d '{"text": "Docker makes deployment so much easier!"}'

# Batch prediction (returns 202 immediately)
curl -X POST http://localhost:8000/predict/batch \
     -H "Content-Type: application/json" \
     -d '{"texts": ["I love this!", "This is terrible.", "Meh, it is okay."]}'
```

Or open the auto-generated API docs: http://localhost:8000/docs

---

## Quick-start (all-in-one)

```bash
# 1. Build
docker build -t sentiment-api:latest .

# 2. Run with port mapping
docker run -d --name sentiment-api -p 8000:8000 sentiment-api:latest

# 3. Test
curl http://localhost:8000/

# 4. Stop & clean up
docker stop sentiment-api && docker rm sentiment-api
```

---

## Useful debugging commands

```bash
# Open a shell inside a running container
docker exec -it sentiment-api /bin/bash

# Open a shell inside a temporary container (without starting the app)
docker run --rm -it sentiment-api:latest /bin/bash

# Show real-time resource usage (CPU, RAM) of running containers
docker stats

# Remove all stopped containers + dangling images (safe cleanup)
docker system prune
```
