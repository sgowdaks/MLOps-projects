Build an image with an explicit version tag:

Bash
docker build -t shivani/sentiment-app:v6 .
Why it matters: Avoids the default :latest tag cache trap. Incrementing version numbers forces Kubernetes to register that a fresh code layer is available.

docker system prune -f
    ```

---

## ☸️ 2. Minikube Cluster Administration

Minikube sets up your local Kubernetes playground. Over-provisioning resources at launch is critical for heavy machine learning model weights.

*   **Start the cluster with high-performance specs:**
    
```bash
    minikube start --cpus=4 --memory=8192
    ```
    > **Why it matters:** Hugging Face models will completely crash (OOM) the node if left at Minikube’s default 2GB allocation.
*   **Inject a local Docker image directly into the cluster node cache:**
    
```bash
    minikube image load shivani/sentiment-app:v6
    ```
    > **Why it matters:** Bypasses the need to push your local images to an external registry like Docker Hub or Azure Container Registry during development.
*   **Wipe the local cluster completely (To start fresh):**
    ```bash
    minikube delete
    ```

---

## 🏗️ 3. Kubernetes Object Management (`kubectl`)

These are your primary tools for creating, destroying, inspecting, and tracking the application microservices inside the cluster.

### Orchestration
*   **Apply or update resources from a manifest file:**
    ```bash
    kubectl apply -f k8s-deploy.yaml
    ```
*   **Purge specific deployments cleanly:**
    ```bash
    kubectl delete deployment api-deployment worker-deployment
    ```
*   **Perform a graceful, zero-downtime rolling restart:**
    
```bash
    kubectl rollout restart deployment/api-deployment
    ```

### Inspection & Diagnostics
*   **List all active pods, statuses, and uptime histories:**
    ```bash
    kubectl get pods
    ```
*   **Inspect resource consumption (RAM/CPU utilization):**
    ```bash
    kubectl top pods
    ```
    *(Requires the Minikube metrics-server addon to be enabled).*
*   **Read the active files sitting inside a running container:**
    
```bash
    kubectl exec deployment/api-deployment -- cat app.py
    ```
    > **Why it matters:** Allows you to verify with 100% certainty if your latest code changes are actually live inside the container.

### Debugging Logs
*   **Stream live application logs continuously:**
    
```bash
    kubectl logs deployment/worker-deployment -f
    ```
*   **Read the logs of a container right *before* it crashed:**
    
```bash
    kubectl logs deployment/worker-deployment --previous
    ```
    > **Why it matters:** Essential for identifying why an `OOMKilled` or Python runtime crash occurred right before Kubernetes rebooted the pod.

---

## 🖲️ 4. Redis Queue Monitoring

Because Celery delegates its underlying message passing to Redis, querying Redis tells us exactly where tasks are getting blocked.

*   **Check the length of the pending task queue:**
    
```bash
    kubectl exec -it redis-7d8db59f88-qrgnj -- redis-cli LLEN celery
    ```
    > **Reading the results:** 
    > * `(integer) 0` means all messages have been picked up by workers.
    > * Greater than `0` means workers are locked up, dead, or not running.
*   **Real-time queue monitoring (refreshes every 2 seconds):**
    
```bash
    watch -n 2 kubectl exec -it redis-7d8db59f88-qrgnj -- redis-cli LLEN celery
    ```
*   **Examine all metadata/keys stored in the database:**
    
```bash
    kubectl exec -it redis-7d8db59f88-qrgnj -- redis-cli KEYS "*"
    ```
*   **Flush the entire database completely (Wipes all poison/stuck tasks):**
    
```bash
    kubectl exec -it redis-7d8db59f88-qrgnj -- redis-cli FLUSHALL
    ```
    > **Why it matters:** Clears out old task IDs that are stuck or look for unregistered names, giving your workers a totally clean slate.