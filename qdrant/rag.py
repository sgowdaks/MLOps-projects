"""Combined single-script experiment (index + query in one run).

For the split index-once / query-via-HTTP workflow, use:
  1. python qdrant/index.py          — embed and store data (run once)
  2. uvicorn qdrant.query_api:app --port 8001  — start the search API
  3. curl -X POST http://localhost:8001/search  — query at any time
"""

from __future__ import annotations

import os
from typing import Any

# Use GPU 0 (RTX A6000, sm_86) — GPU 1 (TITAN X Pascal, sm_61) is not
# supported by this PyTorch build (requires sm_70+).
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

    # Recreate for a clean experiment run.
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)

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

    query_text = "Need an engineer for production RAG and NLP work"
    query_vector = encoder.encode(query_text, normalize_embeddings=True).tolist()

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="years_exp",
                    range=models.Range(gte=3),
                )
            ]
        ),
        limit=3,
    )

    print(f"\nQuery: {query_text}")
    print("Top matches (years_exp >= 3):")
    for rank, hit in enumerate(results.points, start=1):
        payload = hit.payload or {}
        print(
            f"{rank}. id={hit.id} score={hit.score:.4f} "
            f"role={payload.get('role')} years_exp={payload.get('years_exp')}"
        )
        print(f"   text={payload.get('text')}")


if __name__ == "__main__":
    main()