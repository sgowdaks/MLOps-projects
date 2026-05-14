"""Step 2 — Query API (run after indexing).

Usage:
    uvicorn qdrant.query_api:app --reload --port 8001

Then query:
    curl -X POST http://localhost:8001/search \
         -H "Content-Type: application/json" \
         -d '{"query": "RAG engineer with NLP skills", "min_years_exp": 3, "limit": 3}'
"""

from __future__ import annotations

import os

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

COLLECTION_NAME = "resumes_demo"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Shared state loaded once at startup.
state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    state["client"] = QdrantClient("localhost", port=6333)
    state["encoder"] = SentenceTransformer(MODEL_NAME)
    print("Qdrant client and encoder ready.")
    yield
    state.clear()


app = FastAPI(title="Qdrant Resume Search", lifespan=lifespan)


# --- Schemas ---

class SearchRequest(BaseModel):
    query: str
    min_years_exp: int = 0
    limit: int = 5


class SearchResult(BaseModel):
    id: int
    score: float
    role: str
    years_exp: int
    text: str


# --- Endpoints ---

@app.get("/")
def health():
    return {"status": "online", "collection": COLLECTION_NAME}


@app.post("/search", response_model=list[SearchResult])
def search(req: SearchRequest):
    encoder: SentenceTransformer = state["encoder"]
    client: QdrantClient = state["client"]

    query_vector = encoder.encode(req.query, normalize_embeddings=True).tolist()

    query_filter = None
    if req.min_years_exp > 0:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="years_exp",
                    range=models.Range(gte=req.min_years_exp),
                )
            ]
        )

    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=query_filter,
        limit=req.limit,
    )

    return [
        SearchResult(
            id=hit.id,
            score=round(hit.score, 4),
            role=hit.payload.get("role", ""),
            years_exp=hit.payload.get("years_exp", 0),
            text=hit.payload.get("text", ""),
        )
        for hit in response.points
    ]
