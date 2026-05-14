import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict
from transformers import pipeline

# Global dictionary to hold the loaded model
models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Load Model Once on Startup ---
    print("🚀 Loading Hugging Face sentiment model...")
    # This might take a few seconds the first time (downloads the weights)
    models["sentiment_analyzer"] = pipeline(
        "sentiment-analysis", 
        model="distilbert-base-uncased-finetuned-sst-2-english"
    )
    yield
    # --- Cleanup on Shutdown ---
    models.clear()
    print("🛑 Model cleared from memory.")

app = FastAPI(lifespan=lifespan)

# --- Data Schemas ---
class SingleText(BaseModel):
    text: str

class BatchText(BaseModel):
    texts: List[str]

# --- Endpoints ---

@app.get("/")
def health_check():
    return {"status": "online", "model": "distilbert-sentiment"}

@app.post("/predict/realtime")
async def predict_single(data: SingleText):
    """Real-time: Returns a sentiment score immediately."""
    result = models["sentiment_analyzer"](data.text)
    return {"input": data.text, "prediction": result[0]}

@app.post("/predict/batch")
async def predict_batch(data: BatchText, background_tasks: BackgroundTasks):
    """Batch: Returns 202 immediately, processes list in the background."""
    # We trigger the task and return a response instantly
    background_tasks.add_task(process_large_batch, data.texts)
    return {
        "message": f"Processing {len(data.texts)} items in the background.",
        "status": "accepted"
    }

# --- Background Task Simulation ---
async def process_large_batch(texts: List[str]):
    print(f"📦 Starting batch process for {len(texts)} items...")
    
    # In a real app, you'd save these results to a database
    results = models["sentiment_analyzer"](texts)
    
    # Simulate work (e.g., writing to DB)
    await asyncio.sleep(2) 
    print(f"✅ Batch complete. Sample result: {results[0]}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
