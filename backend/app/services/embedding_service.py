# eidbi-query-system/backend/app/services/embedding_service.py

import logging
import time
import os
import random
import numpy as np
from typing import List, Optional
import hashlib

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
MODEL_NAME = "textembedding-gecko@003"
MAX_BATCH_SIZE = 5

def initialize_vertex_ai() -> bool:
    """
    Mock implementation of Vertex AI initialization.
    
    Returns:
        bool: True to indicate successful initialization.
    """
    logger.info("Mock initializing Vertex AI for embedding generation...")
    time.sleep(0.5)  # Simulate initialization time
    logger.info("Mock Vertex AI initialization successful")
    return True

def generate_embeddings(texts: List[str]) -> Optional[List[Optional[List[float]]]]:
    """
    Generate deterministic mock embeddings for the given texts.
    
    This is a mock implementation that generates hash-based vectors as embeddings.
    In a real implementation, this would call Vertex AI's embedding API.
    
    Args:
        texts: List of text strings to generate embeddings for.
        
    Returns:
        List of embeddings, where each embedding is a list of floats.
        Returns None if the embedding generation fails.
    """
    if not texts:
        logger.warning("Empty text list provided for embedding generation")
        return []
    
    try:
        logger.info(f"Generating mock embeddings for {len(texts)} texts")
        
        # Generate deterministic embeddings of dimension 768
        embeddings = []
        for text in texts:
            if not text or not isinstance(text, str):
                logger.warning(f"Invalid text provided for embedding: {text}")
                embeddings.append(None)
                continue
                
            # Hash-based deterministic embedding (similar to simple_query.py)
            hash_obj = hashlib.sha256(text.encode('utf-8'))
            hash_bytes = hash_obj.digest()
            
            # Convert hash bytes to a vector of 768 dimensions
            embedding = []
            for i in range(768):
                byte_idx = i % 32
                value = (hash_bytes[byte_idx] / 128.0) - 1.0
                embedding.append(value)
            
            # Normalize the vector
            embedding_np = np.array(embedding)
            norm = np.linalg.norm(embedding_np)
            if norm > 0:
                embedding_np = embedding_np / norm
                
            embeddings.append(embedding_np.tolist())
            
        logger.info(f"Successfully generated {len(embeddings)} mock embeddings")
        return embeddings
    
    except Exception as e:
        logger.error(f"Error generating mock embeddings: {e}", exc_info=True)
        return None

# --- Example Usage (modified) ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')

    print(f"Using Project: {PROJECT_ID}, Location: {LOCATION}")

    # Initialize *once* when testing directly
    if initialize_vertex_ai():
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