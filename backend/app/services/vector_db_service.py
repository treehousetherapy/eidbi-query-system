# eidbi-query-system/backend/app/services/vector_db_service.py

import logging
from typing import List, Tuple, Optional, Any

from google.cloud import aiplatform
from google.cloud.aiplatform.matching_engine import MatchingEngineIndexEndpoint

# --- Import Settings and Initializer ---
try:
    import sys
    import os
    SERVICE_DIR = os.path.dirname(__file__)
    APP_DIR = os.path.dirname(SERVICE_DIR)
    BACKEND_DIR = os.path.dirname(APP_DIR)
    PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
    # Add scraper utils path for vertex_ai_utils
    SCRAPER_UTILS_PATH = os.path.join(PROJECT_ROOT, 'scraper', 'utils')
    if SCRAPER_UTILS_PATH not in sys.path:
        sys.path.append(SCRAPER_UTILS_PATH)
    # Add config path
    if PROJECT_ROOT not in sys.path:
         sys.path.append(PROJECT_ROOT)
    from config.settings import settings
    from utils.vertex_ai_utils import initialize_vertex_ai_once, LOCATION, PROJECT_ID
except ImportError as e:
    print(f"Error importing modules in vector_db_service.py: {e}")
    # Define fallback values
    settings = None
    LOCATION = None
    PROJECT_ID = None
    def initialize_vertex_ai_once(): return False
# --- End Import ---

logger = logging.getLogger(__name__)

# Use a function to safely get settings to avoid NameError if import failed
def _get_vector_db_setting(key: str, default: Any = None) -> Any:
    if settings and hasattr(settings, 'vector_db') and hasattr(settings.vector_db, key):
        return getattr(settings.vector_db, key)
    logger.warning(f"Vector DB setting '{key}' not found, using default: {default}")
    return default

INDEX_ID = _get_vector_db_setting('index_id')
INDEX_ENDPOINT_ID = _get_vector_db_setting('index_endpoint_id')
NUM_NEIGHBORS = _get_vector_db_setting('num_neighbors', 10)

# Global variable to hold the index endpoint instance
_index_endpoint_instance: Optional[MatchingEngineIndexEndpoint] = None

def _get_index_endpoint() -> Optional[MatchingEngineIndexEndpoint]:
    """Gets or initializes the Matching Engine Index Endpoint instance."""
    global _index_endpoint_instance
    if _index_endpoint_instance:
        return _index_endpoint_instance

    if not initialize_vertex_ai_once():
        logger.error("Vertex AI not initialized. Cannot get Index Endpoint.")
        return None

    if not INDEX_ENDPOINT_ID:
        logger.error("VECTOR_DB_INDEX_ENDPOINT_ID is not configured. Cannot get Index Endpoint.")
        return None

    try:
        logger.info(f"Initializing Matching Engine Index Endpoint: {INDEX_ENDPOINT_ID}")
        _index_endpoint_instance = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=INDEX_ENDPOINT_ID)
        logger.info("Matching Engine Index Endpoint initialized.")
        return _index_endpoint_instance
    except Exception as e:
        logger.error(f"Failed to initialize Matching Engine Index Endpoint: {e}", exc_info=True)
        return None

def upsert_embeddings(
    datapoints: List[Tuple[str, List[float]]],
    index_id_override: Optional[str] = None
) -> bool:
    """
    Upserts (inserts or updates) datapoints into the Matching Engine Index.

    Args:
        datapoints: A list of tuples, where each tuple is (id_string, embedding_vector).
        index_id_override: Optionally override the index ID from settings.

    Returns:
        True if the upsert operation was successful, False otherwise.
    """
    index_endpoint = _get_index_endpoint()
    if not index_endpoint:
        return False

    target_index_id = index_id_override or INDEX_ID
    if not target_index_id:
        logger.error("Vector DB Index ID is not configured. Cannot upsert.")
        return False

    # The Matching Engine client library currently expects datapoints
    # in a specific format for the upsert_datapoints method (or use gRPC).
    # As of late 2023/early 2024, direct upsert via the high-level Python SDK
    # might still be evolving or require specific index types/configurations.
    # Often, upserting is done via batch jobs or dataflow for larger datasets.

    # Placeholder: Direct upsert is complex with the current high-level SDK.
    # For a small number of updates, alternative methods or direct gRPC calls might be needed.
    # This function currently serves as a placeholder and will log a warning.
    logger.warning("Direct upsert via high-level Python SDK is complex/limited.")
    logger.warning("Consider batch index updates or gRPC for production upserts.")
    logger.info(f"Would attempt to upsert {len(datapoints)} datapoints to Index ID: {target_index_id}")

    # Example structure if using a method that accepts it (check SDK docs for your index type):
    # try:
    #     # Construct aiplatform.IndexDatapoint objects if needed
    #     index_datapoints = [
    #         aiplatform.IndexDatapoint(datapoint_id=dp_id, feature_vector=vector)
    #         for dp_id, vector in datapoints
    #     ]
    #     index = aiplatform.MatchingEngineIndex(index_name=target_index_id)
    #     index.upsert_datapoints(datapoints=index_datapoints)
    #     logger.info(f"Successfully submitted upsert request for {len(datapoints)} datapoints.")
    #     return True
    # except Exception as e:
    #     logger.error(f"Failed to upsert datapoints to index {target_index_id}: {e}", exc_info=True)
    #     return False

    return False # Return False as direct upsert isn't fully implemented here


def find_neighbors(
    query_embedding: List[float],
    num_neighbors_override: Optional[int] = None
) -> List[Tuple[str, float]]:
    """
    Finds the nearest neighbors for a given query embedding.

    Args:
        query_embedding: The embedding vector to search for.
        num_neighbors_override: Optionally override the number of neighbors from settings.

    Returns:
        A list of tuples, where each tuple is (neighbor_id, distance_score).
        Returns an empty list if the query fails.
    """
    index_endpoint = _get_index_endpoint()
    if not index_endpoint:
        return []

    target_num_neighbors = num_neighbors_override or NUM_NEIGHBORS

    try:
        logger.info(f"Querying index endpoint {INDEX_ENDPOINT_ID} for {target_num_neighbors} neighbors.")
        # Note: The query format might need adjustment based on index configuration (e.g., filtering)
        response = index_endpoint.find_neighbors(
            queries=[query_embedding], # Find neighbors for a single query vector
            num_neighbors=target_num_neighbors
            # deployed_index_id="..." # Required if endpoint has multiple indexes deployed
        )

        # Response format is typically a list of lists (one per query)
        # Each inner list contains Neighbor objects
        if response and response[0]:
            neighbors = [(neighbor.id, neighbor.distance) for neighbor in response[0]]
            logger.info(f"Found {len(neighbors)} neighbors.")
            return neighbors
        else:
            logger.warning("No neighbors found or empty response from Matching Engine.")
            return []

    except Exception as e:
        logger.error(f"Failed to find neighbors: {e}", exc_info=True)
        return []

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
    # 1. Vertex AI Initialized (via initialize_vertex_ai_once called elsewhere or here)
    # 2. A deployed Matching Engine Index Endpoint ID configured in .env
    # 3. An Index ID configured in .env (for upsert placeholder)
    # 4. Correct embedding dimensions for your index
    # -----------------

    if not initialize_vertex_ai_once():
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