import logging
import re
from typing import Optional, Dict
from bs4 import BeautifulSoup, NavigableString, Tag

logger = logging.getLogger(__name__)

def clean_whitespace(text: str) -> str:
    """
    Replace multiple whitespace characters with a single space
    and strip leading/trailing whitespace.
    """
    if not text:
        return ""
    # Replace various whitespace chars (space, tab, newline, return, formfeed) with a single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_main_content(soup: BeautifulSoup) -> str:
    """
    Tries various strategies to extract the main text content from a parsed HTML document.
    """
    main_content_text = ""

    # Strategy 1: Look for <main> tag
    main_tag = soup.find('main')
    if main_tag:
        logger.debug("Found <main> tag.")
        main_content_text = main_tag.get_text(separator=' ', strip=True)
        if len(main_content_text) > 100: # Arbitrary length check for meaningful content
             return clean_whitespace(main_content_text)

    # Strategy 2: Look for <article> tag
    article_tag = soup.find('article')
    if article_tag:
        logger.debug("Found <article> tag.")
        main_content_text = article_tag.get_text(separator=' ', strip=True)
        if len(main_content_text) > 100:
            return clean_whitespace(main_content_text)

    # Strategy 3: Look for common content divs
    common_selectors = [
        'div[role="main"]',
        '#content', '#main-content', '.content', '.main-content',
        '#bodyContent' # Wikipedia style
    ]
    for selector in common_selectors:
        content_div = soup.select_one(selector)
        if content_div:
            logger.debug(f"Found content using selector: {selector}")
            main_content_text = content_div.get_text(separator=' ', strip=True)
            if len(main_content_text) > 100:
                return clean_whitespace(main_content_text)

    # Strategy 4: Fallback to body if other strategies fail
    logger.debug("Falling back to extracting text from <body>.")
    if soup.body:
        # Remove script and style tags first
        for element in soup.body(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form']):
             element.decompose()
        main_content_text = soup.body.get_text(separator=' ', strip=True)
    else:
        # Very basic fallback if no body
        main_content_text = soup.get_text(separator=' ', strip=True)

    return clean_whitespace(main_content_text)


def parse_html(html_content: str) -> Optional[Dict[str, str]]:
    """
    Parses HTML content to extract the title and main text.

    Args:
        html_content: The HTML content as a string.

    Returns:
        A dictionary with 'title' and 'text' keys if successful,
        otherwise None. Returns None if input is empty or parsing fails
        to find meaningful content.
    """
    logger.info("Parsing HTML...")
    if not html_content:
        logger.warning("HTML content is empty. Cannot parse.")
        return None

    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract Title
        page_title = "No Title Found"
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            page_title = clean_whitespace(title_tag.string)
        logger.debug(f"Extracted Title: {page_title}")

        # Extract Main Text
        extracted_text = extract_main_content(soup)

        if not extracted_text:
            logger.warning("Could not extract meaningful text content from the HTML.")
            # Decide if you want to return None or {'title': page_title, 'text': ''}
            return None

        logger.info(f"Successfully parsed HTML. Title: '{page_title}', Text length: {len(extracted_text)}")
        return {
            "title": page_title,
            "text": extracted_text
        }

    except Exception as e:
        logger.error(f"Error parsing HTML: {e}", exc_info=True)
        return None

# --- Example Usage (for testing) ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG) # Use DEBUG for testing this module

    sample_html_with_main = """
    <html><head><title> Sample Page Title </title></head>
    <body>
        <header>Site Header</header>
        <nav>Navigation Links</nav>
        <main>
            <h1>Main Heading</h1>
            <p>This is the  first paragraph   of the main content. It has extra spaces.</p>
            <p>This is the second paragraph.</p>
            <script>console.log("ignored");</script>
        </main>
        <footer>Site Footer</footer>
    </body></html>
    """

    sample_html_no_main = """
    <html><head><title> Another Page </title></head>
    <body>
        <div class="content">
            <h2>Article Title</h2>
            Some text here. <br> More text.
            <ul><li>Item 1</li><li>Item 2</li></ul>
        </div>
        <div class="sidebar">Sidebar stuff</div>
    </body></html>
    """

    sample_html_body_only = """
    <html><head><title> Body Only </title></head>
    <body>
       Just some basic text directly in the body.   Lots of spaces.
       <script>alert('test');</script>
       And a second line.
    </body></html>
    """

    empty_html = ""
    invalid_html = "<html<head><title>Invalid</title>"


    print("\n--- Test Case 1: With <main> tag ---")
    result1 = parse_html(sample_html_with_main)
    print(result1)

    print("\n--- Test Case 2: With .content div ---")
    result2 = parse_html(sample_html_no_main)
    print(result2)

    print("\n--- Test Case 3: Body only ---")
    result3 = parse_html(sample_html_body_only)
    print(result3)

    print("\n--- Test Case 4: Empty Input ---")
    result4 = parse_html(empty_html)
    print(result4)

    print("\n--- Test Case 5: Invalid HTML ---")
    result5 = parse_html(invalid_html) # BeautifulSoup might still parse some of it
    print(result5) 