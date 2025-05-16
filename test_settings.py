import sys
import os
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info(f"Environment variables: GCP_PROJECT_ID={os.getenv('GCP_PROJECT_ID')}, GCP_REGION={os.getenv('GCP_REGION')}")

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

try:
    from config.settings import Settings
    settings = Settings.load_settings()
    logger.info(f"Loaded settings: project_id={settings.gcp.project_id}, region={settings.gcp.region}")
except Exception as e:
    logger.error(f"Error loading settings: {e}", exc_info=True) 