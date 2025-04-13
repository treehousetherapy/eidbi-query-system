# eidbi-query-system/scraper/utils/gcs_utils.py

import logging
import json
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


def upload_string_to_gcs(
    data_string: str,
    bucket_name: str,
    destination_blob_name: str,
    content_type: str = 'text/plain' # Default to text, change as needed (e.g., 'application/jsonl')
) -> bool:
    """
    Uploads a string directly to a GCS bucket.

    Args:
        data_string: The string data to upload.
        bucket_name: The name of the target GCS bucket.
        destination_blob_name: The desired path/name for the file within the bucket.
        content_type: The content type of the uploaded file.

    Returns:
        True if the upload was successful, False otherwise.
    """
    bucket = _get_gcs_bucket(bucket_name)
    if not bucket:
        return False

    try:
        # Create a blob object
        blob = bucket.blob(destination_blob_name)

        # Upload the string
        logger.info(f"Uploading string data to gs://{bucket_name}/{destination_blob_name}...")
        blob.upload_from_string(
            data=data_string,
            content_type=content_type
        )

        logger.info(f"Successfully uploaded to gs://{bucket_name}/{destination_blob_name}")
        return True

    except GoogleCloudError as e:
        logger.error(f"GCS Error uploading string to gs://{bucket_name}/{destination_blob_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during string upload to GCS: {e}", exc_info=True)
        return False


def upload_dict_to_gcs(
    data_dict: Dict[str, Any],
    bucket_name: str,
    destination_blob_name: str,
    content_type: str = 'application/json'
) -> bool:
    """
    Uploads a Python dictionary as a JSON string to a GCS bucket.

    Args:
        data_dict: The Python dictionary to upload.
        bucket_name: The name of the target GCS bucket.
        destination_blob_name: The desired path/name for the file within the bucket.
        content_type: The content type of the uploaded file. Defaults to 'application/json'.

    Returns:
        True if the upload was successful, False otherwise.
    """
    try:
        # Convert dictionary to JSON string
        json_data = json.dumps(data_dict, indent=2) # Using indent for readability
    except TypeError as e:
        logger.error(f"Failed to serialize dictionary to JSON for GCS upload: {e}")
        return False

    # Use the string upload function
    return upload_string_to_gcs(
        data_string=json_data,
        bucket_name=bucket_name,
        destination_blob_name=destination_blob_name,
        content_type=content_type
    )


def read_json_from_gcs(bucket_name: str, blob_name: str) -> Optional[Dict[str, Any]]:
    """
    Reads a JSON file from GCS and parses it into a Python dictionary.

    Args:
        bucket_name: The name of the GCS bucket.
        blob_name: The full path/name of the blob within the bucket.

    Returns:
        A dictionary parsed from the JSON file, or None if an error occurs.
    """
    bucket = _get_gcs_bucket(bucket_name)
    if not bucket:
        return None

    blob = bucket.blob(blob_name)

    try:
        logger.info(f"Reading JSON data from gs://{bucket_name}/{blob_name}...")
        json_string = blob.download_as_text()
        data_dict = json.loads(json_string)
        logger.debug(f"Successfully read and parsed JSON from gs://{bucket_name}/{blob_name}")
        return data_dict

    except GoogleCloudError as e:
        if e.code == 404:
            logger.warning(f"Blob not found in GCS: gs://{bucket_name}/{blob_name}")
        else:
            logger.error(f"GCS Error reading blob gs://{bucket_name}/{blob_name}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from blob gs://{bucket_name}/{blob_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred reading from GCS: {e}", exc_info=True)
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