import logging
import numpy as np
from typing import List, Optional
import os

logger = logging.getLogger(__name__)

def generate_embeddings(texts: List[str]) -> Optional[List[Optional[List[float]]]]:
    """
    Generate embeddings for the given texts.
    
    Uses real Vertex AI embeddings if available and configured,
    otherwise falls back to mock embeddings for testing.
    
    Args:
        texts: List of text strings to generate embeddings for.
        
    Returns:
        List of embeddings, where each embedding is a list of floats.
        Returns None if the embedding generation fails.
    """
    try:
        # Check if we should use mock embeddings
        use_mock = os.getenv("USE_MOCK_EMBEDDINGS", "false").lower() == "true"
        
        if not use_mock:
            # Try to use real Vertex AI embeddings
            try:
                from google.cloud import aiplatform
                from vertexai.language_models import TextEmbeddingModel
                
                logger.info(f"Generating real embeddings for {len(texts)} texts using Vertex AI")
                
                # Initialize the embedding model - use the same model as backend
                model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
                
                # Generate embeddings in batches to handle API limits
                embeddings = []
                batch_size = 5  # Conservative batch size
                
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    batch_embeddings = model.get_embeddings(batch)
                    
                    for embedding in batch_embeddings:
                        embeddings.append(embedding.values)
                
                logger.info(f"Successfully generated {len(embeddings)} real embeddings")
                return embeddings
                
            except Exception as e:
                logger.warning(f"Failed to generate real embeddings: {e}")
                logger.info("Falling back to mock embeddings")
        
        # Generate mock embeddings (fallback or when USE_MOCK_EMBEDDINGS=true)
        logger.info(f"Generating mock embeddings for {len(texts)} texts")
        
        # Generate random embeddings of dimension 768 (common for text embeddings)
        embeddings = []
        for i, text in enumerate(texts):
            # Generate a random embedding vector normalized to unit length
            random_vector = np.random.randn(768)
            normalized_vector = random_vector / np.linalg.norm(random_vector)
            embeddings.append(normalized_vector.tolist())
            
        logger.info(f"Successfully generated {len(embeddings)} mock embeddings")
        return embeddings
    
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}", exc_info=True)
        return None 