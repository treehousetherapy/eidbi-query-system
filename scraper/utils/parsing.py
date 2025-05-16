import logging
import re
from typing import Optional, Dict, List
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

def remove_unwanted_elements(soup: BeautifulSoup) -> None:
    """
    Remove elements that are not relevant to the main content.
    """
    # Common elements to remove
    selectors_to_remove = [
        'script', 'style', 'noscript', 'iframe', 'svg',
        'header', 'footer', 'nav',
        '.navigation', '.breadcrumbs', '.sidebar', '.menu', '.search',
        '#navigation', '#header', '#footer', '#sidebar',
        '[role="navigation"]', '[role="banner"]', '[role="complementary"]',
        'form', '.social-media', '.share-buttons', '.pagination',
        '#skip-to-content', '.skip-to-content', '.skip-link',
        '.cookie-notice', '.copyright',
        # Minnesota DHS specific selectors (add more as you discover them)
        '#globalHeader', '#globalFooter', '#utilityHeader', '#pageActions',
        '.relatedTopics', '.lastUpdated', '.sidebarSection', 
        '#leftCol', '.sidenav', '.dhs-utility', '.dhs-header',
        '.dhs-mega-menu', '.dhs-footer', '.back-to-top',
        '#search-box', '#ctl00_PlaceHolderSearchArea_SearchBoxScriptWebPart1'
    ]
    
    for selector in selectors_to_remove:
        for element in soup.select(selector):
            element.decompose()

def extract_main_content(soup: BeautifulSoup) -> str:
    """
    Tries various strategies to extract the main text content from a parsed HTML document.
    Specifically optimized for Minnesota DHS website structure.
    """
    # First, remove elements we don't want
    remove_unwanted_elements(soup)
    
    # List of strategies to try, in descending order of preference
    content_strategies = [
        # Minnesota DHS specific selectors (based on their page structure)
        lambda s: s.select_one('#mainContent'),
        lambda s: s.select_one('#ctl00_PlaceHolderMain_ctl01__ControlWrapper_RichHtmlField'),
        lambda s: s.select_one('.dhsContent'),
        lambda s: s.select_one('.mainContent'),
        lambda s: s.select_one('.main-content'),
        lambda s: s.select_one('#content'),
        lambda s: s.select_one('div.ms-rtestate-field'),  # Common in SharePoint sites like DHS
        
        # Standard content containers
        lambda s: s.find('main'),
        lambda s: s.find('article'),
        lambda s: s.select_one('div[role="main"]'),
        lambda s: s.select_one('#bodyContent'),
        
        # Fallback strategies
        lambda s: s.select_one('.container'),
        lambda s: s.select_one('.content'),
        lambda s: s.body if s.body else s
    ]
    
    # Try each strategy in order
    for strategy in content_strategies:
        try:
            content_element = strategy(soup)
            if content_element:
                # Check if the content is meaningful
                text = content_element.get_text(separator=' ', strip=True)
                if len(text) > 100:  # Arbitrary length check for meaningful content
                    logger.debug(f"Found content using strategy: {strategy.__name__ if hasattr(strategy, '__name__') else str(strategy)}")
                    return clean_whitespace(text)
        except Exception as e:
            logger.debug(f"Error with content extraction strategy: {e}")
            continue
    
    # If we reach here, no strategy worked well - fall back to body
    logger.debug("All specific strategies failed, falling back to body content.")
    
    # Make a last attempt to remove all common non-content elements
    try:
        if soup.body:
            # Remove one more round of likely non-content elements
            for tag in soup.body.find_all(['header', 'footer', 'nav', 'aside', 'form']):
                tag.decompose()
            
            return clean_whitespace(soup.body.get_text(separator=' ', strip=True))
    except Exception as e:
        logger.debug(f"Error with fallback body extraction: {e}")
    
    # Last resort - get all text
    return clean_whitespace(soup.get_text(separator=' ', strip=True))

def extract_table_content(soup: BeautifulSoup) -> List[Dict]:
    """
    Extract data from tables in the content.
    Returns a list of dictionaries representing tables.
    """
    tables_data = []
    
    for table_idx, table in enumerate(soup.find_all('table')):
        try:
            rows = table.find_all('tr')
            if not rows:
                continue
                
            # Extract headers
            headers = []
            th_elements = rows[0].find_all('th')
            
            if th_elements:
                # Use th elements if available
                headers = [clean_whitespace(th.get_text()) for th in th_elements]
            else:
                # Use first row td elements as headers if no th elements
                headers = [clean_whitespace(td.get_text()) for td in rows[0].find_all('td')]
            
            # Skip tables with no headers
            if not headers:
                continue
                
            # Extract data rows
            table_data = []
            for row in rows[1:]:  # Skip header row
                cells = row.find_all(['td', 'th'])
                if len(cells) == 0:
                    continue
                    
                # Create row data dictionary
                row_data = {}
                for idx, cell in enumerate(cells):
                    if idx < len(headers):
                        header = headers[idx] or f"Column{idx+1}"
                        row_data[header] = clean_whitespace(cell.get_text())
                    else:
                        row_data[f"Column{idx+1}"] = clean_whitespace(cell.get_text())
                
                if row_data:
                    table_data.append(row_data)
            
            if table_data:
                # Get table caption if available
                caption = table.find('caption')
                caption_text = clean_whitespace(caption.get_text()) if caption else f"Table {table_idx+1}"
                
                tables_data.append({
                    "caption": caption_text,
                    "headers": headers,
                    "data": table_data
                })
                
        except Exception as e:
            logger.warning(f"Error extracting table {table_idx}: {e}")
            continue
    
    return tables_data

def extract_lists(soup: BeautifulSoup) -> List[Dict]:
    """
    Extract content from ordered and unordered lists.
    Returns a list of dictionaries representing lists.
    """
    lists_data = []
    
    for list_idx, list_elem in enumerate(soup.find_all(['ul', 'ol'])):
        try:
            # Skip if the list is nested inside another list
            if list_elem.parent.name in ['li', 'ul', 'ol']:
                continue
                
            list_type = list_elem.name  # 'ul' or 'ol'
            list_items = []
            
            for li in list_elem.find_all('li', recursive=False):
                item_text = clean_whitespace(li.get_text())
                if item_text:
                    list_items.append(item_text)
            
            if list_items:
                # Try to find a title for the list (often in a preceding h2, h3, etc.)
                title = None
                prev_elem = list_elem.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'strong'])
                if prev_elem and prev_elem.name != 'p' or (prev_elem.name == 'p' and len(prev_elem.get_text()) < 100):
                    title = clean_whitespace(prev_elem.get_text())
                
                lists_data.append({
                    "type": list_type,
                    "title": title or f"List {list_idx+1}",
                    "items": list_items
                })
        
        except Exception as e:
            logger.warning(f"Error extracting list {list_idx}: {e}")
            continue
    
    return lists_data

def parse_html(html_content: str) -> Optional[Dict[str, str]]:
    """
    Parses HTML content to extract the title and main text.
    Optimized for Minnesota DHS website structure.

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

        # Extract Title (try multiple strategies)
        page_title = "No Title Found"
        
        # Try specific DHS title elements first
        title_selectors = [
            'h1.page-title', '.pageTitle', '#pageTitle',
            'h1.title', 'h1.main-title', 'h1:first-of-type',
            'h1.dhs-title', '.dhs-page-title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.string:
                page_title = clean_whitespace(title_elem.get_text())
                break
        
        # Fall back to the <title> tag if no h1 found
        if page_title == "No Title Found":
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                page_title = clean_whitespace(title_tag.string)
        
        logger.debug(f"Extracted Title: {page_title}")

        # Extract Main Text
        extracted_text = extract_main_content(soup)
        
        # Extract structured content
        tables = extract_table_content(soup)
        lists = extract_lists(soup)
        
        if not extracted_text and not tables and not lists:
            logger.warning("Could not extract meaningful content from the HTML.")
            return None

        # Log success
        content_length = len(extracted_text)
        logger.info(f"Successfully parsed HTML. Title: '{page_title}', Text length: {content_length}, Tables: {len(tables)}, Lists: {len(lists)}")
        
        result = {
            "title": page_title,
            "text": extracted_text
        }
        
        # Add structured content if available
        if tables:
            result["tables"] = tables
        if lists:
            result["lists"] = lists
            
        return result

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
    
    sample_dhs_like = """
    <html><head><title>Minnesota DHS Page</title></head>
    <body>
        <div id="globalHeader">Header Content</div>
        <div id="leftCol">
            <div class="sidenav">Navigation</div>
        </div>
        <div id="mainContent">
            <h1 class="page-title">EIDBI Services</h1>
            <p>The Early Intensive Developmental and Behavioral Intervention (EIDBI) program provides services for people under age 21 with autism spectrum disorder or related conditions.</p>
            <h2>Eligibility Requirements</h2>
            <ul>
                <li>Be under 21 years of age</li>
                <li>Have a diagnosis of ASD or related condition</li>
                <li>Have a comprehensive evaluation</li>
            </ul>
            <table>
                <caption>Service Types</caption>
                <tr><th>Service</th><th>Description</th></tr>
                <tr><td>CMDE</td><td>Comprehensive evaluation</td></tr>
                <tr><td>Individual Treatment</td><td>One-on-one therapy</td></tr>
            </table>
        </div>
        <div id="globalFooter">Footer Content</div>
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
    
    print("\n--- Test Case 4: DHS-like structure ---")
    result4 = parse_html(sample_dhs_like)
    print(result4)

    print("\n--- Test Case 5: Empty Input ---")
    result5 = parse_html(empty_html)
    print(result5)

    print("\n--- Test Case 6: Invalid HTML ---")
    result6 = parse_html(invalid_html) # BeautifulSoup might still parse some of it
    print(result6) 