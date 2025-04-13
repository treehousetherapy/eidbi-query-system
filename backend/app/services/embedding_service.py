# eidbi-query-system/backend/app/services/embedding_service.py

import logging
import time
from typing import List, Optional
from google.cloud import aiplatform
from google.cloud.aiplatform.gapic.schema import predict
from vertexai.language_models import TextEmbeddingModel, TextEmbedding # Corrected import for v1.38+
import os

# --- Import Vertex AI Initializer ---
try:
    import sys
    # Assuming this file is in eidbi-query-system/backend/app/services/
    # Go up three levels to reach eidbi-query-system/
    SERVICE_DIR = os.path.dirname(__file__)
    APP_DIR = os.path.dirname(SERVICE_DIR)
    BACKEND_DIR = os.path.dirname(APP_DIR)
    PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
    # Add scraper utils path (assuming utils are shared or scraper runs first)
    SCRAPER_UTILS_PATH = os.path.join(PROJECT_ROOT, 'scraper', 'utils')
    if SCRAPER_UTILS_PATH not in sys.path:
         sys.path.append(SCRAPER_UTILS_PATH)
    # We ONLY need these from vertex_ai_utils now
    from utils.vertex_ai_utils import initialize_vertex_ai_once, LOCATION, PROJECT_ID
except ImportError as e:
    print(f"Error importing vertex_ai_utils in embedding_service.py: {e}")
    print("Ensure scraper/utils/vertex_ai_utils.py exists and paths are correct.")
    # Define fallback values directly
    PROJECT_ID = None # Set to None if import fails
    LOCATION = None # Set to None if import fails
    def initialize_vertex_ai_once(): return False
# --- End Import ---

logger = logging.getLogger(__name__)

# Configuration
MODEL_NAME = "textembedding-gecko@003"
MAX_BATCH_SIZE = 5

# --- Vertex AI Initialization --- 
# PROJECT_ID and LOCATION are now imported or set to None above
_is_vertex_initialized = False # Module-level flag

def initialize_vertex_ai_once():
    """
    Initializes the Vertex AI client library if not already initialized.
    Should be called once at application startup.
    """
    global _is_vertex_initialized
    if _is_vertex_initialized:
        logger.debug("Vertex AI already initialized.")
        return True

    if not PROJECT_ID:
        logger.error("GCP_PROJECT_ID was not loaded correctly. Cannot initialize Vertex AI.")
        return False
    if not LOCATION:
        logger.error("GCP region was not loaded correctly. Cannot initialize Vertex AI.")
        return False

    try:
        logger.info(f"Attempting to initialize Vertex AI for Project: {PROJECT_ID}, Location: {LOCATION}")
        aiplatform.init(project=PROJECT_ID, location=LOCATION)
        _is_vertex_initialized = True # Set flag on successful init
        logger.info("Vertex AI initialized successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI: {e}", exc_info=True)
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        logger.error(f"Check credentials. GOOGLE_APPLICATION_CREDENTIALS set to: {creds_path}")
        _is_vertex_initialized = False
        return False

_model_instance = None # Cache the model instance

def _get_embedding_model(model_name: str):
    """Helper to get and cache the embedding model instance."""
    global _model_instance
    if _model_instance is None:
        try:
            logger.info(f"Loading embedding model for the first time: {model_name}")
            _model_instance = TextEmbeddingModel.from_pretrained(model_name)
        except Exception as e:
             logger.error(f"Failed to load embedding model {model_name}: {e}", exc_info=True)
             _model_instance = None # Ensure it stays None on failure
             raise # Re-raise the exception to signal failure
    return _model_instance

def generate_embeddings(texts: List[str], model_name: str = MODEL_NAME) -> Optional[List[Optional[List[float]]]]:
    """
    Generates text embeddings for a list of text strings using Vertex AI.
    Assumes initialize_vertex_ai_once() has been called successfully.
    """
    if not _is_vertex_initialized:
         logger.error("Vertex AI is not initialized. Call initialize_vertex_ai_once() first.")
         return None

    if not texts:
        logger.warning("No texts provided for embedding.")
        return []

    try:
        model = _get_embedding_model(model_name)
        if model is None:
             logger.error("Embedding model could not be loaded.")
             return None

        logger.info(f"Generating embeddings for {len(texts)} text(s) using {model_name}...")
        all_embeddings: List[Optional[List[float]]] = []
        processed_count = 0

        # Process texts in batches to respect API limits
        for i in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[i:i + MAX_BATCH_SIZE]
            try:
                logger.debug(f"Processing batch {i // MAX_BATCH_SIZE + 1} ({len(batch)} items)")
                embeddings_response: List[TextEmbedding] = model.get_embeddings(batch)
                batch_embeddings = [embedding.values for embedding in embeddings_response]
                all_embeddings.extend(batch_embeddings)
                processed_count += len(batch)
                logger.debug(f"Successfully embedded batch {i // MAX_BATCH_SIZE + 1}.")

                # Optional: Add delay between batches if hitting rate limits
                # time.sleep(0.1)

            except Exception as batch_error:
                 logger.error(f"Error embedding batch starting at index {i}: {batch_error}", exc_info=True)
                 all_embeddings.extend([None] * len(batch))

        logger.info(f"Finished generating embeddings for this request.")
        # Ensure length matches input
        if len(all_embeddings) != len(texts):
             logger.error(f"Critical error: Mismatch in embedding results length ({len(all_embeddings)}) vs input length ({len(texts)}).")
             # Attempt to recover, though this indicates a flaw in batch error handling
             all_embeddings.extend([None] * (len(texts) - len(all_embeddings)))

        return all_embeddings

    except Exception as e:
        logger.error(f"Failed to get embeddings from Vertex AI model {model_name}: {e}", exc_info=True)
        return None

# --- Example Usage (modified) ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')

    print(f"Using Project: {PROJECT_ID}, Location: {LOCATION}")

    # Initialize *once* when testing directly
    if initialize_vertex_ai_once():
        sample_texts = [
            "What is the meaning of life?",
            "How does a transformer model work?",
            "This is a sample sentence for testing purposes.",
            "Embeddings are numerical representations of text.",
            "Vertex AI provides various machine learning services.",
            "This is the sixth sentence.",
            "One more for good measure."
        ]

        print(f"\nGenerating embeddings for {len(sample_texts)} texts using model '{MODEL_NAME}'...")
        generated_embeddings = generate_embeddings(sample_texts)

        if generated_embeddings:
            print(f"\nSuccessfully generated {len(generated_embeddings)} results.")
            for i, (text, embedding) in enumerate(zip(sample_texts, generated_embeddings)):
                if embedding:
                    print(f"Text {i+1}: \"{text[:50]}...\" -> Embedding dim: {len(embedding)}, First 3 values: {embedding[:3]}")
                else:
                    print(f"Text {i+1}: \"{text[:50]}...\" -> Embedding failed")
        else:
            print("\nEmbedding generation failed. Check logs.")
    else:
        print("\nVertex AI initialization failed. Cannot run embedding example.") 