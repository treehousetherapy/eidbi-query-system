# eidbi-query-system/backend/app/services/embedding_service.py

import logging
import time
import os
from typing import List, Optional
import hashlib
import numpy as np

# Try to import Vertex AI, but don't fail if not available
try:
    import vertexai
    from vertexai.language_models import TextEmbeddingModel
    from google.api_core import retry
    from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, DeadlineExceeded
    import google.auth
    from google.auth import exceptions as auth_exceptions
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Vertex AI libraries not available. Will use mock embeddings.")

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
MODEL_NAME = "textembedding-gecko@003"  # Latest model for text embeddings
MAX_BATCH_SIZE = 5  # Vertex AI batch size limit
EMBEDDING_DIMENSION = 768  # Default dimension for gecko model

# Get project configuration from environment
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "lyrical-ward-454915-e6")
LOCATION = os.getenv("GCP_REGION", "us-central1")

# Allow fallback to mock embeddings
USE_MOCK_EMBEDDINGS = os.getenv("USE_MOCK_EMBEDDINGS", "false").lower() == "true"

# Global model instance
_embedding_model = None
_use_mock = False  # Track whether we're using mock embeddings

def generate_mock_embedding(text: str) -> List[float]:
    """Generate a deterministic mock embedding for testing."""
    # Use SHA-256 hash of the text
    hash_obj = hashlib.sha256(text.encode('utf-8'))
    hash_bytes = hash_obj.digest()
    
    # Convert bytes to floats in range [-1, 1]
    embedding = []
    for i in range(0, len(hash_bytes), 4):
        # Get 4 bytes and convert to float
        if i + 4 <= len(hash_bytes):
            value = int.from_bytes(hash_bytes[i:i+4], byteorder='big')
            # Normalize to [-1, 1]
            normalized = (value / (2**32 - 1)) * 2 - 1
            embedding.append(normalized)
    
    # Pad or truncate to 768 dimensions
    while len(embedding) < EMBEDDING_DIMENSION:
        embedding.extend(embedding[:min(EMBEDDING_DIMENSION - len(embedding), len(embedding))])
    
    return embedding[:EMBEDDING_DIMENSION]

def check_authentication():
    """Check if we have valid GCP authentication."""
    if not VERTEX_AI_AVAILABLE:
        return False
        
    try:
        credentials, project = google.auth.default()
        logger.info(f"Authentication successful. Project from credentials: {project}")
        return True
    except auth_exceptions.DefaultCredentialsError as e:
        logger.error(f"No valid GCP credentials found: {e}")
        logger.error("Please ensure one of the following:")
        logger.error("1. GOOGLE_APPLICATION_CREDENTIALS environment variable is set")
        logger.error("2. Running on GCP with proper service account")
        logger.error("3. gcloud auth application-default login has been run")
        return False
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        return False

def initialize_vertex_ai() -> bool:
    """
    Initialize Vertex AI and load the embedding model.
    Falls back to mock embeddings if configured or if Vertex AI fails.
    
    Returns:
        bool: True if initialization is successful, False otherwise.
    """
    global _embedding_model, _use_mock
    
    # If explicitly configured to use mock embeddings
    if USE_MOCK_EMBEDDINGS:
        logger.info("Configured to use mock embeddings (USE_MOCK_EMBEDDINGS=true)")
        _use_mock = True
        return True
    
    # If Vertex AI is not available
    if not VERTEX_AI_AVAILABLE:
        logger.warning("Vertex AI not available. Using mock embeddings.")
        _use_mock = True
        return True
    
    try:
        # Check authentication first
        if not check_authentication():
            logger.error("Cannot initialize Vertex AI without valid authentication")
            logger.info("Falling back to mock embeddings")
            _use_mock = True
            return True
        
        logger.info(f"Initializing Vertex AI with project={PROJECT_ID}, location={LOCATION}")
        
        # Initialize Vertex AI
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        
        # Load the embedding model
        _embedding_model = TextEmbeddingModel.from_pretrained(MODEL_NAME)
        
        logger.info(f"Successfully loaded embedding model: {MODEL_NAME}")
        
        # Test the model with a simple embedding
        try:
            test_embedding = _embedding_model.get_embeddings(["test"])
            logger.info(f"Model test successful. Embedding dimension: {len(test_embedding[0].values)}")
            _use_mock = False
            return True
        except Exception as e:
            logger.error(f"Model test failed: {e}")
            logger.info("Falling back to mock embeddings")
            _embedding_model = None
            _use_mock = True
            return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI: {e}", exc_info=True)
        logger.info("Falling back to mock embeddings")
        _embedding_model = None
        _use_mock = True
        return True

if VERTEX_AI_AVAILABLE:
    @retry.Retry(
        predicate=retry.if_exception_type(
            ResourceExhausted,
            ServiceUnavailable,
            DeadlineExceeded,
        ),
        initial=1.0,
        maximum=60.0,
        multiplier=2.0,
        deadline=300.0,
    )
    def _call_embedding_api(texts: List[str]) -> List[List[float]]:
        """
        Call the Vertex AI embedding API with retry logic.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not _embedding_model:
            raise RuntimeError("Embedding model not initialized")
        
        embeddings = _embedding_model.get_embeddings(texts)
        return [embedding.values for embedding in embeddings]

def generate_embeddings(texts: List[str]) -> Optional[List[Optional[List[float]]]]:
    """
    Generate embeddings for the given texts using Vertex AI's text embedding model.
    Falls back to mock embeddings if Vertex AI is not available or fails.
    
    Args:
        texts: List of text strings to generate embeddings for.
        
    Returns:
        List of embeddings, where each embedding is a list of floats.
        Returns None if the embedding generation fails completely.
        Individual embeddings may be None if that specific text fails.
    """
    if not texts:
        logger.warning("Empty text list provided for embedding generation")
        return []
    
    # Use mock embeddings if configured or fallback
    if _use_mock:
        logger.info(f"Generating mock embeddings for {len(texts)} texts")
        embeddings = []
        for text in texts:
            if text and isinstance(text, str) and text.strip():
                embeddings.append(generate_mock_embedding(text))
            else:
                embeddings.append(None)
        return embeddings
    
    # Try to use real Vertex AI embeddings
    if not _embedding_model:
        # Try to initialize on demand
        if not initialize_vertex_ai():
            logger.error("Failed to initialize Vertex AI")
            return None
    
    try:
        logger.info(f"Generating embeddings for {len(texts)} texts using {MODEL_NAME}")
        
        # Process in batches to respect API limits
        all_embeddings = []
        
        for i in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[i:i + MAX_BATCH_SIZE]
            
            try:
                # Clean and validate batch texts
                cleaned_batch = []
                batch_indices = []
                
                for j, text in enumerate(batch):
                    if text and isinstance(text, str) and text.strip():
                        # Truncate very long texts (API limit is ~10k tokens)
                        truncated = text[:8000] if len(text) > 8000 else text
                        cleaned_batch.append(truncated)
                        batch_indices.append(i + j)
                    else:
                        logger.warning(f"Invalid text at index {i + j}, skipping")
                        all_embeddings.append(None)
                
                if cleaned_batch:
                    # Call the API with retry logic
                    batch_embeddings = _call_embedding_api(cleaned_batch)
                    
                    # Map embeddings back to original positions
                    embedding_map = {idx: emb for idx, emb in zip(batch_indices, batch_embeddings)}
                    
                    for j in range(len(batch)):
                        if (i + j) in embedding_map:
                            all_embeddings.append(embedding_map[i + j])
                        elif (i + j) < len(all_embeddings):
                            # Already added None for invalid text
                            pass
                        else:
                            all_embeddings.append(None)
                    
                    logger.debug(f"Processed batch {i//MAX_BATCH_SIZE + 1}/{(len(texts)-1)//MAX_BATCH_SIZE + 1}")
                    
                    # Small delay between batches to avoid rate limiting
                    if i + MAX_BATCH_SIZE < len(texts):
                        time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing batch starting at index {i}: {e}")
                # Add None for all texts in the failed batch
                for j in range(len(batch)):
                    if len(all_embeddings) <= i + j:
                        all_embeddings.append(None)
        
        successful_count = sum(1 for emb in all_embeddings if emb is not None)
        logger.info(f"Successfully generated {successful_count}/{len(texts)} embeddings")
        
        return all_embeddings
    
    except Exception as e:
        logger.error(f"Critical error generating embeddings: {e}", exc_info=True)
        # Fall back to mock embeddings
        logger.info("Falling back to mock embeddings due to error")
        embeddings = []
        for text in texts:
            if text and isinstance(text, str) and text.strip():
                embeddings.append(generate_mock_embedding(text))
            else:
                embeddings.append(None)
        return embeddings

# --- Example Usage ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')

    print(f"Using Project: {PROJECT_ID}, Location: {LOCATION}")
    print(f"Vertex AI Available: {VERTEX_AI_AVAILABLE}")
    print(f"Use Mock Embeddings: {USE_MOCK_EMBEDDINGS}")

    # Initialize once
    if initialize_vertex_ai():
        sample_texts = [
            "What is EIDBI?",
            "Early Intensive Developmental and Behavioral Intervention",
            "EIDBI is a Minnesota Health Care Program benefit",
            "Who is eligible for EIDBI services?",
            "EIDBI provider requirements"
        ]

        print(f"\nGenerating embeddings for {len(sample_texts)} texts...")
        generated_embeddings = generate_embeddings(sample_texts)

        if generated_embeddings:
            print(f"\nSuccessfully generated {len(generated_embeddings)} results.")
            print(f"Using {'mock' if _use_mock else 'real Vertex AI'} embeddings")
            for i, (text, embedding) in enumerate(zip(sample_texts, generated_embeddings)):
                if embedding:
                    print(f"Text {i+1}: \"{text[:50]}...\" -> Embedding dim: {len(embedding)}, First 3 values: {embedding[:3]}")
                else:
                    print(f"Text {i+1}: \"{text[:50]}...\" -> Embedding failed")
        else:
            print("\nEmbedding generation failed. Check logs.")
    else:
        print("\nInitialization failed. Cannot run embedding example.") 