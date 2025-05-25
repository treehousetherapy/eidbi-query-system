# backend/utils/vertex_ai_utils.py

import os
import logging
import vertexai
from google.auth import exceptions as auth_exceptions
import google.auth

logger = logging.getLogger(__name__)

# Get configuration from environment
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "lyrical-ward-454915-e6")
LOCATION = os.getenv("GCP_REGION", "us-central1")

def check_authentication():
    """Check if we have valid GCP authentication."""
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
    Initialize Vertex AI with project and location.
    
    Returns:
        bool: True if initialization is successful, False otherwise.
    """
    try:
        # Check authentication first
        if not check_authentication():
            logger.error("Cannot initialize Vertex AI without valid authentication")
            return False
        
        logger.info(f"Initializing Vertex AI with project={PROJECT_ID}, location={LOCATION}")
        
        # Initialize Vertex AI
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        
        logger.info("Vertex AI initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI: {e}", exc_info=True)
        return False 