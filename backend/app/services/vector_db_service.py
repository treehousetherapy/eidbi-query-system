# eidbi-query-system/backend/app/services/vector_db_service.py

import logging
import os
import json
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import re

# Configure logging
logger = logging.getLogger(__name__)

# Path to the scraped data file
# When running in Docker, the file will be in /app directory
# When running locally, try multiple paths
def get_scraped_data_path():
    """Get the path to the scraped data file, checking multiple locations."""
    possible_paths = [
        # Docker container path - new file with better content
        '/app/local_scraped_data_with_embeddings.jsonl',
        # Local development - in backend directory
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'local_scraped_data_with_embeddings.jsonl'),
        # Fallback to the specific file if the generic one doesn't exist
        '/app/local_scraped_data_with_embeddings_20250511_152056.jsonl',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'local_scraped_data_with_embeddings_20250511_152056.jsonl'),
        # Local development - project root
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'scraper', 'local_scraped_data_with_embeddings_20250511_152056.jsonl')
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"Found scraped data at: {path}")
            return path
    
    logger.error(f"Could not find scraped data file. Tried paths: {possible_paths}")
    return possible_paths[0]  # Default to Docker path

SCRAPED_DATA_PATH = get_scraped_data_path()

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate the cosine similarity between two vectors."""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return np.dot(a, b) / (a_norm * b_norm)

def _load_data() -> List[Dict[str, Any]]:
    """Load the scraped data from the JSONL file."""
    data = []
    try:
        logger.info(f"Loading data from {SCRAPED_DATA_PATH}")
        with open(SCRAPED_DATA_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    chunk = json.loads(line)
                    data.append(chunk)
                except json.JSONDecodeError:
                    logger.warning(f"Error decoding JSON line: {line[:50]}...")
        logger.info(f"Loaded {len(data)} chunks from {SCRAPED_DATA_PATH}")
        return data
    except Exception as e:
        logger.error(f"Error loading data from {SCRAPED_DATA_PATH}: {e}", exc_info=True)
        return []

# Cache the loaded data
_cached_data = None

def find_neighbors(query_embedding: List[float], num_neighbors_override: Optional[int] = None) -> List[Tuple[str, float]]:
    """
    Find nearest neighbors to the query embedding in the local data.
    
    Args:
        query_embedding: The embedding vector to search for
        num_neighbors_override: Optional override for the number of neighbors to return
        
    Returns:
        List of (chunk_id, distance) tuples sorted by similarity (highest first)
    """
    global _cached_data
    
    # Load data if not already cached
    if _cached_data is None:
        _cached_data = _load_data()
    
    if not _cached_data:
        logger.warning("No data loaded for vector search.")
        return []
    
    # Number of neighbors to return
    num_neighbors = num_neighbors_override or 5
    
    # Calculate similarity with each chunk
    results = []
    for chunk in _cached_data:
        if 'embedding' not in chunk or not chunk['embedding'] or 'id' not in chunk:
            continue
            
        similarity = cosine_similarity(query_embedding, chunk['embedding'])
        
        results.append((chunk['id'], similarity))
    
    # Sort by similarity (highest first) and take top_k
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:num_neighbors]

def keyword_search(keywords: List[str], num_results: int = 10) -> List[Tuple[str, int]]:
    """
    Search for chunks containing specific keywords
    
    Args:
        keywords: List of keywords to search for
        num_results: Maximum number of results to return
        
    Returns:
        List of (chunk_id, match_count) tuples sorted by match count
    """
    global _cached_data
    
    # Load data if not already cached
    if _cached_data is None:
        _cached_data = _load_data()
    
    if not _cached_data:
        logger.warning("No data loaded for keyword search.")
        return []
    
    logger.info(f"Performing keyword search for: {keywords}")
    
    keyword_results = []
    
    for chunk in _cached_data:
        if 'id' not in chunk or 'content' not in chunk:
            continue
        
        content_lower = chunk['content'].lower()
        title_lower = chunk.get('title', '').lower()
        
        # Count keyword matches
        match_count = 0
        matched_keywords = set()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # Count occurrences in content
            content_matches = len(re.findall(rf'\b{re.escape(keyword_lower)}\b', content_lower))
            
            # Bonus for title matches
            title_matches = len(re.findall(rf'\b{re.escape(keyword_lower)}\b', title_lower))
            title_matches *= 3  # Title matches are worth more
            
            if content_matches > 0 or title_matches > 0:
                matched_keywords.add(keyword)
                match_count += content_matches + title_matches
        
        # Only include chunks that match at least one keyword
        if match_count > 0:
            keyword_results.append((chunk['id'], match_count, len(matched_keywords)))
    
    # Sort by match count (descending), then by number of different keywords matched
    keyword_results.sort(key=lambda x: (x[1], x[2]), reverse=True)
    
    # Return only chunk_id and match_count
    results = [(chunk_id, match_count) for chunk_id, match_count, _ in keyword_results[:num_results]]
    
    logger.info(f"Keyword search found {len(results)} matching chunks")
    return results

def hybrid_search(
    query_embedding: List[float], 
    keywords: List[str],
    num_results: int = 10,
    vector_weight: float = 0.7
) -> List[Tuple[str, float]]:
    """
    Perform hybrid search combining vector similarity and keyword matching
    
    Args:
        query_embedding: The embedding vector for semantic search
        keywords: Keywords for keyword matching
        num_results: Number of results to return
        vector_weight: Weight for vector search (0-1), keyword gets 1-vector_weight
        
    Returns:
        List of (chunk_id, combined_score) tuples
    """
    logger.info(f"Performing hybrid search with vector_weight={vector_weight}")
    
    # Get vector search results
    vector_results = find_neighbors(query_embedding, num_results * 2)  # Get more for better coverage
    
    # Get keyword search results
    keyword_results = keyword_search(keywords, num_results * 2)
    
    # Combine scores
    combined_scores = {}
    
    # Add vector scores (normalized)
    if vector_results:
        max_vector_score = max(score for _, score in vector_results)
        for chunk_id, score in vector_results:
            normalized_score = score / max_vector_score if max_vector_score > 0 else 0
            combined_scores[chunk_id] = vector_weight * normalized_score
    
    # Add keyword scores (normalized)
    if keyword_results:
        max_keyword_score = max(count for _, count in keyword_results)
        for chunk_id, count in keyword_results:
            normalized_score = count / max_keyword_score if max_keyword_score > 0 else 0
            keyword_contribution = (1 - vector_weight) * normalized_score
            
            if chunk_id in combined_scores:
                combined_scores[chunk_id] += keyword_contribution
            else:
                combined_scores[chunk_id] = keyword_contribution
    
    # Sort by combined score
    results = [(chunk_id, score) for chunk_id, score in combined_scores.items()]
    results.sort(key=lambda x: x[1], reverse=True)
    
    return results[:num_results]

def get_chunk_by_id(chunk_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific chunk by its ID from the local JSONL file.
    
    Args:
        chunk_id: The ID of the chunk to retrieve
        
    Returns:
        The chunk data as a dictionary, or None if not found
    """
    global _cached_data
    
    # Load data if not already cached
    if _cached_data is None:
        _cached_data = _load_data()
    
    if not _cached_data:
        logger.warning("No data loaded for chunk retrieval.")
        return None
    
    # Search for the chunk with the matching ID
    for chunk in _cached_data:
        if chunk.get('id') == chunk_id:
            return chunk
            
    logger.warning(f"Chunk with ID {chunk_id} not found in local data.")
    return None

def get_chunks_by_ids(chunk_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Retrieve multiple chunks by their IDs
    
    Args:
        chunk_ids: List of chunk IDs to retrieve
        
    Returns:
        List of chunk dictionaries
    """
    chunks = []
    for chunk_id in chunk_ids:
        chunk = get_chunk_by_id(chunk_id)
        if chunk:
            chunks.append(chunk)
    return chunks

# --- Example Usage --- (Requires a Deployed Index Endpoint)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')

    # Use the safely loaded values
    current_index_id = _get_vector_db_setting('index_id')
    current_endpoint_id = _get_vector_db_setting('index_endpoint_id')
    current_num_neighbors = _get_vector_db_setting('num_neighbors', 10)

    print(f"Vector DB Service using:")
    print(f"  Project: {PROJECT_ID}")
    print(f"  Location: {LOCATION}")
    print(f"  Index Endpoint ID: {current_endpoint_id}")
    print(f"  Index ID (for upsert): {current_index_id}")
    print(f"  Num Neighbors: {current_num_neighbors}")

    # --- IMPORTANT --- 
    # The following calls require:
    # 1. Vertex AI Initialized (via initialize_vertex_ai called elsewhere or here)
    # 2. A deployed Matching Engine Index Endpoint ID configured in .env
    # 3. An Index ID configured in .env (for upsert placeholder)
    # 4. Correct embedding dimensions for your index
    # -----------------

    if not initialize_vertex_ai():
         print("\nERROR: Vertex AI Initialization failed. Cannot run examples.")

    elif not current_endpoint_id:
         print("\nERROR: VECTOR_DB_INDEX_ENDPOINT_ID not set in .env. Cannot run query example.")

    else:
         print("\n--- Testing Find Neighbors --- ")
         # Replace with a real embedding vector of the correct dimension (e.g., 768)
         # This is just a dummy vector for structure
         dummy_query_vector = [0.1] * 768 # Adjust dimension if needed!

         neighbors_result = find_neighbors(dummy_query_vector, current_num_neighbors)

         if neighbors_result:
             print("Found Neighbors:")
             for neighbor_id, distance in neighbors_result:
                 print(f"  ID: {neighbor_id}, Distance: {distance:.4f}")
         else:
             print("Could not find neighbors (or query failed). Check logs and index status.")

         print("\n--- Testing Upsert (Placeholder) ---")
         if not current_index_id:
              print("\nERROR: VECTOR_DB_INDEX_ID not set in .env. Cannot run upsert example.")
         else:
              dummy_datapoints = [
                  ("doc1_chunk1", [0.2] * 768),
                  ("doc1_chunk2", [0.3] * 768)
              ]
              upsert_embeddings(dummy_datapoints, current_index_id)
              print("(Check logs for upsert placeholder message)") 