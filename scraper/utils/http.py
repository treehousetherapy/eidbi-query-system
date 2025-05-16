import requests
import logging
import time
import random
from typing import Optional, Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

def create_session() -> requests.Session:
    """
    Create a session with retry logic and default headers.
    
    Returns:
        A configured requests Session object
    """
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,  # Total number of retries
        backoff_factor=1,  # Exponential backoff
        status_forcelist=[429, 500, 502, 503, 504],  # Status codes to retry on
        allowed_methods=["GET", "HEAD"]  # HTTP methods to retry
    )
    
    # Mount the adapter to the session
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set default headers to mimic a browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'DNT': '1',  # Do Not Track
    })
    
    return session

# Global session for reuse
_session = None

def fetch_url(url: str, timeout: int = 15, max_retries: int = 3, wait_time: float = 2.0) -> Optional[str]:
    """
    Fetch HTML content from a URL with proper error handling and retry logic.

    Args:
        url: The URL to fetch from.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of manual retries (beyond the session retries).
        wait_time: Base wait time between retries in seconds.

    Returns:
        HTML content as a string if successful, None otherwise.
    """
    global _session
    
    # Initialize session if not already done
    if _session is None:
        _session = create_session()
        logger.info("Created new HTTP session for scraping")
    
    # Track retry attempts
    attempts = 0
    last_exception = None
    
    while attempts <= max_retries:
        try:
            if attempts > 0:
                logger.info(f"Retry attempt {attempts}/{max_retries} for {url}")
                # Add jitter to wait time to avoid predictable patterns
                jitter = random.uniform(0.1, 1.0)
                sleep_time = wait_time * (2 ** (attempts - 1)) + jitter
                logger.info(f"Waiting {sleep_time:.2f} seconds before retrying...")
                time.sleep(sleep_time)
            
            # Make the request using the session
            response = _session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Attempt to decode using apparent encoding, fallback to utf-8
            response.encoding = response.apparent_encoding or 'utf-8'
            
            # Log success after retries
            if attempts > 0:
                logger.info(f"Successfully fetched {url} after {attempts} retries")
                
            return response.text
            
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            logger.warning(f"HTTP Error fetching URL {url}: {status_code} {e.response.reason}")
            
            # Don't retry for certain status codes (e.g., 403 Forbidden, 404 Not Found)
            if status_code in [403, 404, 401]:
                return None
                
            last_exception = e
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error fetching URL {url}: {str(e)}")
            last_exception = e
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout Error fetching URL {url}: {str(e)}")
            last_exception = e
            
        except requests.exceptions.RequestException as e:
            logger.error(f"General Error fetching URL {url}: {str(e)}")
            last_exception = e
        
        attempts += 1
    
    # Log the final failure after all retries
    logger.error(f"Failed to fetch {url} after {max_retries} retries. Last error: {str(last_exception)}")
    return None

def get_page_with_params(url: str, params: Dict[str, Any], timeout: int = 15) -> Optional[str]:
    """
    Fetch a page with query parameters.
    
    Args:
        url: The base URL to fetch from.
        params: Dictionary of query parameters.
        timeout: Request timeout in seconds.
        
    Returns:
        HTML content as a string if successful, None otherwise.
    """
    global _session
    
    # Initialize session if not already done
    if _session is None:
        _session = create_session()
    
    try:
        response = _session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or 'utf-8'
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching URL {url} with params {params}: {str(e)}")
        return None 