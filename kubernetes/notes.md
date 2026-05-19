
---

# Blog Outline: Anatomy of an MLOps Post-Mortem

## Introduction: The Architecture

The goal was to deploy a distributed, production-grade sentiment analysis pipeline using **FastAPI** as the web framework, **Celery** as the asynchronous task manager, **Redis** as the message broker/result backend, and **HuggingFace Transformers** (`distilbert-base-uncased`) for machine learning inference. Everything was orchestrated locally using **Minikube (Kubernetes)**.

But moving from `localhost` code to containerized microservices turned into a battlefield of memory allocations, network drops, and threading deadlocks. Here is exactly what broke, why it broke, and how we engineered the fixes.

---

## 💥 Error 1: The Out-of-Memory (OOM) Massacre

### The Symptom

Running `kubectl get pods` revealed that the API pods were crashing instantly with an **`OOMKilled`** status.

### Why It Happened

1. **The Default Minikube Trap:** By default, Minikube starts with a minuscule cluster RAM allocation (typically 2GB).
2. **The Massive Image & Multi-Pod Race:** The application used a massive 5.66GB Docker image layers to wrap HuggingFace. Trying to run 2 API pods, 2 Worker pods, and a Redis instance inside a 2GB cluster immediately starved the Linux kernel, forcing it to kill the pods to protect the machine.

### The Fix

* **Scale down for local testing:** Reduced the deployment configurations to exactly 1 replica for the API and 1 replica for the worker to halve the memory footprint.
* **Over-provision Minikube:** Purged the tiny default cluster and booted a robust machine using:
```bash
minikube delete
minikube start --cpus=4 --memory=8192

```



---

## 💥 Error 2: The "Lightweight API" Memory Leak

### The Symptom

Even after scaling down, the API pod *still* suffered from `OOMKilled` errors despite having its own independent container limit of 1Gi-2Gi.

### Why It Happened

The API script had a direct Python import dependency on the worker module:

```python
# In app.py
from worker import sentiment_task

```

Because of how Python evaluates top-level scripts, importing anything from `worker.py` forced the API process to execute the entire file. If the HuggingFace `pipeline()` initialization sat at the top layer of the worker, the API accidentally loaded the multi-gigabyte machine learning model into its own container memory space, instantly breaching its Kubernetes limits.

### The Fix

We decoupled the architecture cleanly using Celery's string-based execution routing (`send_task`). This allowed the API to communicate with Redis without ever importing or touching a single line of machine learning code.

**Before (Monolithic Import):**

```python
task = sentiment_task.delay(data.texts)

```

**After (Decoupled Messaging):**

```python
task = celery_client.send_task("global_sentiment_task", args=[data.texts])

```

---

## 💥 Error 3: The Ghost Endpoint (404 Not Found)

### The Symptom

Hitting the synchronous endpoint via curl returned a `{"detail":"Not Found"}` (404 Error), even though the endpoint was clearly written down in `app.py`.

### Why It Happened

**Kubernetes Image Caching.** When rebuilding images locally using the `:latest` tag, Minikube's underlying cluster nodes often assume they already possess the latest image layer and completely skip pulling your fresh code adjustments. The container was literally running a ghost version of your historical code.

### The Fix

Adopted an immutable image tagging strategy (moving from `:latest` to explicit versions like `:v2`, `:v3`, etc.) and explicitly set the `imagePullPolicy: IfNotPresent`, forcing Kubernetes to identify the new tag string and pull the updated deployment layers cleanly.

---

## 💥 Error 4: The Endless Loop of `PENDING` Tasks

### The Symptom

The API successfully returned a task UUID, but hitting `/result/{id}` returned a status of `PENDING` indefinitely. Checking the worker logs revealed an abrupt `worker: Warm shutdown (MainProcess)` error followed by a pod restart.

### Why It Happened

**Aggressive Kubernetes Health Checks.** The `k8s-deploy.yaml` configuration contained a `livenessProbe` that forced the worker to respond to a `celery inspect ping` command every 60 seconds. Because the worker process was 100% occupied loading or running the massive model weights, it couldn't answer the ping within the tight 10-second timeout window. Kubernetes mistakenly declared the container dead, sent a `SIGTERM` signal, and aborted the operation.

### The Fix

Completely removed the `livenessProbe` block from the worker deployment manifest. Background queue processors do not serve public HTTP routes and should be allowed to run long, synchronous computations without container execution interruptions.

---

## 💥 Error 5: The Discarded Message (`KeyError: 'sentiment_task'`)

### The Symptom

The task stayed `PENDING` indefinitely, but checking the active worker logs revealed a fatal Celery runtime exception:

```text
Received unregistered task of type 'sentiment_task'.
The message has been ignored and discarded.
KeyError: 'sentiment_task'

```

### Why It Happened

When launching Celery with a module pointer (`celery -A worker worker`), Celery sometimes appends the file wrapper name as a namespace prefix (e.g., `worker.sentiment_task`). Because the API sent a bare target string (`"sentiment_task"`), the worker rejected it as an unlisted signature and immediately dropped the payload.

### The Fix

Forced a strict, unbendable, absolute naming convention inside the task decorator definition to fully bypass automated Python folder nesting lookups:

```python
# In worker.py
@celery_app.task(name="global_sentiment_task", bind=True, max_retries=3)

```

---

## 💥 Error 6: The Infinite Hang (The Solo Process Thread Lock)

### The Symptom

The task was received with a matching name string (`Task global_sentiment_task received`), but the logs completely froze on that line. No execution feedback, no success metrics, and a permanent `PENDING` state on the frontend.

### Why It Happened

**Concurrency Conflict with `--pool=solo`.** HuggingFace Transformers use underlying multi-threaded C++ runtimes (like PyTorch/OpenBLAS) to manage tokenization and tensor operations. When Celery is configured to run with `--pool=solo`, it executes everything inside its absolute primary process thread. When the model tried to split operations into multiple threads inside that rigid process space, it locked horns with Celery's loop, causing a silent, unbreakable **deadlock**.

### The Fix

1. Switched the Celery container startup pooling architecture from `solo` to an isolated worker process instance with low concurrency overhead:
```yaml
command: ["celery", "-A", "worker", "worker", "--loglevel=info", "--pool=prefork", "--concurrency=1"]

```


2. Injected strict environment overrides at the absolute top of `worker.py` to instruct PyTorch and Tokenizers to run linearly inside the container without spawning unstable secondary fork streams:

```python
   import os
   os.environ["TOKENIZERS_PARALLELISM"] = "false"
   os.environ["OMP_NUM_THREADS"] = "1"
   os.environ["MKL_NUM_THREADS"] = "1"

```

---

## Key Takeaways for your Blog Readers

1. **Never use `:latest` in local Dev:** It breaks the Kubernetes development feedback loop due to deep engine caching. Use explicit tags.
2. **Decouple by Messaging, Not Imports:** Keep your API light. If an API container imports an ML worker file, it inherits the memory profile of an ML worker file.
3. **Turn Off Background Probes:** Don’t subject asynchronous workers running blocking tensor mathematics to strict, time-sensitive liveness pings.
4. **Be Careful with `--pool=solo`:** While memory-efficient, the solo execution pool can easily deadlock when mixed with heavy multi-threaded C libraries like PyTorch.



```

```