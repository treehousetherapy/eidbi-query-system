# eidbi-query-system/scraper/utils/vertex_ai_utils.py

import logging
import os
from google.cloud import aiplatform
from google.api_core.exceptions import GoogleAPICallError

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
    from config.settings import settings
except ImportError as e:
    print(f"Error importing settings in vertex_ai_utils.py: {e}")
    print("Ensure config/settings.py exists relative to the project root.")
    # Fallback or raise error - using placeholder values here
    settings = type('obj', (object,), {
        'gcp': type('obj', (object,), {'project_id': 'your-gcp-project-id-fallback', 'region': 'us-central1'})
    })()
# --- End Import Settings ---

logger = logging.getLogger(__name__)

# Get Project ID and Location from settings
# Ensure these are set in your .env file or default.yaml
PROJECT_ID = settings.gcp.project_id
LOCATION = settings.gcp.region # Using region from settings

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