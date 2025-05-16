# eidbi-query-system/scraper/utils/gcs_utils.py

import logging
import json
import os
from typing import Dict, Any, Optional
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

logger = logging.getLogger(__name__)

def _get_gcs_bucket(bucket_name: str) -> Optional[storage.Bucket]:
    """Helper to get a GCS bucket object, handling client init and existence check."""
    try:
        # Initialize GCS client
        # Assumes GOOGLE_APPLICATION_CREDENTIALS env var is set or other auth is configured.
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        if not bucket.exists():
            logger.error(f"Bucket '{bucket_name}' does not exist or you lack permissions to access it.")
            # Optionally attempt creation:
            # try:
            #     bucket = storage_client.create_bucket(bucket_name)
            #     logger.info(f"Bucket {bucket_name} created.")
            #     return bucket
            # except GoogleCloudError as create_error:
            #     logger.error(f"Failed to create bucket {bucket_name}: {create_error}")
            #     return None
            return None
        return bucket
    except GoogleCloudError as e:
        logger.error(f"Failed to initialize GCS client or get bucket '{bucket_name}': {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting GCS bucket '{bucket_name}': {e}", exc_info=True)
        return None


def upload_string_to_gcs(data_string: str, bucket_name: str, destination_blob_name: str, content_type: str = 'text/plain') -> bool:
    """
    Mock implementation that saves string data to a local file instead of uploading to GCS.
    
    Args:
        data_string: The string data to store
        bucket_name: Unused - would be the GCS bucket name in real implementation
        destination_blob_name: Used as the local filename
        content_type: Unused - would specify the content type in real implementation
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Mock GCS: Saving string data to local file '{destination_blob_name}'")
        
        # Create directory if it doesn't exist
        os.makedirs('local_gcs_mock', exist_ok=True)
        local_path = os.path.join('local_gcs_mock', destination_blob_name)
        
        # Create directories in the path if they don't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Write the data to the file
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(data_string)
            
        logger.info(f"Mock GCS: Successfully saved data to '{local_path}'")
        return True
        
    except Exception as e:
        logger.error(f"Mock GCS: Error saving data to local file: {e}", exc_info=True)
        return False


def upload_dict_to_gcs(data_dict: Dict[str, Any], bucket_name: str, destination_blob_name: str) -> bool:
    """
    Mock implementation that saves dictionary data as JSON to a local file instead of uploading to GCS.
    
    Args:
        data_dict: The dictionary to store as JSON
        bucket_name: Unused - would be the GCS bucket name in real implementation
        destination_blob_name: Used as the local filename
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Mock GCS: Saving dictionary data to local file '{destination_blob_name}'")
        
        # Convert dict to JSON string
        json_str = json.dumps(data_dict, ensure_ascii=False)
        
        # Use the string upload function
        return upload_string_to_gcs(
            data_string=json_str, 
            bucket_name=bucket_name,
            destination_blob_name=destination_blob_name,
            content_type='application/json'
        )
        
    except Exception as e:
        logger.error(f"Mock GCS: Error converting dict to JSON or saving: {e}", exc_info=True)
        return False


def read_json_from_gcs(bucket_name: str, blob_name: str) -> Optional[Dict[str, Any]]:
    """
    Mock implementation that reads a JSON file from local storage instead of GCS.
    
    Args:
        bucket_name: Unused - would be the GCS bucket name in real implementation
        blob_name: The local filename to read
        
    Returns:
        Dict or None: The JSON content as a dictionary, or None if reading fails
    """
    try:
        logger.info(f"Mock GCS: Reading JSON data from local file '{blob_name}'")
        
        local_path = os.path.join('local_gcs_mock', blob_name)
        
        # Check if file exists
        if not os.path.exists(local_path):
            logger.warning(f"Mock GCS: File '{local_path}' does not exist")
            return None
            
        # Read the JSON file
        with open(local_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        logger.info(f"Mock GCS: Successfully read JSON data from '{local_path}'")
        return data
        
    except Exception as e:
        logger.error(f"Mock GCS: Error reading JSON from local file: {e}", exc_info=True)
        return None


# --- Example Usage (for testing this module directly) ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # --- Configuration (Replace or load from settings/env) ---
    # IMPORTANT: Set GOOGLE_APPLICATION_CREDENTIALS environment variable
    TEST_BUCKET_NAME = "your-gcs-bucket-name"  # <<< CHANGE THIS
    TEST_BLOB_NAME_JSON = "test/my_test_dict_upload.json"
    TEST_BLOB_NAME_JSONL = "test/my_test_string_upload.jsonl"
    # --- End Configuration ---

    if TEST_BUCKET_NAME == "your-gcs-bucket-name":
        print("Please update TEST_BUCKET_NAME in the script before running the example.")
    else:
        # Test Dictionary Upload
        print("\n--- Testing Dictionary Upload ---")
        sample_dictionary = {
            "name": "Test Document", "version": 1.0,
            "items": [{"id": 1, "value": "apple"}, {"id": 2, "value": "banana"}],
            "processed": True
        }
        success_dict = upload_dict_to_gcs(
            data_dict=sample_dictionary,
            bucket_name=TEST_BUCKET_NAME,
            destination_blob_name=TEST_BLOB_NAME_JSON
        )
        if success_dict: print("Dictionary upload successful.")
        else: print("Dictionary upload failed.")

        # Test String Upload (as JSON Lines)
        print("\n--- Testing String Upload (JSON Lines) ---")
        chunks_for_jsonl = [
            {"id": "chunk1", "content": "Line 1 content.", "metadata": {"url": "url1"}},
            {"id": "chunk2", "content": "Line 2 content.", "metadata": {"url": "url1"}},
            {"id": "chunk3", "content": "Line 3 content.", "metadata": {"url": "url2"}},
        ]
        jsonl_string = '\n'.join(json.dumps(chunk) for chunk in chunks_for_jsonl)

        success_string = upload_string_to_gcs(
            data_string=jsonl_string,
            bucket_name=TEST_BUCKET_NAME,
            destination_blob_name=TEST_BLOB_NAME_JSONL,
            content_type='application/jsonl' # Important for JSON Lines
        )
        if success_string: print("String (JSONL) upload successful.")
        else: print("String (JSONL) upload failed.")

        if TEST_BUCKET_NAME != "your-gcs-bucket-name":
            # Test Reading JSON (assuming the dict upload test ran successfully)
            print("\n--- Testing JSON Read --- ")
            retrieved_dict = read_json_from_gcs(
                bucket_name=TEST_BUCKET_NAME,
                blob_name=TEST_BLOB_NAME_JSON
            )
            if retrieved_dict:
                print(f"Successfully read dict back from GCS:")
                print(json.dumps(retrieved_dict, indent=2))
            else:
                print("Failed to read dict from GCS. Check logs or if the file exists.")

            print("\n--- Testing JSON Read (Non-existent file) --- ")
            retrieved_dict_fail = read_json_from_gcs(
                bucket_name=TEST_BUCKET_NAME,
                blob_name="test/non_existent_file.json"
            )
            if retrieved_dict_fail is None:
                print("Correctly failed to read non-existent file (returned None).")
            else:
                print("ERROR: Read non-existent file did not return None.") 