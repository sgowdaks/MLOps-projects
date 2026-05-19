import os
# Force underlying libraries to run single-threaded to avoid deadlocks in containers
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from celery import Celery
from typing import List

REDIS_URL = "redis://redis-service:6379/0"

celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,  # results expire after 1 hour
)

# Load the model once when the worker process starts (not per task).
# This means each worker pod loads it into memory exactly once.
print("Loading Hugging Face sentiment model into worker...")
from transformers import pipeline  # noqa: E402  (import after Celery config)

model = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english",
)
print("Model loaded successfully.")


@celery_app.task(name="global_sentiment_task", bind=True, max_retries=3)
def sentiment_task(self, texts: List[str]):
    """Runs sentiment analysis on a batch of texts and returns the results."""
    try:
        results = model(texts)
        return results
    except Exception as exc:
        # Retry with exponential backoff on transient errors
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
