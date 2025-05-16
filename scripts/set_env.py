import os

# Set environment variables
os.environ["GCP_PROJECT_ID"] = "lyrical-ward-454915-e6"
os.environ["GCP_REGION"] = "us-central1"
os.environ["GCP_BUCKET_NAME"] = "eidbi-data-bucket" 

print("Environment variables set:")
print(f"GCP_PROJECT_ID: {os.environ.get('GCP_PROJECT_ID')}")
print(f"GCP_REGION: {os.environ.get('GCP_REGION')}")
print(f"GCP_BUCKET_NAME: {os.environ.get('GCP_BUCKET_NAME')}")
print(f"VECTOR_DB_INDEX_ID: {os.environ.get('VECTOR_DB_INDEX_ID')}")
print(f"VECTOR_DB_INDEX_ENDPOINT_ID: {os.environ.get('VECTOR_DB_INDEX_ENDPOINT_ID')}") 