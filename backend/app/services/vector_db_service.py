# eidbi-query-system/backend/app/services/vector_db_service.py

import logging
import os
import json
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Path to the scraped data file (using absolute path)
# Make path absolute and independent of current working directory
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
SCRAPED_DATA_PATH = os.path.join(PROJECT_ROOT, 'scraper', 'local_scraped_data_with_embeddings_20250511_154715.jsonl')

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