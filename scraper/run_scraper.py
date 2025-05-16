#!/usr/bin/env python
"""
EIDBI Scraper Runner Script
---------------------------
This script runs the enhanced scraper to collect data from the Minnesota DHS website
about EIDBI (Early Intensive Developmental and Behavioral Intervention) services.
"""

import argparse
import logging
from typing import List
import sys
import os

# Add the current directory to the path to find the scraper module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from scraper import scrape_and_process
except ImportError as e:
    print(f"Error importing scraper module: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"scraper_run_{os.path.basename(__file__).split('.')[0]}.log")
    ]
)
logger = logging.getLogger(__name__)

# Initial seed URLs for EIDBI content on the Minnesota DHS website
EIDBI_SEED_URLS = [
    "https://mn.gov/dhs/people-we-serve/children-and-families/health-care/autism/eidbi/",
    "https://mn.gov/dhs/partners-and-providers/policies-procedures/childrens-mental-health/eidbi/",
    "https://mn.gov/dhs/people-we-serve/people-with-disabilities/services/home-community/programs-and-services/eidbi-services.jsp",
    "https://mn.gov/dhs/partners-and-providers/news-initiatives-reports-workgroups/long-term-services-and-supports/eidbi-workgroup/",
]

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments for the scraper."""
    parser = argparse.ArgumentParser(description="Run the EIDBI Web Scraper")
    
    parser.add_argument(
        "--urls", 
        nargs="+", 
        help="Specific URLs to scrape (space-separated). If not provided, default EIDBI seed URLs will be used."
    )
    
    parser.add_argument(
        "--crawl", 
        action="store_true",
        help="Enable crawling from seed URLs to find more EIDBI content."
    )
    
    parser.add_argument(
        "--depth", 
        type=int, 
        default=2,
        help="Maximum link depth for crawling (default: 2)."
    )
    
    parser.add_argument(
        "--max-pages", 
        type=int, 
        default=50,
        help="Maximum number of pages to collect during crawling (default: 50)."
    )
    
    parser.add_argument(
        "--upload-gcs", 
        action="store_true",
        help="Upload results to Google Cloud Storage."
    )
    
    parser.add_argument(
        "--no-save-local", 
        action="store_true",
        help="Disable saving results locally."
    )
    
    parser.add_argument(
        "--url-file",
        help="Path to a text file containing URLs to scrape (one URL per line)."
    )
    
    return parser.parse_args()

def read_urls_from_file(file_path: str) -> List[str]:
    """Read URLs from a text file, one URL per line."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        logger.info(f"Read {len(urls)} URLs from {file_path}")
        return urls
    except Exception as e:
        logger.error(f"Error reading URLs from {file_path}: {e}")
        return []

def main():
    """Main function to run the scraper with command line arguments."""
    args = parse_arguments()
    
    # Determine which URLs to scrape
    urls_to_scrape = []
    
    if args.url_file:
        urls_to_scrape = read_urls_from_file(args.url_file)
    elif args.urls:
        urls_to_scrape = args.urls
    else:
        # Use default seed URLs
        urls_to_scrape = EIDBI_SEED_URLS
    
    if not urls_to_scrape:
        logger.error("No URLs to scrape. Please provide URLs using --urls or --url-file.")
        sys.exit(1)
    
    logger.info(f"Starting EIDBI scraper with {len(urls_to_scrape)} URLs")
    logger.info(f"Crawling: {'Enabled' if args.crawl else 'Disabled'}")
    
    if args.crawl:
        logger.info(f"Crawl depth: {args.depth}, Max pages: {args.max_pages}")
    
    # Run the scraper
    try:
        scraped_data = scrape_and_process(
            urls_to_scrape=urls_to_scrape,
            upload_to_gcs=args.upload_gcs,
            save_local=not args.no_save_local,
            crawl_first=args.crawl,
            crawl_depth=args.depth,
            max_pages=args.max_pages
        )
        
        # Report results
        if scraped_data:
            logger.info(f"Scraper completed successfully. Collected {len(scraped_data)} chunks of data.")
        else:
            logger.warning("Scraper completed, but no data was collected.")
    
    except Exception as e:
        logger.error(f"Error running scraper: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("Scraper run completed")

if __name__ == "__main__":
    main() 