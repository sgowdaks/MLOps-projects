"""Step 1 — Index data into Qdrant (run once).

Usage:
    python qdrant/index.py

Embeds sample resumes with all-MiniLM-L6-v2 and upserts them into the
'resumes_demo' collection on the running Qdrant server.
"""

from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

COLLECTION_NAME = "resumes_demo"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def build_sample_data() -> list[dict[str, Any]]:
    return [
        {
            "id": 1,
            "text": "Python backend engineer with FastAPI and Docker experience.",
            "years_exp": 4,
            "role": "backend-engineer",
            "skills": ["python", "fastapi", "docker"],
        },
        {
            "id": 2,
            "text": "Data scientist who builds NLP pipelines and recommendation systems.",
            "years_exp": 5,
            "role": "data-scientist",
            "skills": ["python", "nlp", "pytorch"],
        },
        {
            "id": 3,
            "text": "Junior frontend developer focused on React and TypeScript.",
            "years_exp": 1,
            "role": "frontend-engineer",
            "skills": ["react", "typescript", "css"],
        },
        {
            "id": 4,
            "text": "MLOps engineer handling model deployment, monitoring, and CI/CD.",
            "years_exp": 6,
            "role": "mlops-engineer",
            "skills": ["mlops", "kubernetes", "monitoring"],
        },
        {
            "id": 5,
            "text": "Machine learning engineer building retrieval-augmented generation systems.",
            "years_exp": 3,
            "role": "ml-engineer",
            "skills": ["rag", "embeddings", "vector-db"],
        },
    ]


def main() -> None:
    client = QdrantClient("localhost", port=6333)
    encoder = SentenceTransformer(MODEL_NAME)

    docs = build_sample_data()
    texts = [doc["text"] for doc in docs]
    vectors = encoder.encode(texts, normalize_embeddings=True)
    vector_size = len(vectors[0])

    # Drop and recreate for a clean index.
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
        print(f"Dropped existing '{COLLECTION_NAME}' collection.")

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE,
        ),
    )

    points = [
        models.PointStruct(
            id=doc["id"],
            vector=vectors[idx].tolist(),
            payload={
                "text": doc["text"],
                "years_exp": doc["years_exp"],
                "role": doc["role"],
                "skills": doc["skills"],
            },
        )
        for idx, doc in enumerate(docs)
    ]

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"Indexed {len(points)} documents into '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    main()
