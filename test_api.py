import requests
from http import HTTPStatus
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

def test_root():
    """Test the root endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/")
        logger.info(f"Root endpoint response: {response.json()}")
        return response.ok
    except Exception as e:
        logger.error(f"Error testing root endpoint: {e}")
        return False

def test_embeddings():
    """Test the generate-embeddings endpoint."""
    try:
        data = {"texts": ["This is a test sentence for embedding generation."]}
        logger.info(f"Sending request to embedding endpoint with data: {data}")
        
        response = requests.post(
            f"{BASE_URL}/generate-embeddings",
            json=data
        )
        
        logger.info(f"Embedding response status: {response.status_code}")
        
        if response.ok:
            result = response.json()
            logger.info(f"Embedding response type: {type(result)}")
            logger.info(f"Embedding response content: {result}")
            
            if result is None:
                logger.error("Response JSON returned None")
                return False
                
            # Check if it's a list
            if isinstance(result, list):
                logger.info(f"Generated embeddings list length: {len(result)}")
                if len(result) > 0:
                    if result[0] is None:
                        logger.error("First embedding is None")
                    else:
                        logger.info(f"First embedding length: {len(result[0])}")
            else:
                logger.error(f"Expected list response, got {type(result)}")
        else:
            logger.error(f"Failed to generate embeddings: Status {response.status_code}")
            logger.error(f"Response text: {response.text}")
        
        return response.ok
    except Exception as e:
        logger.error(f"Error testing embeddings endpoint: {e}", exc_info=True)
        return False

def main():
    """Run all tests."""
    logger.info("Starting API tests...")
    
    # Test root endpoint
    if test_root():
        logger.info("Root endpoint test passed.")
    else:
        logger.error("Root endpoint test failed.")
        return
    
    # Test embeddings endpoint
    if test_embeddings():
        logger.info("Embeddings endpoint test passed.")
    else:
        logger.error("Embeddings endpoint test failed.")

if __name__ == "__main__":
    main() 