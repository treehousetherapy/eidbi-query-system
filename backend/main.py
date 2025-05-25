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

# --- Import Services ---
try:
    # Import services (using relative imports since we're in backend directory)
    from app.services.embedding_service import initialize_vertex_ai, generate_embeddings
    from app.services.vector_db_service import find_neighbors, get_chunk_by_id, hybrid_search, get_chunks_by_ids
    from app.services.llm_service import generate_text_response
    from app.services.query_enhancer import query_enhancer
    from app.services.reranker import reranker
    
    # Import new enhanced services
    from app.services.feedback_service import feedback_service, FeedbackType, FeedbackCategory
    from app.services.prompt_engineering import prompt_service, QueryType, ResponseFormat
    from app.services.data_source_integration import data_integration_service
    
    # Import utilities and config (now local to backend)
    from utils.gcs_utils import read_json_from_gcs
    from config.settings import settings

except ImportError as e:
    logger.error(f"Failed to import services or utils: {e}", exc_info=True)
    # Define dummy functions if import fails, to allow basic app run
    def initialize_vertex_ai(): return False
    def generate_embeddings(texts: List[str]) -> Optional[List[Optional[List[float]]]]: return None
    def find_neighbors(query_embedding: List[float]) -> List[Dict[str, Any]]: return []
    def generate_text_response(prompt: str) -> Optional[str]: return "LLM Service unavailable."
    def read_json_from_gcs(bucket: str, blob: str) -> Optional[Dict]: return None
    def get_chunk_by_id(chunk_id: str) -> Optional[Dict[str, Any]]: return None
    def hybrid_search(query_embedding, keywords, num_results=10): return []
    def get_chunks_by_ids(chunk_ids): return []
    settings = None # Fallback
    query_enhancer = None
    reranker = None
    feedback_service = None
    prompt_service = None
    data_integration_service = None

# --- System Version ---
APP_VERSION = "2.0.0"  # Updated version for enhanced features

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
    
    # Initialize data source integration service
    if data_integration_service:
        logger.info("Initializing data source integration service...")
        try:
            # Perform initial data source update in background
            import asyncio
            asyncio.create_task(data_integration_service.update_all_sources())
        except Exception as e:
            logger.warning(f"Failed to initialize data source updates: {e}")
    
    yield
    
    # Shutdown: Cleanup (if any needed)
    logger.info("Application shutting down...")

# --- FastAPI App Instance ---
app = FastAPI(
    title="Enhanced EIDBI Backend API",
    description="API for processing and querying EIDBI data with enhanced search capabilities, feedback loops, and multi-source integration.",
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

# --- Enhanced API Models ---
class QueryRequest(BaseModel):
    query_text: str
    num_results: int = 5 # Default to 5 neighbors
    use_hybrid_search: bool = True  # Enable hybrid search by default
    use_reranking: bool = True  # Enable reranking by default
    use_enhanced_prompts: bool = True  # Enable enhanced prompt engineering
    use_additional_sources: bool = True  # Enable additional data sources
    user_session_id: Optional[str] = None  # For tracking user sessions

class NeighborResult(BaseModel):
    chunk_id: str
    distance: float

class QueryResponse(BaseModel):
    query: str
    answer: str
    retrieved_chunk_ids: List[str]
    version: str = APP_VERSION
    cached: bool = False
    search_method: str = "hybrid"  # "vector", "hybrid", or "keyword"
    query_type: Optional[str] = None  # Detected query type
    response_format: Optional[str] = None  # Used response format
    sources_used: Optional[List[str]] = None  # Data sources used
    prompt_metadata: Optional[Dict[str, Any]] = None  # Prompt engineering metadata

class FeedbackRequest(BaseModel):
    query_text: str
    response_text: str
    feedback_type: str  # "thumbs_up", "thumbs_down", "rating", "detailed"
    rating: Optional[int] = None  # 1-5 scale
    categories: Optional[List[str]] = None  # List of feedback categories
    detailed_feedback: Optional[str] = None
    retrieved_chunk_ids: Optional[List[str]] = None
    search_method: Optional[str] = None
    user_session_id: Optional[str] = None

class CacheStatsResponse(BaseModel):
    embedding_cache_enabled: bool
    embedding_cache_size: int
    embedding_cache_max_size: int
    query_cache_enabled: bool
    query_cache_size: int 
    query_cache_max_size: int

# --- Helper Function ---
def construct_llm_prompt(query: str, context_chunks: List[Dict[str, Any]], use_enhanced_prompts: bool = True) -> tuple[str, Dict[str, Any]]:
    """Constructs a prompt for the LLM using retrieved context."""
    if use_enhanced_prompts and prompt_service:
        # Use enhanced prompt engineering
        prompt = prompt_service.construct_enhanced_prompt(query, context_chunks)
        metadata = prompt_service.get_prompt_metadata(query)
        return prompt, metadata
    else:
        # Use basic prompt
        context = "\n\n---\n\n".join([chunk.get('content', '') for chunk in context_chunks])
        prompt = f"""You are an expert assistant knowledgeable about the Minnesota EIDBI program.
Answer the following question based *only* on the provided context. If the context does not contain the answer, say 'I cannot answer the question based on the provided information.'

Question: {query}

Context:
{context}

Answer:"""
        metadata = {"query_type": "general", "response_format": "basic", "template_used": "basic"}
        return prompt, metadata

# --- API Endpoints ---
@app.get("/")
async def read_root():
    return {
        "message": "Welcome to the Enhanced EIDBI Backend API",
        "version": APP_VERSION,
        "status": "healthy",
        "features": [
            "query_expansion", 
            "hybrid_search", 
            "reranking", 
            "enhanced_caching",
            "feedback_loops",
            "enhanced_prompt_engineering",
            "multi_source_integration",
            "automated_testing"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "timestamp": time.time(),
        "services": {
            "feedback_service": feedback_service is not None,
            "prompt_service": prompt_service is not None,
            "data_integration_service": data_integration_service is not None
        }
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

# --- Feedback Endpoints ---
@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Submit user feedback for query responses."""
    if not feedback_service:
        raise HTTPException(status_code=503, detail="Feedback service not available")
    
    try:
        # Convert string enums to enum objects
        feedback_type = FeedbackType(feedback.feedback_type)
        categories = [FeedbackCategory(cat) for cat in feedback.categories] if feedback.categories else None
        
        feedback_id = feedback_service.submit_feedback(
            query_text=feedback.query_text,
            response_text=feedback.response_text,
            feedback_type=feedback_type,
            rating=feedback.rating,
            categories=categories,
            detailed_feedback=feedback.detailed_feedback,
            retrieved_chunk_ids=feedback.retrieved_chunk_ids,
            search_method=feedback.search_method,
            user_session_id=feedback.user_session_id
        )
        
        return {
            "feedback_id": feedback_id,
            "message": "Feedback submitted successfully",
            "timestamp": time.time()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")

@app.get("/feedback/stats")
async def get_feedback_stats(days: int = 30):
    """Get feedback statistics."""
    if not feedback_service:
        raise HTTPException(status_code=503, detail="Feedback service not available")
    
    try:
        stats = feedback_service.get_feedback_stats(days=days)
        return stats
    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get feedback statistics")

@app.get("/feedback/problematic-queries")
async def get_problematic_queries(min_feedback_count: int = 2):
    """Get queries that consistently receive poor feedback."""
    if not feedback_service:
        raise HTTPException(status_code=503, detail="Feedback service not available")
    
    try:
        problematic = feedback_service.get_problematic_queries(min_feedback_count=min_feedback_count)
        return {
            "problematic_queries": problematic,
            "count": len(problematic)
        }
    except Exception as e:
        logger.error(f"Error getting problematic queries: {e}")
        raise HTTPException(status_code=500, detail="Failed to get problematic queries")

@app.get("/feedback/improvement-suggestions")
async def get_improvement_suggestions():
    """Get improvement suggestions based on feedback patterns."""
    if not feedback_service:
        raise HTTPException(status_code=503, detail="Feedback service not available")
    
    try:
        suggestions = feedback_service.get_improvement_suggestions()
        return {
            "suggestions": suggestions,
            "count": len(suggestions)
        }
    except Exception as e:
        logger.error(f"Error getting improvement suggestions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get improvement suggestions")

# --- Data Source Integration Endpoints ---
@app.get("/data-sources/status")
async def get_data_sources_status():
    """Get status of all data sources."""
    if not data_integration_service:
        raise HTTPException(status_code=503, detail="Data integration service not available")
    
    try:
        status = data_integration_service.get_source_status()
        return status
    except Exception as e:
        logger.error(f"Error getting data source status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get data source status")

@app.post("/data-sources/update")
async def update_data_sources(force_update: bool = False):
    """Update content from all data sources."""
    if not data_integration_service:
        raise HTTPException(status_code=503, detail="Data integration service not available")
    
    try:
        result = await data_integration_service.update_all_sources(force_update=force_update)
        return result
    except Exception as e:
        logger.error(f"Error updating data sources: {e}")
        raise HTTPException(status_code=500, detail="Failed to update data sources")

# --- Enhanced Query Endpoint ---
@app.post("/query", response_model=QueryResponse)
async def perform_query(request: QueryRequest):
    """
    Enhanced query endpoint with query expansion, hybrid search, reranking,
    enhanced prompt engineering, feedback integration, and multi-source data.
    """
    logger.info(f"Received enhanced query: '{request.query_text}', num_results: {request.num_results}")
    logger.info(f"Options: hybrid_search={request.use_hybrid_search}, reranking={request.use_reranking}, enhanced_prompts={request.use_enhanced_prompts}, additional_sources={request.use_additional_sources}")
    
    query_start_time = time.time()
    
    # Check cache first 
    cached_result = query_cache.get(request.query_text, request.num_results, False)
    if cached_result:
        return QueryResponse(**cached_result)

    # 1. Query Enhancement - Expand the query
    if query_enhancer:
        expanded_queries = query_enhancer.expand_query(request.query_text)
        keywords = query_enhancer.extract_keywords(request.query_text)
        logger.info(f"Expanded to {len(expanded_queries)} queries, extracted {len(keywords)} keywords")
    else:
        expanded_queries = [request.query_text]
        keywords = request.query_text.lower().split()

    # 2. Generate embeddings for expanded queries
    all_embeddings = []
    for query in expanded_queries[:3]:  # Limit to first 3 expansions for efficiency
        if ENABLE_EMBEDDING_CACHE:
            query_embedding = cached_generate_embeddings(query)
        else:
            query_embedding_list = generate_embeddings([query])
            query_embedding = query_embedding_list[0] if query_embedding_list and query_embedding_list[0] is not None else None
        
        if query_embedding:
            all_embeddings.append(query_embedding)

    if not all_embeddings:
        logger.error(f"Failed to generate any embeddings for query: '{request.query_text}'")
        raise HTTPException(status_code=500, detail="Failed to generate query embedding.")

    # Use the first embedding as primary (original query)
    primary_embedding = all_embeddings[0]

    # 3. Perform search (hybrid or vector-only)
    search_results = []
    sources_used = []
    
    # Primary search in vector database
    if request.use_hybrid_search:
        # Hybrid search combining vector and keyword
        primary_results = hybrid_search(
            query_embedding=primary_embedding,
            keywords=keywords,
            num_results=request.num_results * 2  # Get more for reranking
        )
        search_method = "hybrid"
    else:
        # Traditional vector-only search
        primary_results = find_neighbors(
            query_embedding=primary_embedding,
            num_neighbors_override=request.num_results * 2
        )
        search_method = "vector"
    
    search_results.extend(primary_results)
    sources_used.append("primary_vector_db")
    
    # Additional sources search
    if request.use_additional_sources and data_integration_service:
        try:
            additional_content = data_integration_service.get_content_for_query(
                request.query_text, 
                max_sources=2
            )
            
            if additional_content:
                logger.info(f"Found {len(additional_content)} additional content items")
                # Convert additional content to search result format
                for item in additional_content:
                    # Create a pseudo chunk ID for additional content
                    chunk_id = f"additional_{hashlib.md5(item['url'].encode()).hexdigest()[:8]}"
                    search_results.append((chunk_id, 0.8))  # Give it a good similarity score
                    sources_used.append(item.get('source_name', 'additional_source'))
        except Exception as e:
            logger.warning(f"Failed to get additional sources: {e}")

    if not search_results:
        logger.warning(f"No results found for query: '{request.query_text}'")
        
        # Fall back to simple answer
        logger.info("Falling back to simple answer mode")
        
        if request.use_enhanced_prompts and prompt_service:
            prompt, prompt_metadata = construct_llm_prompt(request.query_text, [], request.use_enhanced_prompts)
        else:
            prompt = f"""You are an expert assistant knowledgeable about the Minnesota EIDBI program.
Answer the following question as best you can with general knowledge.

Question: {request.query_text}

Answer:"""
            prompt_metadata = {"query_type": "general", "response_format": "basic"}
        
        fallback_answer = generate_text_response(prompt)
        if not fallback_answer:
            fallback_answer = "Could not find relevant information about this topic in the EIDBI documentation."
            
        result = {
            "query": request.query_text,
            "answer": fallback_answer + "\n\n(Note: This response is based on general knowledge as no matching content was found in the database.)",
            "retrieved_chunk_ids": [],
            "version": APP_VERSION,
            "cached": False,
            "search_method": search_method,
            "query_type": prompt_metadata.get("query_type"),
            "response_format": prompt_metadata.get("response_format"),
            "sources_used": sources_used,
            "prompt_metadata": prompt_metadata
        }
        
        # Cache the result
        query_cache.set(request.query_text, request.num_results, False, result)
        
        return QueryResponse(**result)

    # 4. Get chunk IDs and retrieve content
    chunk_ids = [result[0] for result in search_results]
    similarity_scores = [result[1] for result in search_results]
    
    # Retrieve chunk content
    chunks = get_chunks_by_ids(chunk_ids)
    
    # Add additional source content if available
    if request.use_additional_sources and data_integration_service:
        try:
            additional_content = data_integration_service.get_content_for_query(
                request.query_text, 
                max_sources=2
            )
            
            for item in additional_content:
                chunk_id = f"additional_{hashlib.md5(item['url'].encode()).hexdigest()[:8]}"
                if chunk_id in chunk_ids:
                    # Add the additional content as a chunk
                    chunks.append({
                        'id': chunk_id,
                        'content': item['content'],
                        'url': item['url'],
                        'title': item.get('title', ''),
                        'source_type': 'additional'
                    })
        except Exception as e:
            logger.warning(f"Failed to add additional content: {e}")
    
    if not chunks:
        logger.error(f"Failed to retrieve content for any chunk IDs: {chunk_ids}")
        # Fall back to simple answer with enhanced prompts
        if request.use_enhanced_prompts and prompt_service:
            prompt, prompt_metadata = construct_llm_prompt(request.query_text, [], request.use_enhanced_prompts)
        else:
            prompt = f"""You are an expert assistant knowledgeable about the Minnesota EIDBI program.
Answer the following question as best you can with general knowledge.

Question: {request.query_text}

Answer:"""
            prompt_metadata = {"query_type": "general", "response_format": "basic"}
        
        fallback_answer = generate_text_response(prompt)
        if not fallback_answer:
            fallback_answer = "I apologize, but I could not retrieve the relevant content to answer your question accurately."
            
        result = {
            "query": request.query_text,
            "answer": fallback_answer + "\n\n(Note: This response is based on general knowledge as there was an error retrieving specific content.)",
            "retrieved_chunk_ids": [],
            "cached": False,
            "version": APP_VERSION,
            "search_method": search_method,
            "query_type": prompt_metadata.get("query_type"),
            "response_format": prompt_metadata.get("response_format"),
            "sources_used": sources_used,
            "prompt_metadata": prompt_metadata
        }
        
        # Cache the result
        query_cache.set(request.query_text, request.num_results, False, result)
        
        return QueryResponse(**result)

    # 5. Rerank results if enabled
    if request.use_reranking and reranker:
        reranked_results = reranker.rerank_results(
            query=request.query_text,
            chunks=chunks,
            keywords=keywords,
            similarity_scores=similarity_scores
        )
        
        # Take top results after reranking
        final_chunks = [result[0] for result in reranked_results[:request.num_results]]
        final_chunk_ids = [chunk['id'] for chunk in final_chunks]
        logger.info(f"Reranked results. Top chunk IDs: {final_chunk_ids}")
    else:
        # Use original order
        final_chunks = chunks[:request.num_results]
        final_chunk_ids = [chunk['id'] for chunk in final_chunks]

    # 6. Construct Enhanced Prompt and Query LLM
    prompt, prompt_metadata = construct_llm_prompt(request.query_text, final_chunks, request.use_enhanced_prompts)
    logger.debug(f"Generated LLM Prompt with {len(final_chunks)} chunks using {prompt_metadata.get('template_used', 'basic')} template")

    llm_answer = generate_text_response(prompt)

    if llm_answer is None:
        logger.error("LLM failed to generate a response.")
        raise HTTPException(status_code=500, detail="AI failed to generate an answer.")

    # 7. Format and Return Response
    query_duration_ms = int((time.time() - query_start_time) * 1000)
    logger.info(f"Successfully generated LLM answer in {query_duration_ms}ms using {search_method} search with {len(sources_used)} sources")
    
    result = {
        "query": request.query_text,
        "answer": llm_answer.strip(),
        "retrieved_chunk_ids": final_chunk_ids,
        "cached": False,
        "version": APP_VERSION,
        "search_method": search_method,
        "query_type": prompt_metadata.get("query_type"),
        "response_format": prompt_metadata.get("response_format"),
        "sources_used": list(set(sources_used)),  # Remove duplicates
        "prompt_metadata": prompt_metadata
    }
    
    # Cache the result
    query_cache.set(request.query_text, request.num_results, False, result)
    
    return QueryResponse(**result)

# Keep existing endpoints for backward compatibility
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
        # Use enhanced prompts if available
        if prompt_service:
            prompt, prompt_metadata = construct_llm_prompt(query_text, [], True)
        else:
            prompt = f"""You are an expert assistant knowledgeable about the Minnesota EIDBI program.
Answer the following question as best you can with general knowledge.

Question: {query_text}

Answer:"""
            prompt_metadata = {"query_type": "general", "response_format": "basic"}
        
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
            "retrieved_chunk_ids": [],  # Empty for simple answers
            "query_type": prompt_metadata.get("query_type"),
            "response_format": prompt_metadata.get("response_format"),
            "prompt_metadata": prompt_metadata
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

# Add script entry point to run directly
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Starting enhanced server on {host}:{port}")
    uvicorn.run("main:app", host=host, port=port) 