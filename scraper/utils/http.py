import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def fetch_url(url: str, timeout: int = 10) -> Optional[str]:
    """
    Fetch HTML content from a URL with proper error handling.

    Args:
        url: The URL to fetch from.
        timeout: Request timeout in seconds.

    Returns:
        HTML content as a string if successful, None otherwise.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        # Attempt to decode using apparent encoding, fallback to utf-8
        response.encoding = response.apparent_encoding or 'utf-8'
        return response.text
    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP Error fetching URL {url}: {e.response.status_code} {e.response.reason}")
        return None # Return None for HTTP errors like 404, 500 etc.
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection Error fetching URL {url}: {str(e)}")
        return None
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout Error fetching URL {url}: {str(e)}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"General Error fetching URL {url}: {str(e)}")
        return None 