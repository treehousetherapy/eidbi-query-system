# eidbi-query-system/scraper/utils/vertex_ai_utils.py

import logging
import os
from google.cloud import aiplatform
from google.api_core.exceptions import GoogleAPICallError
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
try:
    load_dotenv()
except Exception as e:
    logger.warning(f"Failed to load .env file: {e}")
    # Continue without .env - we'll use default credentials

# --- Import Settings ---
# Adjust path to import from the config directory located at the project root
try:
    import sys
    # Assuming this file is in eidbi-query-system/scraper/utils/
    # Go up two levels to reach eidbi-query-system/
    UTILS_DIR = os.path.dirname(__file__)
    SCRAPER_DIR = os.path.dirname(UTILS_DIR)
    PROJECT_ROOT = os.path.dirname(SCRAPER_DIR)
    sys.path.append(PROJECT_ROOT)
    from config.settings import Settings
    settings = Settings.load_settings()
    logger.info(f"Loaded settings: project_id={settings.gcp.project_id}, region={settings.gcp.region}")
except ImportError as e:
    print(f"Error importing settings in vertex_ai_utils.py: {e}")
    print("Ensure config/settings.py exists relative to the project root.")
    # Fallback or raise error - using placeholder values here
    settings = type('obj', (object,), {
        'gcp': type('obj', (object,), {'project_id': 'your-gcp-project-id-fallback', 'region': 'us-central1'})
    })()
# --- End Import Settings ---

# Get Project ID and Location from settings
# Determine the GCP project ID: prefer settings, else use default credentials
try:
    import google.auth
    credentials, default_project_id = google.auth.default()
except Exception as e:
    logger.warning(f"Could not determine default project from credentials: {e}")
    default_project_id = None

# Fallback: attempt to get project ID from gcloud config
if not default_project_id:
    try:
        import subprocess
        default_project_id = subprocess.check_output(
            ["gcloud", "config", "get-value", "project", "--quiet"],
            text=True
        ).strip()
        logger.info(f"Determined default project from gcloud config: {default_project_id}")
    except Exception as e:
        logger.warning(f"Could not get project from gcloud config: {e}")
        # Hardcode project ID from ADC auth we performed earlier
        default_project_id = "lyrical-ward-454915-e6"
        logger.info(f"Using hardcoded project ID: {default_project_id}")

PROJECT_ID = settings.gcp.project_id or default_project_id
LOCATION = settings.gcp.region  # Using region from settings

# Global flag to track initialization state
_vertex_ai_initialized = False

def initialize_vertex_ai_once() -> bool:
    """
    Initialize Vertex AI for embeddings and other services.
    Uses real Vertex AI if credentials are available, otherwise returns False.
    
    Returns:
        bool: True if the initialization is successful, False otherwise.
    """
    global _vertex_ai_initialized
    
    if _vertex_ai_initialized:
        logger.info("Vertex AI already initialized, skipping.")
        return True
    
    # Check if we should use mock embeddings
    use_mock = os.getenv("USE_MOCK_EMBEDDINGS", "false").lower() == "true"
    if use_mock:
        logger.info("Mock embeddings enabled via USE_MOCK_EMBEDDINGS environment variable")
        _vertex_ai_initialized = True
        return True
    
    try:
        logger.info("Initializing Vertex AI for enhanced scraper...")
        
        if not PROJECT_ID:
            logger.error("No GCP project ID available. Cannot initialize Vertex AI.")
            return False
        if not LOCATION:
            logger.error("No GCP location configured. Cannot initialize Vertex AI.")
            return False
        
        # Initialize Vertex AI
        aiplatform.init(project=PROJECT_ID, location=LOCATION)
        
        _vertex_ai_initialized = True
        logger.info(f"Vertex AI initialization successful for project {PROJECT_ID} in {LOCATION}")
        return True
    
    except Exception as e:
        logger.error(f"Vertex AI initialization failed: {e}", exc_info=True)
        logger.info("You can set USE_MOCK_EMBEDDINGS=true to use mock embeddings instead")
        return False

def initialize_vertex_ai():
    """
    Initializes the Vertex AI client library with project ID and location.

    Returns:
        True if initialization was successful or already done, False otherwise.
    """
    if not PROJECT_ID:
        logger.error("GCP_PROJECT_ID is not configured in settings. Cannot initialize Vertex AI.")
        return False
    if not LOCATION:
        logger.error("GCP region (location) is not configured in settings. Cannot initialize Vertex AI.")
        return False

    try:
        logger.info(f"Initializing Vertex AI for Project ID: {PROJECT_ID}, Location: {LOCATION}")
        aiplatform.init(project=PROJECT_ID, location=LOCATION)
        logger.info("Vertex AI initialized successfully.")
        return True
    except GoogleAPICallError as e:
        logger.error(f"Google API Call Error during Vertex AI initialization: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI: {e}", exc_info=True)
        # Log details about credentials if possible
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        logger.error(f"Check credentials. GOOGLE_APPLICATION_CREDENTIALS set to: {creds_path}")
        return False

# --- Example Usage (for testing this module directly) ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')

    print(f"Attempting to initialize Vertex AI with:")
    print(f"  Project ID: {PROJECT_ID}")
    print(f"  Location:   {LOCATION}")
    print(f"  Credentials Env Var: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'Not Set')}")

    if initialize_vertex_ai():
        print("\nVertex AI initialization check successful (or already initialized).")
        # You could add a simple API call here to verify further, e.g., listing models
        # try:
        #     models = aiplatform.Model.list(location=LOCATION)
        #     print(f"Found {len(models)} models in {LOCATION}.")
        # except Exception as e:
        #     print(f"Error making test API call after init: {e}")
    else:
        print("\nVertex AI initialization check failed. Please check logs and configuration.") 