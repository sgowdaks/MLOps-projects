from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from worker import sentiment_task

app = FastAPI(title="Sentiment Analysis API", version="1.0.0")


class SingleText(BaseModel):
    text: str


class BatchText(BaseModel):
    texts: List[str]


@app.get("/")
def health_check():
    return {"status": "online", "mode": "distributed", "broker": "redis"}


@app.post("/predict")
async def predict_batch(data: BatchText):
    """Enqueues a batch of texts for sentiment analysis. Returns immediately."""
    if not data.texts:
        raise HTTPException(status_code=422, detail="texts list must not be empty")
    task = sentiment_task.delay(data.texts)
    return {"task_id": task.id, "status": "Pending", "item_count": len(data.texts)}


@app.get("/result/{task_id}")
async def get_result(task_id: str):
    """Poll this endpoint with the task_id to retrieve the result."""
    task = sentiment_task.AsyncResult(task_id)
    if task.state == "PENDING":
        return {"task_id": task_id, "status": "Pending"}
    elif task.state == "SUCCESS":
        return {"task_id": task_id, "status": "Success", "result": task.result}
    elif task.state == "FAILURE":
        return {"task_id": task_id, "status": "Failed", "error": str(task.info)}
    return {"task_id": task_id, "status": task.state}
