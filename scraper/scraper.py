import logging
from datetime import datetime
import json
import time
from typing import List, Dict, Any

# --- Local Imports ---
# Make sure these files exist in the 'utils' and 'config' directories relative to this script
try:
    # Adjust relative paths if needed, assuming utils and config are in the same dir or added to sys.path
    from utils.http import fetch_url
    from utils.parsing import parse_html
    from utils.chunking import chunk_text
    from utils.gcs_utils import upload_string_to_gcs, upload_dict_to_gcs # Import for use in function
    # from utils.gcs_utils import upload_to_gcs # Keep commented out for local run
    # Import embedding service relative to scraper
    from utils.vertex_ai_utils import initialize_vertex_ai_once # For pre-check
    from utils.embedding_service import generate_embeddings # Import the function
    # Assume config is one level up
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..')) # Add parent directory to path
    from config.settings import settings
except ImportError as e:
    print(f"Error importing modules in scraper: {e}")
    # Ensure embedding_service is mentioned in error
    print("Please ensure utils/http.py, utils/parsing.py, utils/chunking.py, utils/gcs_utils.py, utils/vertex_ai_utils.py, utils/embedding_service.py exist")
    print("Also ensure config/settings.py exists in the parent directory (eidbi-query-system/config)")
    exit(1)
# --- End Local Imports ---


# Configure basic logging
# Set level to DEBUG to see more details from utils
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')
# Optionally set lower level for specific loggers
# logging.getLogger('utils.parsing').setLevel(logging.DEBUG)

logger = logging.getLogger(__name__) # Use a specific logger for this module

def scrape_and_process(urls_to_scrape: List[str], upload_to_gcs: bool = False, save_local: bool = True):
    """
    Fetches, parses, chunks data from a list of URLs, optionally uploads to GCS,
    and optionally saves locally.

    Args:
        urls_to_scrape: A list of URLs to process.
        upload_to_gcs: If True, attempts to upload the results to GCS.
        save_local: If True, saves the results locally as a .jsonl file.
    """
    all_processed_chunks_with_embeddings: List[Dict[str, Any]] = []
    processed_url_count = 0
    error_count = 0
    total_chunks_collected = 0

    # --- Initialize Vertex AI Once for Embedding --- 
    # Important: Scraper needs auth and config for embeddings
    logger.info("Initializing Vertex AI for embedding generation (if not already done)...")
    if not initialize_vertex_ai_once():
         logger.error("Vertex AI initialization failed in scraper. Cannot generate embeddings.")
         # Decide how to handle: exit, or continue without embeddings?
         # For now, let's exit as embeddings are crucial.
         return

    logger.info(f"Starting scraping process for {len(urls_to_scrape)} URLs.")

    for url in urls_to_scrape:
        logger.info(f"--- Processing URL: {url} ---")
        url_successful = False
        try:
            # 1. Fetch HTML Content
            logger.info(f"Fetching content from {url}...")
            html_content = fetch_url(url)
            if html_content is None:
                logger.warning(f"No content fetched or HTTP error for {url}. Skipping.")
                error_count += 1
                time.sleep(1) # Add a small delay
                continue

            # 2. Parse HTML for Title and Text
            logger.info(f"Parsing content from {url}...")
            parsed_result = parse_html(html_content)
            if parsed_result is None:
                # parse_html already logs warnings/errors if it returns None
                logger.warning(f"Parsing failed or yielded no content for {url}. Skipping.")
                error_count += 1
                time.sleep(1)
                continue

            page_title = parsed_result.get("title", "No Title Found")
            page_text = parsed_result.get("text", "")

            if not page_text:
                 logger.warning(f"No text extracted after parsing {url}. Skipping chunking.")
                 # Count as processed but maybe note it didn't yield text? For now, just skip chunking.
                 error_count += 1 # Or maybe a different counter?
                 time.sleep(1)
                 continue


            # 3. Chunk the Extracted Text
            logger.info(f"Chunking data from {url} (Title: '{page_title}')...")
            chunks = chunk_text(text=page_text, url=url, title=page_title)
            if not chunks:
                logger.warning(f"No chunks generated for {url}, although text was present. Skipping.")
                # This might indicate an issue in chunking logic or very short text
                error_count += 1
                time.sleep(1)
                continue

            # 4. Generate Embeddings for Chunks
            logger.info(f"Generating embeddings for {len(chunks)} chunks from {url}...")
            chunk_contents = [chunk['content'] for chunk in chunks]
            # Call the embedding service (ensure it's initialized)
            chunk_embeddings = generate_embeddings(chunk_contents)

            if chunk_embeddings is None:
                logger.error(f"Embedding generation failed entirely for chunks from {url}. Skipping URL.")
                error_count += 1
                continue

            # 5. Combine Chunks with Embeddings and Collect
            successful_embeddings_count = 0
            for i, chunk in enumerate(chunks):
                if chunk_embeddings[i] is not None:
                    chunk['embedding'] = chunk_embeddings[i] # Add embedding to the chunk dict
                    all_processed_chunks_with_embeddings.append(chunk)
                    successful_embeddings_count += 1
                else:
                    logger.warning(f"Embedding failed for chunk {i} (ID: {chunk.get('id')}) from {url}. Skipping this chunk.")

            if successful_embeddings_count > 0:
                logger.info(f"Successfully processed, chunked, and embedded {successful_embeddings_count}/{len(chunks)} chunks from {url}.")
                total_chunks_collected += successful_embeddings_count
                processed_url_count += 1
                url_successful = True
            else:
                 logger.error(f"No chunks were successfully embedded for {url}. Marking as error.")
                 error_count += 1

        except Exception as e:
            logger.error(f"An unexpected error occurred processing {url}: {e}", exc_info=True)
            error_count += 1
            # Continue to the next URL even if one fails

        finally:
            # Add a delay between requests, especially if the URL failed, to avoid hammering
             time.sleep(1 if url_successful else 2)


    logger.info(f"--- Finished processing all URLs ---")
    logger.info(f"Successfully processed URLs: {processed_url_count}")
    logger.info(f"URLs with Errors/Skipped: {error_count}")
    logger.info(f"Total chunks collected (with embeddings): {total_chunks_collected}")

    # --- GCS Upload Section (Modified) --- 
    gcs_bucket_name = settings.gcp.bucket_name
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    if upload_to_gcs:
        if not all_processed_chunks_with_embeddings:
            logger.warning("No data collected, skipping GCS upload.")
        else:
            # Upload 1: JSON Lines file (for batch upsert to vector DB)
            try:
                jsonl_filename = f"scraped_data_with_embeddings_{timestamp_str}.jsonl"
                logger.info(f"Preparing JSON Lines data for upload to gs://{gcs_bucket_name}/{jsonl_filename}")
                output_data_str = '\n'.join(json.dumps(chunk) for chunk in all_processed_chunks_with_embeddings)
                logger.info("Uploading JSON Lines file to GCS...")
                success_jsonl = upload_string_to_gcs(
                    data_string=output_data_str,
                    bucket_name=gcs_bucket_name,
                    destination_blob_name=jsonl_filename,
                    content_type='application/jsonl'
                )
                if success_jsonl:
                     logger.info(f"Successfully uploaded {jsonl_filename}")
                else:
                     logger.error(f"Failed to upload {jsonl_filename}")
            except Exception as e:
                 logger.error(f"Failed during GCS JSONL upload: {e}", exc_info=True)

            # Upload 2: Individual chunk files (for backend retrieval)
            logger.info(f"Uploading individual chunk files to GCS path gs://{gcs_bucket_name}/chunks/ ...")
            chunks_uploaded_count = 0
            for chunk in all_processed_chunks_with_embeddings:
                try:
                    chunk_id = chunk.get('id')
                    if not chunk_id:
                         logger.warning("Chunk missing ID, cannot upload individually.")
                         continue
                    chunk_filename = f"chunks/{chunk_id}.json" # Store in a 'chunks' subfolder
                    # Don't need to log every single one unless debugging
                    # logger.debug(f"Uploading chunk {chunk_id} to {chunk_filename}")
                    success_chunk = upload_dict_to_gcs(
                         data_dict=chunk, # Upload the whole chunk dict (incl. content, metadata, embedding)
                         bucket_name=gcs_bucket_name,
                         destination_blob_name=chunk_filename # Use content_type='application/json'
                    )
                    if success_chunk:
                         chunks_uploaded_count += 1
                    else:
                         logger.warning(f"Failed to upload individual chunk: {chunk_filename}")
                except Exception as e:
                    logger.error(f"Error uploading chunk {chunk.get('id','UNKNOWN')} to GCS: {e}", exc_info=True)
            logger.info(f"Finished uploading individual chunks. {chunks_uploaded_count}/{len(all_processed_chunks_with_embeddings)} successful.")
    else:
        logger.info("GCS upload skipped (upload_to_gcs=False).")

    # Save collected chunks locally for review (using JSON Lines format)
    if save_local:
        if not all_processed_chunks_with_embeddings:
            logger.warning("No data collected, skipping local save.")
        else:
            local_output_filename = f"local_scraped_data_with_embeddings_{timestamp_str}.jsonl"
            logger.info(f"Saving collected data (with embeddings) locally to '{local_output_filename}'...")
            try:
                # Save in the same directory as the script, or specify a different path
                script_dir = os.path.dirname(__file__)
                local_save_path = os.path.join(script_dir, local_output_filename)

                with open(local_save_path, 'w', encoding='utf-8') as f:
                    for chunk in all_processed_chunks_with_embeddings:
                        json.dump(chunk, f)
                        f.write('\n') # Write each chunk as a JSON object on a new line
                logger.info(f"Local save successful to '{local_save_path}'.")
            except Exception as e:
                logger.error(f"Failed to save data locally: {e}")
    else:
        logger.info("Local save skipped (save_local=False).")

if __name__ == "__main__":
    logger.info("--- Scraper script starting ---")

    # Check if necessary settings are available before starting
    try:
        _ = settings.gcp.project_id
        gcs_bucket = settings.gcp.bucket_name
        if not gcs_bucket: # Explicitly check if bucket name is set if GCS upload might be enabled
             logger.warning("GCP_BUCKET_NAME is not set in settings. GCS upload will fail if enabled.")
    except AttributeError:
         logger.error("Error accessing GCP settings (settings.gcp.project_id or settings.gcp.bucket_name).")
         logger.error("Please ensure config/settings.py is correct and .env exists with required GCP variables.")
         exit(1)
    except Exception as e:
         logger.error(f"Unexpected error loading settings: {e}")
         exit(1)

    # Define URLs to scrape (consider moving to settings or command-line args)
    urls_to_process = [
        "https://www.dhs.gov/immigration-statistics/yearbook/2022",
        "https://www.dhs.gov/topics/cybersecurity",
        "https://httpbin.org/html",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/status/404",
        "https://invalid-url-that-does-not-exist-abcxyz.com",
    ]

    # --- Choose execution options ---
    ENABLE_GCS_UPLOAD = False # Set to True to enable GCS upload (requires credentials)
    ENABLE_LOCAL_SAVE = True  # Set to True to save results locally
    # ---------------------------------

    logger.info(f"Configuration: GCS Upload = {ENABLE_GCS_UPLOAD}, Local Save = {ENABLE_LOCAL_SAVE}")
    if ENABLE_GCS_UPLOAD:
        logger.info(f"GCS Target Bucket: {gcs_bucket}")

    # Call the main processing function
    scrape_and_process(
        urls_to_scrape=urls_to_process,
        upload_to_gcs=ENABLE_GCS_UPLOAD,
        save_local=ENABLE_LOCAL_SAVE
    )

    logger.info("--- Scraper script finished ---")
