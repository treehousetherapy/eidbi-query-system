# eidbi-query-system/config/settings.py

from pathlib import Path
from typing import List, Optional, Any
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os

# Determine the root directory (eidbi-query-system)
# This assumes settings.py is in eidbi-query-system/config/
ROOT_DIR = Path(__file__).parent.parent

def load_yaml_config() -> dict:
    """Load the YAML configuration file."""
    config_path = ROOT_DIR / "config" / "default.yaml"
    if not config_path.exists():
        print(f"Warning: YAML config file not found at {config_path}")
        return {}
    try:
        with open(config_path, "r", encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML config file {config_path}: {e}")
        return {}

class GCPSettings(BaseSettings):
    project_id: Optional[str] = Field(None, env='GCP_PROJECT_ID')
    bucket_name: Optional[str] = Field(None, env='GCP_BUCKET_NAME')
    region: str = Field("us-central1", env='GCP_REGION')

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

class APISettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    prefix: str = "/api/v1"

    model_config = SettingsConfigDict(
        env_prefix='API_',
        env_file=ROOT_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

class StreamlitSettings(BaseSettings):
    page_title: str = "My App"
    page_icon: str = "🚀"
    layout: str = "wide"

    model_config = SettingsConfigDict(
        env_prefix='STREAMLIT_',
        env_file=ROOT_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

class AppSettings(BaseSettings):
    cache_ttl: int = 3600
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = [".pdf", ".txt", ".csv"]
    target_urls: List[str] = [] # Add target_urls here

    model_config = SettingsConfigDict(
        env_prefix='APP_',
        env_file=ROOT_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

class VectorDBSettings(BaseSettings):
    index_id: Optional[str] = Field(None)
    index_endpoint_id: Optional[str] = Field(None)
    num_neighbors: int = 10

    # Pydantic V2 configuration
    model_config = SettingsConfigDict(
        env_prefix='VECTOR_DB_', # e.g., VECTOR_DB_INDEX_ID
        env_file=ROOT_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

class Settings(BaseSettings):
    """Main settings class loading from YAML and environment variables."""
    api: APISettings
    gcp: GCPSettings
    streamlit: StreamlitSettings
    app: AppSettings
    vector_db: VectorDBSettings # Add VectorDB settings

    model_config = SettingsConfigDict(
        env_file = ROOT_DIR / '.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        case_sensitive=True,
        extra='ignore'
    )

    @classmethod
    def load_settings(cls) -> 'Settings':
        """Load settings from YAML and environment variables."""
        yaml_config = load_yaml_config()
        
        # Load GCP settings from environment variables
        yaml_config['gcp'] = {
            'project_id': os.getenv('GCP_PROJECT_ID'),
            'bucket_name': os.getenv('GCP_BUCKET_NAME'),
            'region': os.getenv('GCP_REGION', 'us-central1')
        }
        
        return cls(**yaml_config)

# Create a global settings instance by calling the custom loader
settings = Settings.load_settings() 