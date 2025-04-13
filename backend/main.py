# eidbi-query-system/backend/main.py

import logging
from fastapi import FastAPI, HTTPException, Body
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

# Assuming embedding_service is within app/services
# Adjust imports based on your actual backend structure
try:
    from app.services.embedding_service import initialize_vertex_ai_once, generate_embeddings
    from app.services.vector_db_service import find_neighbors
    from app.services.llm_service import generate_text_response # Import LLM service
    # Assume GCS utils are now in backend utils or accessible via shared path
    import sys
    import os
    SERVICE_DIR = os.path.dirname(__file__)
    APP_DIR = os.path.dirname(SERVICE_DIR)
    BACKEND_DIR = os.path.dirname(APP_DIR)
    PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
    UTILS_PATH = os.path.join(PROJECT_ROOT, 'scraper', 'utils') # Path to shared utils
    if UTILS_PATH not in sys.path:
         sys.path.append(UTILS_PATH)
    from utils.gcs_utils import read_json_from_gcs
    from config.settings import settings # Import settings for bucket name
except ImportError as e:
    print(f"Failed to import services or utils: {e}")
    # Define dummy functions if import fails, to allow basic app run
    def initialize_vertex_ai_once(): return False
    def generate_embeddings(texts: List[str]) -> Optional[List[Optional[List[float]]]]: return None
    def find_neighbors(query_embedding: List[float]) -> List[Dict[str, Any]]: return []
    def generate_text_response(prompt: str) -> Optional[str]: return "LLM Service unavailable."
    def read_json_from_gcs(bucket: str, blob: str) -> Optional[Dict]: return None
    settings = None # Fallback


# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')
logger = logging.getLogger(__name__)

# --- Application Lifecycle (Startup/Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Vertex AI
    logger.info("Application starting up...")
    if not initialize_vertex_ai_once():
        logger.error("FATAL: Vertex AI Initialization failed on startup. Embedding endpoint will not work.")
        # Depending on requirements, you might want to exit here or let it run degraded
    yield
    # Shutdown: Cleanup (if any needed)
    logger.info("Application shutting down...")

# --- FastAPI App Instance ---
app = FastAPI(
    title="EIDBI Backend API",
    description="API for processing and querying EIDBI data.",
    version="0.1.0",
    lifespan=lifespan # Register startup/shutdown events
)

# --- API Models ---
class QueryRequest(BaseModel):
    query_text: str
    num_results: int = 5 # Default to 5 neighbors

class NeighborResult(BaseModel):
    chunk_id: str
    distance: float

class QueryResponse(BaseModel):
    query: str
    answer: str
    retrieved_chunk_ids: List[str]

# --- Helper Function ---
def construct_llm_prompt(query: str, context_chunks: List[Dict[str, Any]]) -> str:
    """Constructs a prompt for the LLM using retrieved context."""
    context = "\n\n---\n\n".join([chunk.get('content', '') for chunk in context_chunks])
    prompt = f"""You are an expert assistant knowledgeable about the Minnesota EIDBI program.
Answer the following question based *only* on the provided context. If the context does not contain the answer, say 'I cannot answer the question based on the provided information.'

Question: {query}

Context:
{context}

Answer:"""
    return prompt

# --- API Endpoints ---
@app.get("/")
async def read_root():
    return {"message": "Welcome to the EIDBI Backend API"}

@app.post("/generate-embeddings", response_model=List[Optional[List[float]]])
async def get_embeddings(texts: List[str] = Body(..., embed=True, description="List of texts to embed.")):
    """
    Generates vector embeddings for a list of input texts using Vertex AI.
    """
    logger.info(f"Received request to generate embeddings for {len(texts)} text(s).")
    if not texts:
        raise HTTPException(status_code=400, detail="No texts provided.")

    embeddings = generate_embeddings(texts)

    if embeddings is None:
        # This indicates a failure within generate_embeddings, likely logged already
        raise HTTPException(status_code=500, detail="Failed to generate embeddings. Check server logs.")

    # Check if any individual embedding failed (returned as None in the list)
    failed_count = sum(1 for emb in embeddings if emb is None)
    if failed_count > 0:
         logger.warning(f"Embedding failed for {failed_count}/{len(texts)} input texts.")
         # Decide response: you could return partial results or raise an error.
         # Returning partial results here.
         # raise HTTPException(status_code=507, detail=f"Embedding failed for {failed_count} texts.")


    logger.info(f"Successfully processed embedding request. Returning {len(embeddings)} results.")
    return embeddings

@app.post("/query", response_model=QueryResponse)
async def perform_query(request: QueryRequest):
    """
    Receives text query, generates embedding, finds neighbors, retrieves chunk text,
    prompts LLM, and returns the synthesized answer.
    """
    logger.info(f"Received query: '{request.query_text}', num_results: {request.num_results}")

    # 1. Generate embedding for the query
    query_embedding_list = generate_embeddings([request.query_text])
    if not query_embedding_list or query_embedding_list[0] is None:
        logger.error(f"Failed to generate embedding for query: '{request.query_text}'")
        raise HTTPException(status_code=500, detail="Failed to generate query embedding.")
    query_embedding = query_embedding_list[0]

    # 2. Find nearest neighbor chunk IDs in Vector DB
    neighbors = find_neighbors(
        query_embedding=query_embedding,
        num_neighbors_override=request.num_results
    )
    if neighbors is None or not neighbors:
        logger.warning(f"No neighbors found for query: '{request.query_text}'")
        return QueryResponse(query=request.query_text, answer="Could not find relevant information.", retrieved_chunk_ids=[])

    neighbor_ids = [nid for nid, dist in neighbors]
    logger.info(f"Found neighbor chunk IDs: {neighbor_ids}")

    # 3. Retrieve content for neighbor chunks from GCS
    retrieved_chunks_content: List[Dict[str, Any]] = []
    gcs_bucket_name = settings.gcp.bucket_name if settings else None
    if not gcs_bucket_name:
        logger.error("GCS_BUCKET_NAME not configured. Cannot retrieve chunk content.")
        raise HTTPException(status_code=500, detail="Server configuration error [GCS Bucket].")

    for chunk_id in neighbor_ids:
        blob_name = f"chunks/{chunk_id}.json" # Assumes chunks stored in 'chunks/' prefix
        chunk_data = read_json_from_gcs(gcs_bucket_name, blob_name)
        if chunk_data:
            retrieved_chunks_content.append(chunk_data)
        else:
            logger.warning(f"Could not retrieve content for chunk ID: {chunk_id} from GCS.")

    if not retrieved_chunks_content:
        logger.error(f"Found neighbor IDs {neighbor_ids} but failed to retrieve content for any of them.")
        raise HTTPException(status_code=500, detail="Failed to retrieve context for search results.")

    # 4. Construct Prompt and Query LLM
    prompt = construct_llm_prompt(request.query_text, retrieved_chunks_content)
    logger.debug(f"Generated LLM Prompt:\n{prompt}")

    llm_answer = generate_text_response(prompt)

    if llm_answer is None:
        logger.error("LLM failed to generate a response.")
        raise HTTPException(status_code=500, detail="AI failed to generate an answer.")

    # 5. Format and Return Response
    logger.info("Successfully generated LLM answer.")
    return QueryResponse(
        query=request.query_text,
        answer=llm_answer.strip(),
        retrieved_chunk_ids=neighbor_ids
    )

# --- Run with Uvicorn (for local development) ---
# Run using: uvicorn main:app --reload --host 0.0.0.0 --port 8000
# (Assuming you are in the 'backend' directory) 