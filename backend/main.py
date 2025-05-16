# eidbi-query-system/backend/main.py

import logging
from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import sys
import os
import time
import hashlib
import json
from functools import lru_cache

# --- Logging Setup (Moved before imports) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')
logger = logging.getLogger(__name__) # Initialize logger early

# --- Adjust Python Path & Import Services ---
# Correctly calculate the project root and add it (if necessary)
try:
    MAIN_PY_PATH = os.path.abspath(__file__)
    BACKEND_DIR = os.path.dirname(MAIN_PY_PATH)
    PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

    # Add project root to sys.path if not already present (often needed for imports like 'config')
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    # Use imports relative to the project root
    from backend.app.services.embedding_service import initialize_vertex_ai, generate_embeddings
    from backend.app.services.vector_db_service import find_neighbors, get_chunk_by_id
    from backend.app.services.llm_service import generate_text_response
    from scraper.utils.gcs_utils import read_json_from_gcs # Import from scraper.utils
    from config.settings import settings # Import from config

except ImportError as e:
    logger.error(f"Failed to import services or utils: {e}", exc_info=True) # Logger is now defined
    # Define dummy functions if import fails, to allow basic app run
    def initialize_vertex_ai(): return False
    def generate_embeddings(texts: List[str]) -> Optional[List[Optional[List[float]]]]: return None
    def find_neighbors(query_embedding: List[float]) -> List[Dict[str, Any]]: return []
    def generate_text_response(prompt: str) -> Optional[str]: return "LLM Service unavailable."
    def read_json_from_gcs(bucket: str, blob: str) -> Optional[Dict]: return None
    def get_chunk_by_id(chunk_id: str) -> Optional[Dict[str, Any]]: return None
    settings = None # Fallback

# --- System Version ---
APP_VERSION = "1.1.0"

# --- Cache Configuration ---
# Get cache settings from environment variables or use defaults
ENABLE_EMBEDDING_CACHE = os.getenv("ENABLE_EMBEDDING_CACHE", "true").lower() == "true"
ENABLE_QUERY_CACHE = os.getenv("ENABLE_QUERY_CACHE", "true").lower() == "true"
EMBEDDING_CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "100"))
QUERY_CACHE_SIZE = int(os.getenv("QUERY_CACHE_SIZE", "50"))

# Cache decorator for embedding generation
@lru_cache(maxsize=EMBEDDING_CACHE_SIZE)
def cached_generate_embeddings(text: str) -> Optional[List[float]]:
    """Generate embeddings with caching for a single text."""
    if not ENABLE_EMBEDDING_CACHE:
        # If cache is disabled, just pass through to the regular function
        embeddings = generate_embeddings([text])
        return embeddings[0] if embeddings and embeddings[0] is not None else None
    
    # Generate embedding with caching
    logger.info(f"Generating embedding for text (length={len(text)})")
    result = generate_embeddings([text])
    if result and result[0] is not None:
        logger.info("Successfully generated embedding with caching")
        return result[0]
    else:
        logger.warning("Failed to generate embedding")
        return None

# Cache for query responses
class QueryCache:
    def __init__(self, max_size=50):
        self.cache = {}
        self.max_size = max_size
        self.keys_by_access_time = []
    
    def _get_key(self, query_text: str, num_results: int, simple_mode: bool) -> str:
        """Generate a deterministic cache key from the query parameters."""
        key_data = f"{query_text}:{num_results}:{simple_mode}".encode('utf-8')
        return hashlib.md5(key_data).hexdigest()
    
    def get(self, query_text: str, num_results: int, simple_mode: bool) -> Optional[Dict[str, Any]]:
        """Get a cached query result if it exists."""
        if not ENABLE_QUERY_CACHE:
            return None
            
        key = self._get_key(query_text, num_results, simple_mode)
        result = self.cache.get(key)
        
        if result:
            # Update access time by moving key to end of list
            if key in self.keys_by_access_time:
                self.keys_by_access_time.remove(key)
            self.keys_by_access_time.append(key)
            logger.info(f"Query cache hit for: '{query_text}'")
            
        return result
    
    def set(self, query_text: str, num_results: int, simple_mode: bool, result: Dict[str, Any]) -> None:
        """Store a query result in the cache."""
        if not ENABLE_QUERY_CACHE:
            return
            
        key = self._get_key(query_text, num_results, simple_mode)
        
        # If cache is full, remove least recently used item
        if len(self.cache) >= self.max_size and self.keys_by_access_time:
            oldest_key = self.keys_by_access_time.pop(0)
            if oldest_key in self.cache:
                del self.cache[oldest_key]
        
        # Store new result
        self.cache[key] = result
        self.keys_by_access_time.append(key)
        logger.info(f"Cached query result for: '{query_text}'")
    
    def clear(self) -> None:
        """Clear the entire cache."""
        self.cache = {}
        self.keys_by_access_time = []
        logger.info("Query cache cleared")

# Initialize query cache
query_cache = QueryCache(max_size=QUERY_CACHE_SIZE)

# --- Application Lifecycle (Startup/Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Vertex AI
    logger.info(f"Application starting up (version {APP_VERSION})...")
    logger.info(f"Cache settings: Embedding cache: {ENABLE_EMBEDDING_CACHE} (size={EMBEDDING_CACHE_SIZE}), Query cache: {ENABLE_QUERY_CACHE} (size={QUERY_CACHE_SIZE})")
    
    # Initialize settings once at startup
    if settings:
        logger.info(f"Loaded configuration: API port={settings.api.port}, Debug={settings.api.debug}")
        if not settings.gcp.bucket_name:
            logger.warning("GCP_BUCKET_NAME not configured. Will use local file fallback only.")
    else:
        logger.warning("Settings not properly loaded. Running with defaults.")
    
    # Initialize embedding service
    if not initialize_vertex_ai():
        logger.error("FATAL: Vertex AI Initialization failed on startup. Embedding endpoint will not work.")
        # Depending on requirements, you might want to exit here or let it run degraded
    
    yield
    
    # Shutdown: Cleanup (if any needed)
    logger.info("Application shutting down...")

# --- FastAPI App Instance ---
app = FastAPI(
    title="EIDBI Backend API",
    description="API for processing and querying EIDBI data.",
    version=APP_VERSION,
    lifespan=lifespan # Register startup/shutdown events
)

# --- Add CORS middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you'd want to restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request timing middleware ---
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# --- Exception handlers ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log the error with full traceback
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
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
    version: str = APP_VERSION
    cached: bool = False

class CacheStatsResponse(BaseModel):
    embedding_cache_enabled: bool
    embedding_cache_size: int
    embedding_cache_max_size: int
    query_cache_enabled: bool
    query_cache_size: int 
    query_cache_max_size: int

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
    return {
        "message": "Welcome to the EIDBI Backend API",
        "version": APP_VERSION,
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "timestamp": time.time()
    }

@app.get("/cache-stats")
async def cache_stats():
    """Get cache statistics."""
    return CacheStatsResponse(
        embedding_cache_enabled=ENABLE_EMBEDDING_CACHE,
        embedding_cache_size=cached_generate_embeddings.cache_info().currsize if ENABLE_EMBEDDING_CACHE else 0,
        embedding_cache_max_size=EMBEDDING_CACHE_SIZE,
        query_cache_enabled=ENABLE_QUERY_CACHE,
        query_cache_size=len(query_cache.cache),
        query_cache_max_size=QUERY_CACHE_SIZE
    )

@app.post("/clear-cache")
async def clear_cache():
    """Clear all caches."""
    if ENABLE_EMBEDDING_CACHE:
        cached_generate_embeddings.cache_clear()
    
    query_cache.clear()
    
    return {
        "message": "All caches cleared successfully",
        "timestamp": time.time()
    }

@app.post("/simple-answer")
async def simple_answer(query_text: str = Body(..., embed=True, description="Question to answer")):
    """
    Provides a direct answer to a question without using the vector database.
    This is a simplified endpoint for testing when vector DB isn't configured.
    """
    logger.info(f"Received simple answer request: '{query_text}'")
    
    # Check cache first
    cached_result = query_cache.get(query_text, 0, True)
    if cached_result:
        cached_result["cached"] = True
        return cached_result
    
    try:
        prompt = f"""You are an expert assistant knowledgeable about the Minnesota EIDBI program.
Answer the following question as best you can with general knowledge.

Question: {query_text}

Answer:"""
        
        answer = generate_text_response(prompt)
        
        # LLM service now provides fallback responses instead of None
        # But we still validate that we have a response
        if not answer:
            logger.error("LLM failed to generate a response for simple-answer.")
            answer = "I apologize, but I'm unable to provide an answer at this time. Please try again later."
        
        result = {
            "query": query_text,
            "answer": answer.strip(),
            "note": "This response is based on general model knowledge, not specific document retrieval.",
            "version": APP_VERSION,
            "cached": False,
            "retrieved_chunk_ids": []  # Empty for simple answers
        }
        
        # Cache the result
        query_cache.set(query_text, 0, True, result)
        
        return result
    except Exception as e:
        logger.error(f"Error generating simple answer: {e}", exc_info=True)
        # Provide a friendly response even when things go wrong
        return {
            "query": query_text,
            "answer": "I apologize, but I'm having technical difficulties generating a response. Please try again later.",
            "note": "This is a fallback response due to a backend error. Error details have been logged for investigation.",
            "version": APP_VERSION,
            "cached": False,
            "retrieved_chunk_ids": []
        }

@app.post("/generate-embeddings", response_model=List[Optional[List[float]]])
async def get_embeddings(texts: List[str] = Body(..., embed=True, description="List of texts to embed.")):
    """
    Generates vector embeddings for a list of input texts using Vertex AI.
    """
    logger.info(f"Received request to generate embeddings for {len(texts)} text(s).")
    if not texts:
        raise HTTPException(status_code=400, detail="No texts provided.")

    # Handle multiple texts by using cached_generate_embeddings for each text
    if ENABLE_EMBEDDING_CACHE:
        embeddings = []
        for text in texts:
            emb = cached_generate_embeddings(text)
            embeddings.append(emb)
    else:
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
    
    query_start_time = time.time()
    
    # Check cache first 
    cached_result = query_cache.get(request.query_text, request.num_results, False)
    if cached_result:
        return QueryResponse(**cached_result)

    # 1. Generate embedding for the query
    query_embedding = None
    if ENABLE_EMBEDDING_CACHE:
        query_embedding = cached_generate_embeddings(request.query_text)
    else:
        query_embedding_list = generate_embeddings([request.query_text])
        query_embedding = query_embedding_list[0] if query_embedding_list and query_embedding_list[0] is not None else None

    if query_embedding is None:
        logger.error(f"Failed to generate embedding for query: '{request.query_text}'")
        raise HTTPException(status_code=500, detail="Failed to generate query embedding.")

    # 2. Find nearest neighbor chunk IDs in Vector DB
    neighbors = find_neighbors(
        query_embedding=query_embedding,
        num_neighbors_override=request.num_results
    )
    if neighbors is None or not neighbors:
        logger.warning(f"No neighbors found for query: '{request.query_text}'")
        
        # If no relevant chunks found, fall back to simple answer
        logger.info("Falling back to simple answer mode")
        
        prompt = f"""You are an expert assistant knowledgeable about the Minnesota EIDBI program.
Answer the following question as best you can with general knowledge.

Question: {request.query_text}

Answer:"""
        
        fallback_answer = generate_text_response(prompt)
        if not fallback_answer:
            fallback_answer = "Could not find relevant information about this topic in the EIDBI documentation."
            
        result = {
            "query": request.query_text,
            "answer": fallback_answer + "\n\n(Note: This response is based on general knowledge as no matching content was found in the database.)",
            "retrieved_chunk_ids": [],
            "version": APP_VERSION,
            "cached": False
        }
        
        # Cache the result
        query_cache.set(request.query_text, request.num_results, False, result)
        
        return QueryResponse(**result)

    neighbor_ids = [nid for nid, dist in neighbors]
    logger.info(f"Found neighbor chunk IDs: {neighbor_ids}")

    # 3. Retrieve content for neighbor chunks
    retrieved_chunks_content: List[Dict[str, Any]] = []
    
    # First try to get the chunks from local file
    logger.info("Retrieving chunks from local file...")
    for chunk_id in neighbor_ids:
        chunk = get_chunk_by_id(chunk_id)
        if chunk:
            retrieved_chunks_content.append(chunk)
            logger.debug(f"Retrieved chunk {chunk_id} from local file")
        else:
            logger.warning(f"Could not find chunk {chunk_id} in local file")
    
    # If local retrieval was successful, skip GCS
    if retrieved_chunks_content:
        logger.info(f"Successfully retrieved {len(retrieved_chunks_content)} chunks from local file")
    else:
        # Try GCS as fallback
        gcs_bucket_name = settings.gcp.bucket_name if settings else None
        if gcs_bucket_name:
            logger.info(f"Trying to retrieve chunks from GCS bucket: {gcs_bucket_name}")
            try:
                for chunk_id in neighbor_ids:
                    blob_name = f"chunks/{chunk_id}.json"
                    chunk_data = read_json_from_gcs(gcs_bucket_name, blob_name)
                    if chunk_data:
                        retrieved_chunks_content.append(chunk_data)
                    else:
                        logger.warning(f"Could not retrieve content for chunk ID: {chunk_id} from GCS.")
                
                if retrieved_chunks_content:
                    logger.info(f"Successfully retrieved {len(retrieved_chunks_content)} chunks from GCS")
            except Exception as e:
                logger.error(f"Error retrieving chunks from GCS: {e}")
    
    if not retrieved_chunks_content:
        logger.error(f"Failed to retrieve content for any of the matching IDs: {neighbor_ids}")
        # Fall back to simple answer instead of raising an exception
        prompt = f"""You are an expert assistant knowledgeable about the Minnesota EIDBI program.
Answer the following question as best you can with general knowledge.

Question: {request.query_text}

Answer:"""
        
        fallback_answer = generate_text_response(prompt)
        if not fallback_answer:
            fallback_answer = "I apologize, but I could not retrieve the relevant content to answer your question accurately."
            
        result = {
            "query": request.query_text,
            "answer": fallback_answer + "\n\n(Note: This response is based on general knowledge as there was an error retrieving specific content.)",
            "retrieved_chunk_ids": [],
            "cached": False,
            "version": APP_VERSION
        }
        
        # Cache the result
        query_cache.set(request.query_text, request.num_results, False, result)
        
        return QueryResponse(**result)

    # 4. Construct Prompt and Query LLM
    prompt = construct_llm_prompt(request.query_text, retrieved_chunks_content)
    logger.debug(f"Generated LLM Prompt:\n{prompt}")

    llm_answer = generate_text_response(prompt)

    if llm_answer is None:
        logger.error("LLM failed to generate a response.")
        raise HTTPException(status_code=500, detail="AI failed to generate an answer.")

    # 5. Format and Return Response
    query_duration_ms = int((time.time() - query_start_time) * 1000)
    logger.info(f"Successfully generated LLM answer in {query_duration_ms}ms")
    
    result = {
        "query": request.query_text,
        "answer": llm_answer.strip(),
        "retrieved_chunk_ids": neighbor_ids,
        "cached": False,
        "version": APP_VERSION
    }
    
    # Cache the result
    query_cache.set(request.query_text, request.num_results, False, result)
    
    return QueryResponse(**result)

# Add script entry point to run directly
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run("main:app", host=host, port=port) 