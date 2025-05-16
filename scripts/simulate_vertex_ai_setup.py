import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "lyrical-ward-454915-e6")
REGION = os.getenv("GCP_REGION", "us-central1")
INDEX_NAME = "eidbi-index"
ENDPOINT_NAME = "eidbi-index-endpoint"

# Simulated IDs
SIMULATED_INDEX_ID = f"projects/{PROJECT_ID}/locations/{REGION}/indexes/1234567890"
SIMULATED_ENDPOINT_ID = f"projects/{PROJECT_ID}/locations/{REGION}/indexEndpoints/0987654321"

def update_env_file():
    """Update the .env file with the simulated index and endpoint IDs."""
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
    env_vars['VECTOR_DB_INDEX_ID'] = SIMULATED_INDEX_ID
    env_vars['VECTOR_DB_INDEX_ENDPOINT_ID'] = SIMULATED_ENDPOINT_ID

    # Write back to .env file
    with open(env_path, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    print(f"Updated .env file with simulated index and endpoint IDs")

def main():
    """Main function to simulate setting up Vertex AI resources."""
    print("Starting Vertex AI setup simulation...")
    print(f"Initialized Vertex AI for project {PROJECT_ID} in region {REGION}")
    
    # Simulate creating index
    print("\nSimulating index creation...")
    print(f"Index {INDEX_NAME} created with ID: {SIMULATED_INDEX_ID}")
    
    # Simulate creating endpoint
    print("\nSimulating endpoint creation...")
    print(f"Endpoint {ENDPOINT_NAME} created with ID: {SIMULATED_ENDPOINT_ID}")
    
    # Update .env file
    print("\nUpdating .env file...")
    update_env_file()
    
    print("\nSimulation complete! You can now use the simulated index and endpoint IDs in your application.")
    print(f"Index ID: {SIMULATED_INDEX_ID}")
    print(f"Endpoint ID: {SIMULATED_ENDPOINT_ID}")
    print("\nNOTE: These are simulated values. In a real environment, you would need to create actual Vertex AI resources.")

if __name__ == "__main__":
    main() 