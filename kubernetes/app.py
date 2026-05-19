import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from celery import Celery

# Client-only Celery instance — connects to Redis to send/check tasks.
# It does NOT import worker.py, so the ML model is never loaded here.
celery_client = Celery(
    broker="redis://redis-service:6379/0",
    backend="redis://redis-service:6379/0",
)

app = FastAPI(title="Sentiment Analysis API")


# The request body shape: a list of texts to analyse
class BatchText(BaseModel):
    texts: list[str]


# ── Health check ────────────────────────────────────────────────────────────
@app.get("/")
def health_check():
    return {"status": "online"}


# ── Option A: fire-and-forget (good for large batches) ──────────────────────
# Sends the job to Redis and returns a task_id straight away.
# The client can check progress with GET /result/{task_id}.
@app.post("/predict")
async def predict_async(data: BatchText):
    if not data.texts:
        raise HTTPException(status_code=422, detail="texts list must not be empty")
    # send_task references the task by name — worker.py is never imported here
    task = celery_client.send_task("global_sentiment_task", args=[data.texts])
    return {"task_id": task.id, "status": "Pending"}


# ── Option B: wait for result (good for small/interactive requests) ──────────
# Sends the job to Redis, then waits for the worker to finish and returns
# the result directly — all in one request.
# asyncio.to_thread keeps the server free to handle other requests while waiting.
@app.post("/predict/sync")
async def predict_sync(data: BatchText):
    if not data.texts:
        raise HTTPException(status_code=422, detail="texts list must not be empty")
    task = celery_client.send_task("global_sentiment_task", args=[data.texts])
    try:
        result = await asyncio.to_thread(task.get, timeout=30)
    except Exception as exc:
        raise HTTPException(status_code=504, detail=str(exc))
    return {"result": result}


# ── Check the status/result of an async job ──────────────────────────────────
@app.get("/result/{task_id}")
async def get_result(task_id: str):
    task = celery_client.AsyncResult(task_id)
    if task.state == "SUCCESS":
        return {"status": "Success", "result": task.result}
    if task.state == "FAILURE":
        return {"status": "Failed", "error": str(task.info)}
    return {"status": task.state}  # PENDING, STARTED, RETRY, etc.
