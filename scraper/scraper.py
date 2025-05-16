import logging
from datetime import datetime
import json
import time
import random
from typing import List, Dict, Any, Set, Optional
from urllib.parse import urljoin, urlparse

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
    from bs4 import BeautifulSoup  # Make sure this is imported for the link extraction
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

# Base DHS domain for URL validation
DHS_DOMAIN = "mn.gov"
EIDBI_KEYWORD_PATTERNS = [
    "eidbi", "early intensive", "developmental", "behavioral intervention",
    "autism", "asd", "spectrum disorder", "neurodevelopmental"
]

def is_valid_dhs_url(url: str) -> bool:
    """
    Check if a URL is a valid Minnesota DHS URL.
    """
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        # Check if the domain is part of mn.gov
        if DHS_DOMAIN not in domain:
            return False
            
        # Make sure it's not an asset, image, or document link
        path = parsed_url.path.lower()
        file_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.csv']
        for ext in file_extensions:
            if path.endswith(ext):
                return False
                
        # Avoid specific paths that are not content pages
        excluded_paths = ['/search/', '/login/', '/user/', '/admin/', '/media/']
        for excluded in excluded_paths:
            if excluded in path:
                return False
                
        return True
    except Exception:
        return False

def is_eidbi_related(url: str, text: Optional[str] = None) -> bool:
    """
    Check if a URL or its content is related to EIDBI.
    """
    # Check URL first
    url_lower = url.lower()
    
    # Quick positive check for EIDBI in URL
    if "eidbi" in url_lower:
        return True
    
    # Check for other keywords in URL
    for pattern in EIDBI_KEYWORD_PATTERNS:
        if pattern in url_lower:
            return True
    
    # If text content is provided, check it as well
    if text:
        text_lower = text.lower()
        if "eidbi" in text_lower:
            return True
            
        # Check if multiple patterns appear in the text
        matches = 0
        for pattern in EIDBI_KEYWORD_PATTERNS:
            if pattern in text_lower:
                matches += 1
                # If we find at least 2 matches, consider it related
                if matches >= 2:
                    return True
    
    return False

def extract_links_from_page(html_content: str, base_url: str) -> List[str]:
    """
    Extract links from a page, focusing on Minnesota DHS links.
    
    Args:
        html_content: The HTML content of the page
        base_url: The base URL for resolving relative links
        
    Returns:
        A list of valid, absolute URLs
    """
    if not html_content:
        return []
        
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        # Find all anchor tags with href attribute
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '').strip()
            
            # Skip empty links, javascript, and anchors
            if not href or href.startswith('javascript:') or href.startswith('#'):
                continue
                
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            
            # Validate the URL
            if is_valid_dhs_url(absolute_url):
                # Check if the link text or URL contains EIDBI-related keywords
                link_text = a_tag.get_text().strip()
                if is_eidbi_related(absolute_url, link_text):
                    links.append(absolute_url)
        
        return links
    except Exception as e:
        logger.error(f"Error extracting links from {base_url}: {e}")
        return []

def crawl_for_eidbi_content(seed_urls: List[str], max_depth: int = 2, max_pages: int = 50) -> List[str]:
    """
    Crawl DHS website starting from seed URLs to find EIDBI-related content.
    
    Args:
        seed_urls: Starting URLs for the crawl
        max_depth: Maximum link depth to crawl
        max_pages: Maximum number of pages to collect
        
    Returns:
        List of EIDBI-related URLs
    """
    visited_urls: Set[str] = set()
    to_visit: List[Dict[str, Any]] = [{"url": url, "depth": 0} for url in seed_urls]
    collected_urls: List[str] = []
    
    logger.info(f"Starting crawl from {len(seed_urls)} seed URLs with max depth {max_depth}")
    
    while to_visit and len(collected_urls) < max_pages:
        current = to_visit.pop(0)
        current_url = current["url"]
        current_depth = current["depth"]
        
        # Skip if already visited
        if current_url in visited_urls:
            continue
            
        visited_urls.add(current_url)
        logger.info(f"Crawling: {current_url} (depth: {current_depth})")
        
        # Fetch the page
        html_content = fetch_url(current_url)
        if not html_content:
            logger.warning(f"Failed to fetch {current_url}")
            # Add random delay before continuing
            time.sleep(random.uniform(2.0, 4.0))
            continue
            
        # Parse the content
        parsed_result = parse_html(html_content)
        if not parsed_result:
            logger.warning(f"Failed to parse {current_url}")
            time.sleep(random.uniform(2.0, 4.0))
            continue
            
        # Check if the page content is related to EIDBI
        page_text = parsed_result.get("text", "")
        if is_eidbi_related(current_url, page_text):
            logger.info(f"Found EIDBI-related content: {current_url}")
            collected_urls.append(current_url)
            
        # If we haven't reached max depth, extract and add new links
        if current_depth < max_depth:
            links = extract_links_from_page(html_content, current_url)
            logger.info(f"Found {len(links)} potential EIDBI-related links on {current_url}")
            
            # Add new links to the queue
            for link in links:
                if link not in visited_urls:
                    to_visit.append({"url": link, "depth": current_depth + 1})
                    
        # Add a polite delay between requests (with randomization)
        delay = random.uniform(3.0, 5.0)
        logger.info(f"Waiting {delay:.2f} seconds before next request...")
        time.sleep(delay)
    
    logger.info(f"Crawl complete. Found {len(collected_urls)} EIDBI-related URLs")
    return collected_urls

def scrape_and_process(urls_to_scrape: List[str], upload_to_gcs: bool = False, save_local: bool = True, 
                      crawl_first: bool = False, crawl_depth: int = 2, max_pages: int = 50):
    """
    Fetches, parses, chunks data from a list of URLs, optionally uploads to GCS,
    and optionally saves locally.

    Args:
        urls_to_scrape: A list of URLs to process.
        upload_to_gcs: If True, attempts to upload the results to GCS.
        save_local: If True, saves the results locally as a .jsonl file.
        crawl_first: If True, crawl from seed URLs to find more EIDBI content.
        crawl_depth: Maximum depth for crawling.
        max_pages: Maximum pages to collect during crawling.
    """
    # If crawl_first is enabled, use the provided URLs as seeds
    if crawl_first:
        logger.info(f"Crawling for EIDBI content from {len(urls_to_scrape)} seed URLs...")
        urls_to_scrape = crawl_for_eidbi_content(seed_urls=urls_to_scrape, max_depth=crawl_depth, max_pages=max_pages)
        logger.info(f"Crawl complete. Found {len(urls_to_scrape)} URLs to scrape.")
    
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
                time.sleep(random.uniform(2.0, 4.0))  # Add a randomized delay
                continue

            # 2. Parse HTML for Title and Text
            logger.info(f"Parsing content from {url}...")
            parsed_result = parse_html(html_content)
            if parsed_result is None:
                # parse_html already logs warnings/errors if it returns None
                logger.warning(f"Parsing failed or yielded no content for {url}. Skipping.")
                error_count += 1
                time.sleep(random.uniform(2.0, 4.0))
                continue

            page_title = parsed_result.get("title", "No Title Found")
            page_text = parsed_result.get("text", "")
            
            # Add structured content if available
            tables = parsed_result.get("tables", [])
            lists = parsed_result.get("lists", [])
            
            # Extract structured content to enhance the page text
            if tables or lists:
                logger.info(f"Found structured content: {len(tables)} tables, {len(lists)} lists")
                
                # Add tables as text
                if tables:
                    for table in tables:
                        caption = table.get("caption", "Table")
                        page_text += f"\n\n{caption}:\n"
                        headers = table.get("headers", [])
                        
                        for row in table.get("data", []):
                            row_text = " | ".join([f"{headers[i]}: {row.get(header, '')}" 
                                                 for i, header in enumerate(headers) if i < len(headers)])
                            page_text += f"\n{row_text}"
                
                # Add lists as text
                if lists:
                    for list_item in lists:
                        title = list_item.get("title", "List")
                        page_text += f"\n\n{title}:\n"
                        
                        for idx, item in enumerate(list_item.get("items", [])):
                            page_text += f"\n- {item}"

            if not page_text:
                 logger.warning(f"No text extracted after parsing {url}. Skipping chunking.")
                 # Count as processed but maybe note it didn't yield text? For now, just skip chunking.
                 error_count += 1 # Or maybe a different counter?
                 time.sleep(random.uniform(2.0, 4.0))
                 continue


            # 3. Chunk the Extracted Text
            logger.info(f"Chunking data from {url} (Title: '{page_title}')...")
            chunks = chunk_text(text=page_text, url=url, title=page_title)
            if not chunks:
                logger.warning(f"No chunks generated for {url}, although text was present. Skipping.")
                # This might indicate an issue in chunking logic or very short text
                error_count += 1
                time.sleep(random.uniform(2.0, 4.0))
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
            # Add a delay between requests with randomization to avoid rate limiting
            delay = random.uniform(3.0, 6.0) if url_successful else random.uniform(5.0, 8.0)
            logger.info(f"Waiting {delay:.2f} seconds before next request...")
            time.sleep(delay)


    logger.info(f"--- Finished processing all URLs ---")
    logger.info(f"Successfully processed URLs: {processed_url_count}")
    logger.info(f"URLs with Errors/Skipped: {error_count}")
    logger.info(f"Total chunks collected (with embeddings): {total_chunks_collected}")

    # --- Save Local Files Section --- 
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if save_local and all_processed_chunks_with_embeddings:
        local_jsonl_filename = f"local_scraped_data_with_embeddings_{timestamp_str}.jsonl"
        logger.info(f"Saving data locally to {local_jsonl_filename}...")
        
        try:
            with open(local_jsonl_filename, 'w', encoding='utf-8') as f:
                for chunk in all_processed_chunks_with_embeddings:
                    f.write(json.dumps(chunk) + '\n')
            logger.info(f"Successfully saved data to {local_jsonl_filename}")
            
            # Also save a text file with just the URLs for reference
            urls_filename = f"scraped_urls_{timestamp_str}.txt"
            with open(urls_filename, 'w', encoding='utf-8') as f:
                # Collect unique URLs from the chunks
                unique_urls = set(chunk.get('url', '') for chunk in all_processed_chunks_with_embeddings)
                for url in unique_urls:
                    if url:
                        f.write(url + '\n')
            logger.info(f"Saved list of {len(unique_urls)} unique URLs to {urls_filename}")
            
        except Exception as e:
            logger.error(f"Error saving data locally: {e}")

    # --- GCS Upload Section --- 
    if upload_to_gcs:
        gcs_bucket_name = settings.gcp.bucket_name
        
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
                except Exception as e:
                     logger.error(f"Error uploading chunk {chunk.get('id')}: {e}")
                     # Continue with other chunks
            
            logger.info(f"Uploaded {chunks_uploaded_count}/{len(all_processed_chunks_with_embeddings)} chunk files to GCS.")

    return all_processed_chunks_with_embeddings

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
        # MN DHS EIDBI Program Pages
        "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=DHS-293662",  # Main EIDBI page
        "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs-305956",  # EIDBI Benefit Policy Manual
        "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs-292229",  # EIDBI Provider Information 
        "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=DHS-293657",  # EIDBI Service Options
        "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs-292657",  # EIDBI Covered Services
        "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_155989",  # EIDBI FAQ
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
