from google.cloud import aiplatform
from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "lyrical-ward-454915-e6")
REGION = os.getenv("GCP_REGION", "us-central1")
INDEX_NAME = "eidbi-index"
ENDPOINT_NAME = "eidbi-index-endpoint"

def initialize_vertex_ai():
    """Initialize Vertex AI with the project and region."""
    aiplatform.init(project=PROJECT_ID, location=REGION)
    print(f"Initialized Vertex AI for project {PROJECT_ID} in region {REGION}")

def create_index():
    """Create a Matching Engine index."""
    try:
        # Check if index already exists
        existing_indexes = MatchingEngineIndex.list()
        for index in existing_indexes:
            if index.display_name == INDEX_NAME:
                print(f"Index {INDEX_NAME} already exists with ID: {index.name}")
                return index

        # Create new index
        index = MatchingEngineIndex.create(
            display_name=INDEX_NAME,
            contents_delta_uri=None,  # We'll update this later
            dimensions=768,  # Default embedding dimension
            approximate_neighbors_count=100,
            distance_measure_type="COSINE_DISTANCE",
            algorithm_config={
                "treeAhConfig": {
                    "leafNodeEmbeddingCount": 100,
                    "leafNodesToSearchPercent": 10
                }
            }
        )
        print(f"Created new index: {index.name}")
        return index
    except Exception as e:
        print(f"Error creating index: {e}")
        raise

def create_endpoint(index):
    """Create a Matching Engine index endpoint."""
    try:
        # Check if endpoint already exists
        existing_endpoints = MatchingEngineIndexEndpoint.list()
        for endpoint in existing_endpoints:
            if endpoint.display_name == ENDPOINT_NAME:
                print(f"Endpoint {ENDPOINT_NAME} already exists with ID: {endpoint.name}")
                return endpoint

        # Create new endpoint
        endpoint = MatchingEngineIndexEndpoint.create(
            display_name=ENDPOINT_NAME,
            description="Endpoint for EIDBI query system",
            network=None,  # Use default network
            index=index,
            deployed_index_id=f"{INDEX_NAME}-deployed",
            machine_type="e2-standard-2",
            min_replica_count=1,
            max_replica_count=1
        )
        print(f"Created new endpoint: {endpoint.name}")
        return endpoint
    except Exception as e:
        print(f"Error creating endpoint: {e}")
        raise

def update_env_file(index, endpoint):
    """Update the .env file with the new index and endpoint IDs."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    
    # Read existing .env file
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value

    # Update with new values
    env_vars['VECTOR_DB_INDEX_ID'] = index.name
    env_vars['VECTOR_DB_INDEX_ENDPOINT_ID'] = endpoint.name

    # Write back to .env file
    with open(env_path, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    print(f"Updated .env file with new index and endpoint IDs")

def main():
    """Main function to set up Vertex AI resources."""
    print("Starting Vertex AI setup...")
    
    # Initialize Vertex AI
    initialize_vertex_ai()
    
    # Create index
    print("\nCreating index...")
    index = create_index()
    
    # Create endpoint
    print("\nCreating endpoint...")
    endpoint = create_endpoint(index)
    
    # Update .env file
    print("\nUpdating .env file...")
    update_env_file(index, endpoint)
    
    print("\nSetup complete! You can now use the index and endpoint in your application.")
    print(f"Index ID: {index.name}")
    print(f"Endpoint ID: {endpoint.name}")

if __name__ == "__main__":
    main() 