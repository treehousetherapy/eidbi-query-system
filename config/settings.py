# eidbi-query-system/config/settings.py

from pathlib import Path
from typing import List, Optional, Any
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

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
    project_id: Optional[str] = Field(None)
    bucket_name: Optional[str] = Field(None)
    region: str = "us-central1"

    model_config = SettingsConfigDict(
        env_prefix='GCP_',
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
        extra='ignore'
    )

    @classmethod
    def load_settings(cls) -> 'Settings':
        yaml_config = load_yaml_config()
        # Initialize nested settings classes if they are present in YAML
        # This helps Pydantic v2 handle nested BaseSettings loaded from dict
        if 'api' in yaml_config: yaml_config['api'] = APISettings(**yaml_config.get('api', {}))
        if 'gcp' in yaml_config: yaml_config['gcp'] = GCPSettings(**yaml_config.get('gcp', {}))
        if 'streamlit' in yaml_config: yaml_config['streamlit'] = StreamlitSettings(**yaml_config.get('streamlit', {}))
        if 'app' in yaml_config: yaml_config['app'] = AppSettings(**yaml_config.get('app', {}))
        if 'vector_db' in yaml_config: yaml_config['vector_db'] = VectorDBSettings(**yaml_config.get('vector_db', {}))

        return cls(**yaml_config)

# Create a global settings instance by calling the custom loader
settings = Settings.load_settings() 