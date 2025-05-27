# eidbi-query-system/backend/app/services/vector_db_service.py

import logging
import os
import json
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import re
from .structured_data_service import StructuredDataService

# Configure logging
logger = logging.getLogger(__name__)

# Enhanced configuration for better coverage
DEFAULT_NUM_NEIGHBORS = 15  # Increased from 5 for better coverage
DEFAULT_KEYWORD_RESULTS = 20  # Increased for better coverage
DEFAULT_HYBRID_RESULTS = 12  # Increased for better coverage

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
_structured_data_service = None

def get_structured_data_service() -> StructuredDataService:
    """Get or initialize the structured data service"""
    global _structured_data_service
    if _structured_data_service is None:
        _structured_data_service = StructuredDataService()
    return _structured_data_service

def _load_data_with_structured() -> List[Dict[str, Any]]:
    """Load both regular and structured data"""
    data = _load_data()  # Load regular data
    
    # Add structured data
    try:
        structured_service = get_structured_data_service()
        structured_entries = structured_service.to_vector_db_format()
        
        logger.info(f"Adding {len(structured_entries)} structured data entries")
        data.extend(structured_entries)
        
    except Exception as e:
        logger.warning(f"Could not load structured data: {e}")
    
    return data

def find_neighbors(query_embedding: List[float], num_neighbors_override: Optional[int] = None) -> List[Tuple[str, float]]:
    """
    Find nearest neighbors to the query embedding in the local data (including structured data).
    
    Args:
        query_embedding: The embedding vector to search for
        num_neighbors_override: Optional override for the number of neighbors to return
        
    Returns:
        List of (chunk_id, distance) tuples sorted by similarity (highest first)
    """
    global _cached_data
    
    # Load data if not already cached (including structured data)
    if _cached_data is None:
        _cached_data = _load_data_with_structured()
    
    if not _cached_data:
        logger.warning("No data loaded for vector search.")
        return []
    
    # Number of neighbors to return (increased default for better coverage)
    num_neighbors = num_neighbors_override or DEFAULT_NUM_NEIGHBORS
    
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

def keyword_search(keywords: List[str], num_results: int = None) -> List[Tuple[str, int]]:
    """
    Search for chunks containing specific keywords (including structured data)
    
    Args:
        keywords: List of keywords to search for
        num_results: Maximum number of results to return
        
    Returns:
        List of (chunk_id, match_count) tuples sorted by match count
    """
    global _cached_data
    
    # Load data if not already cached (including structured data)
    if _cached_data is None:
        _cached_data = _load_data_with_structured()
    
    if not _cached_data:
        logger.warning("No data loaded for keyword search.")
        return []
    
    # Use enhanced default for better coverage
    if num_results is None:
        num_results = DEFAULT_KEYWORD_RESULTS
    
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
    num_results: int = None,
    vector_weight: float = 0.7
) -> List[Tuple[str, float]]:
    """
    Perform enhanced hybrid search combining vector similarity and keyword matching
    
    Args:
        query_embedding: The embedding vector for semantic search
        keywords: Keywords for keyword matching
        num_results: Number of results to return
        vector_weight: Weight for vector search (0-1), keyword gets 1-vector_weight
        
    Returns:
        List of (chunk_id, combined_score) tuples
    """
    # Use enhanced default for better coverage
    if num_results is None:
        num_results = DEFAULT_HYBRID_RESULTS
        
    logger.info(f"Performing hybrid search with vector_weight={vector_weight}")
    
    # Get vector search results with expanded coverage
    vector_results = find_neighbors(query_embedding, num_results * 3)  # Get more for better coverage
    
    # Get keyword search results with expanded coverage
    keyword_results = keyword_search(keywords, num_results * 3)
    
    # Check for structured data matches first (prioritize exact facts)
    structured_matches = search_structured_data(keywords)
    
    # Combine scores
    combined_scores = {}
    
    # Prioritize structured data matches (give them highest scores)
    structured_boost = 1.5  # Boost factor for structured data
    for chunk_id, relevance_score in structured_matches:
        combined_scores[chunk_id] = relevance_score * structured_boost
    
    # Add vector scores (normalized)
    if vector_results:
        max_vector_score = max(score for _, score in vector_results)
        for chunk_id, score in vector_results:
            normalized_score = score / max_vector_score if max_vector_score > 0 else 0
            vector_contribution = vector_weight * normalized_score
            
            if chunk_id in combined_scores:
                combined_scores[chunk_id] += vector_contribution
            else:
                combined_scores[chunk_id] = vector_contribution
    
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

def search_structured_data(keywords: List[str]) -> List[Tuple[str, float]]:
    """
    Search specifically in structured data for keyword matches
    
    Args:
        keywords: List of keywords to search for
        
    Returns:
        List of (chunk_id, relevance_score) tuples
    """
    try:
        structured_service = get_structured_data_service()
        matches = []
        
        for keyword in keywords:
            # Search for entries matching keywords
            matching_entries = structured_service.search_entries(keyword)
            
            for entry in matching_entries:
                relevance_score = 1.0
                
                # Higher relevance for provider-related queries
                if any(provider_keyword in keyword.lower() for provider_keyword in 
                      ['provider', 'count', 'number', 'total', 'how many']):
                    if 'provider' in entry.key.lower():
                        relevance_score = 2.0
                
                # Higher relevance for exact key matches
                if keyword.lower() in entry.key.lower():
                    relevance_score *= 1.5
                
                chunk_id = f"structured_{entry.id}"
                matches.append((chunk_id, relevance_score))
        
        # Remove duplicates and sort by relevance
        unique_matches = {}
        for chunk_id, score in matches:
            if chunk_id not in unique_matches or unique_matches[chunk_id] < score:
                unique_matches[chunk_id] = score
        
        sorted_matches = [(chunk_id, score) for chunk_id, score in unique_matches.items()]
        sorted_matches.sort(key=lambda x: x[1], reverse=True)
        
        return sorted_matches
        
    except Exception as e:
        logger.warning(f"Error searching structured data: {e}")
        return []

def get_provider_statistics() -> Dict[str, Any]:
    """
    Get current provider statistics from structured data
    
    Returns:
        Dictionary containing provider statistics
    """
    try:
        structured_service = get_structured_data_service()
        return structured_service.get_provider_stats()
    except Exception as e:
        logger.error(f"Error getting provider statistics: {e}")
        return {}

def update_provider_data(total_count: int, by_county: Optional[Dict[str, int]] = None,
                        source: str = "Minnesota DHS Provider Directory",
                        source_url: Optional[str] = None) -> bool:
    """
    Update provider count data in structured storage
    
    Args:
        total_count: Total number of EIDBI providers
        by_county: Optional breakdown by county
        source: Data source name
        source_url: URL of the data source
        
    Returns:
        True if successful, False otherwise
    """
    try:
        structured_service = get_structured_data_service()
        structured_service.update_provider_count(total_count, by_county, source, source_url)
        
        # Clear cache to force reload with new data
        global _cached_data
        _cached_data = None
        
        logger.info(f"Updated provider data: {total_count} total providers")
        return True
        
    except Exception as e:
        logger.error(f"Error updating provider data: {e}")
        return False

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