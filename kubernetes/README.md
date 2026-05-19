# Distributed Sentiment Analysis — Kubernetes

Runs a **FastAPI** API (2 pods) + **Celery ML workers** (2 pods) + **Redis** broker on a local Kubernetes cluster.

```
Client → FastAPI pod → Redis → Celery worker pod → Redis (result)
                                  (loads DistilBERT model)
```

---

## Prerequisites

Install these once:

| Tool | Purpose | Install |
|---|---|---|
| Docker | Build the image | https://docs.docker.com/get-docker |
| kubectl | Talk to the cluster | https://kubernetes.io/docs/tasks/tools |
| minikube | Local Kubernetes cluster | https://minikube.sigs.k8s.io/docs/start |

Verify everything is installed:
```bash
docker --version
kubectl version --client
minikube version
```

---

## Step 1 — Start the cluster

Give minikube enough memory for the ML model (~1 GB per worker pod):
```bash
minikube start --memory=4096 --cpus=4
```

---

## Step 2 — Point Docker at minikube's internal registry

This lets you use a locally-built image inside the cluster without pushing to Docker Hub:
```bash
eval $(minikube docker-env)
```

> Run this in every new terminal session before building.

---

## Step 3 — Build the Docker image

Run from this folder (`kubernetes/`):
```bash
cd /home/shivani/work/MLOps-projects/kubernetes
docker build -t your-username/sentiment-app:latest .
```

The first build takes a few minutes (downloads PyTorch + Transformers).

---

## Step 4 — Set imagePullPolicy to Never

Because the image is local (not on Docker Hub), open `k8s-deploy.yaml` and change **both** occurrences of:
```yaml
imagePullPolicy: Always
```
to:
```yaml
imagePullPolicy: Never
```
(There is one in `api-deployment` and one in `worker-deployment`.)

---

## Step 5 — Deploy everything

```bash
kubectl apply -f k8s-deploy.yaml
```

This creates:
- 1 Redis pod
- 2 FastAPI API pods
- 2 Celery worker pods

---

## Step 6 — Watch the pods come up

```bash
kubectl get pods --watch
```

Wait until all 5 pods show `Running`. Worker pods take ~60 seconds because they download the DistilBERT model on first start.

Expected output:
```
NAME                                 READY   STATUS    RESTARTS
redis-xxxx                           1/1     Running   0
api-deployment-xxxx                  1/1     Running   0
api-deployment-yyyy                  1/1     Running   0
worker-deployment-xxxx               1/1     Running   0
worker-deployment-yyyy               1/1     Running   0
```

---

## Step 7 — Get the API URL

```bash
minikube service api-service --url
```

This prints something like `http://192.168.49.2:31234`. Use that URL in all requests below.

---

## Step 8 — Test the API

### Health check
```bash
curl http://<URL>/
# {"status":"online"}
```

### Option A — Instant result (waits up to 30s)
```bash
curl -X POST http://<URL>/predict/sync \
  -H "Content-Type: application/json" \
  -d '{"texts": ["I love this!", "This is terrible."]}'
```
Response:
```json
{
  "result": [
    {"label": "POSITIVE", "score": 0.9998},
    {"label": "NEGATIVE", "score": 0.9997}
  ]
}
```

### Option B — Fire and forget (for large batches)
```bash
# 1. Submit the job
curl -X POST http://<URL>/predict \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Great product!", "Awful experience."]}'
# {"task_id": "abc-123", "status": "Pending"}

# 2. Poll for the result using the task_id
curl http://<URL>/result/abc-123
# {"status": "Success", "result": [...]}
```

---

## Useful debug commands

```bash
# See logs from the worker (model loading, task results)
kubectl logs -f deployment/worker-deployment

# See logs from the API
kubectl logs -f deployment/api-deployment

# Describe a pod to diagnose crash/pending issues
kubectl describe pod <pod-name>

# See recent cluster events (good for spotting errors)
kubectl get events --sort-by=.lastTimestamp
```

---

## Tear down

```bash
# Delete all deployed resources
kubectl delete -f k8s-deploy.yaml

# Stop the minikube cluster
minikube stop
```

---

## File structure

```
kubernetes/
├── app.py            # FastAPI — receives requests, sends jobs to Redis
├── worker.py         # Celery — pulls jobs from Redis, runs the ML model
├── Dockerfile        # Single image used by both API and worker pods
├── requirements.txt  # Python dependencies
└── k8s-deploy.yaml   # All Kubernetes manifests (Redis + API + Worker)
```

---

## Why this architecture?

| Concern | How it's solved |
|---|---|
| API stays online if the model crashes | API and worker are separate pods |
| Handle millions of texts without HTTP timeout | Jobs queued in Redis, not blocked on HTTP |
| Scale workers independently | `kubectl scale deployment worker-deployment --replicas=5` |
| Assign GPUs only to workers | Add GPU node selector to `worker-deployment` only |
