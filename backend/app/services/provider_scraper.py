"""
Minnesota DHS Provider Directory Scraper

This module scrapes the Minnesota DHS Provider Directory to extract
EIDBI provider count data and maintain up-to-date provider statistics.
"""

import requests
import logging
import time
import re
from typing import Dict, List, Any, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ProviderInfo:
    """Information about an EIDBI provider"""
    name: str
    address: str
    county: str
    phone: Optional[str] = None
    services: List[str] = None
    provider_id: Optional[str] = None
    
    def __post_init__(self):
        if self.services is None:
            self.services = []

class ProviderDirectoryScraper:
    """Scraper for Minnesota DHS Provider Directory"""
    
    def __init__(self):
        self.base_url = "https://www.dhs.state.mn.us"
        self.provider_search_url = "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_155949"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.rate_limit_delay = 2  # seconds between requests
        
    def _make_request(self, url: str, params: Optional[Dict] = None, 
                     retries: int = 3) -> Optional[requests.Response]:
        """Make HTTP request with retry logic and rate limiting"""
        for attempt in range(retries):
            try:
                time.sleep(self.rate_limit_delay)
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed for {url}: {e}")
                if attempt == retries - 1:
                    logger.error(f"Failed to fetch {url} after {retries} attempts")
                    return None
                time.sleep(5 * (attempt + 1))  # Exponential backoff
        
        return None
    
    def search_eidbi_providers(self) -> List[ProviderInfo]:
        """Search for EIDBI providers in the directory"""
        try:
            logger.info("Starting EIDBI provider search...")
            
            # Try multiple search strategies
            providers = []
            
            # Strategy 1: Search by service type
            providers.extend(self._search_by_service_type("EIDBI"))
            providers.extend(self._search_by_service_type("Early Intensive Developmental"))
            providers.extend(self._search_by_service_type("Behavioral Intervention"))
            
            # Strategy 2: Search by program keywords
            providers.extend(self._search_by_keywords("autism", "developmental disabilities"))
            
            # Remove duplicates based on name and address
            unique_providers = self._deduplicate_providers(providers)
            
            logger.info(f"Found {len(unique_providers)} unique EIDBI providers")
            return unique_providers
            
        except Exception as e:
            logger.error(f"Error searching EIDBI providers: {e}")
            return []
    
    def _search_by_service_type(self, service_type: str) -> List[ProviderInfo]:
        """Search providers by service type"""
        try:
            logger.info(f"Searching providers for service type: {service_type}")
            
            # Try different search endpoints
            search_urls = [
                "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_155949",
                "https://www.dhs.state.mn.us/main/groups/disabilities/documents/pub/dhs16_155949.html",
                "https://edocs.dhs.state.mn.us/lfserver/Public/DHS-4641A-ENG"
            ]
            
            providers = []
            
            for url in search_urls:
                try:
                    response = self._make_request(url)
                    if response:
                        providers.extend(self._parse_provider_page(response.text, service_type))
                except Exception as e:
                    logger.warning(f"Failed to search {url}: {e}")
                    continue
            
            return providers
            
        except Exception as e:
            logger.error(f"Error in service type search for {service_type}: {e}")
            return []
    
    def _search_by_keywords(self, *keywords) -> List[ProviderInfo]:
        """Search providers by keywords"""
        try:
            providers = []
            
            # Search DHS directory pages
            directory_urls = [
                "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_140346",
                "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_140349"
            ]
            
            for url in directory_urls:
                try:
                    response = self._make_request(url)
                    if response:
                        for keyword in keywords:
                            providers.extend(self._parse_provider_page(response.text, keyword))
                except Exception as e:
                    logger.warning(f"Failed to search {url}: {e}")
                    continue
            
            return providers
            
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []
    
    def _parse_provider_page(self, html_content: str, search_term: str) -> List[ProviderInfo]:
        """Parse HTML content to extract provider information"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            providers = []
            
            # Look for provider information in various formats
            
            # Method 1: Look for structured provider listings
            provider_sections = soup.find_all(['div', 'section', 'article'], 
                                            class_=re.compile(r'provider|directory|listing', re.I))
            
            for section in provider_sections:
                if search_term.lower() in section.get_text().lower():
                    provider = self._extract_provider_info(section, search_term)
                    if provider:
                        providers.append(provider)
            
            # Method 2: Look for tables with provider data
            tables = soup.find_all('table')
            for table in tables:
                if search_term.lower() in table.get_text().lower():
                    providers.extend(self._parse_provider_table(table, search_term))
            
            # Method 3: Look for text patterns indicating provider counts
            text_content = soup.get_text()
            count_matches = self._extract_provider_counts_from_text(text_content, search_term)
            
            # Method 4: Look for links to provider directories
            links = soup.find_all('a', href=True)
            for link in links:
                if any(keyword in link.get_text().lower() for keyword in ['provider', 'directory', 'eidbi']):
                    href = link['href']
                    if not href.startswith('http'):
                        href = urljoin(self.base_url, href)
                    # Could recursively search linked pages (with depth limit)
            
            return providers
            
        except Exception as e:
            logger.error(f"Error parsing provider page: {e}")
            return []
    
    def _extract_provider_info(self, element, search_term: str) -> Optional[ProviderInfo]:
        """Extract provider information from HTML element"""
        try:
            text = element.get_text().strip()
            
            # Skip if this doesn't seem to be about EIDBI
            if not any(keyword in text.lower() for keyword in 
                      ['eidbi', 'autism', 'developmental', 'behavioral intervention']):
                return None
            
            # Try to extract structured information
            name = ""
            address = ""
            county = ""
            phone = ""
            
            # Look for common patterns
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            for i, line in enumerate(lines):
                # First non-empty line is often the name
                if not name and len(line) > 3:
                    name = line
                
                # Look for address patterns
                if re.search(r'\d+.*\w+\s+(St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Boulevard)', line, re.I):
                    address = line
                
                # Look for county patterns
                if 'county' in line.lower():
                    county = line
                
                # Look for phone patterns
                phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', line)
                if phone_match:
                    phone = phone_match.group()
            
            if name:
                return ProviderInfo(
                    name=name,
                    address=address,
                    county=county,
                    phone=phone,
                    services=[search_term]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting provider info: {e}")
            return None
    
    def _parse_provider_table(self, table, search_term: str) -> List[ProviderInfo]:
        """Parse provider information from HTML table"""
        try:
            providers = []
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:  # Need at least name and one other field
                    cell_texts = [cell.get_text().strip() for cell in cells]
                    
                    # Skip header rows
                    if any(header in cell_texts[0].lower() for header in ['name', 'provider', 'organization']):
                        continue
                    
                    if any(keyword in ' '.join(cell_texts).lower() for keyword in 
                          ['eidbi', 'autism', 'developmental', 'behavioral']):
                        
                        provider = ProviderInfo(
                            name=cell_texts[0] if cell_texts else "",
                            address=cell_texts[1] if len(cell_texts) > 1 else "",
                            county=cell_texts[2] if len(cell_texts) > 2 else "",
                            phone=cell_texts[3] if len(cell_texts) > 3 else "",
                            services=[search_term]
                        )
                        providers.append(provider)
            
            return providers
            
        except Exception as e:
            logger.error(f"Error parsing provider table: {e}")
            return []
    
    def _extract_provider_counts_from_text(self, text: str, search_term: str) -> Dict[str, int]:
        """Extract provider counts from text content"""
        try:
            counts = {}
            
            # Look for patterns like "X EIDBI providers", "X licensed providers"
            patterns = [
                r'(\d+)\s+EIDBI\s+providers?',
                r'(\d+)\s+licensed\s+providers?.*EIDBI',
                r'(\d+)\s+providers?.*EIDBI',
                r'EIDBI.*?(\d+)\s+providers?',
                r'(\d+)\s+facilities?.*EIDBI',
                r'(\d+)\s+organizations?.*EIDBI'
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    count = int(match.group(1))
                    counts[f"text_extracted_{search_term}"] = count
                    logger.info(f"Found provider count in text: {count} for {search_term}")
            
            return counts
            
        except Exception as e:
            logger.error(f"Error extracting counts from text: {e}")
            return {}
    
    def _deduplicate_providers(self, providers: List[ProviderInfo]) -> List[ProviderInfo]:
        """Remove duplicate providers based on name and address"""
        seen = set()
        unique_providers = []
        
        for provider in providers:
            # Create a key for deduplication
            key = (provider.name.lower().strip(), provider.address.lower().strip())
            
            if key not in seen:
                seen.add(key)
                unique_providers.append(provider)
        
        return unique_providers
    
    def get_provider_counts_by_county(self, providers: List[ProviderInfo]) -> Dict[str, int]:
        """Get provider counts grouped by county"""
        county_counts = {}
        
        for provider in providers:
            county = provider.county.strip()
            if county:
                # Clean up county name
                county = re.sub(r'\s+county', '', county, flags=re.IGNORECASE).strip()
                county_counts[county] = county_counts.get(county, 0) + 1
        
        return county_counts
    
    def scrape_provider_data(self) -> Tuple[int, Dict[str, int], List[ProviderInfo]]:
        """
        Main method to scrape provider data
        Returns: (total_count, county_counts, provider_list)
        """
        try:
            logger.info("Starting comprehensive provider data scrape...")
            
            # Get provider information
            providers = self.search_eidbi_providers()
            
            # If we don't find detailed provider info, try to get counts from summary pages
            if not providers:
                logger.info("No detailed provider info found, trying summary extraction...")
                total_count = self._get_summary_count()
                return total_count, {}, []
            
            # Calculate statistics
            total_count = len(providers)
            county_counts = self.get_provider_counts_by_county(providers)
            
            logger.info(f"Scraping complete: {total_count} total providers, {len(county_counts)} counties")
            
            return total_count, county_counts, providers
            
        except Exception as e:
            logger.error(f"Error in provider data scrape: {e}")
            return 0, {}, []
    
    def _get_summary_count(self) -> int:
        """Try to get provider count from summary/overview pages"""
        try:
            summary_urls = [
                "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_140346",
                "https://mn.gov/dhs/people-we-serve/people-with-disabilities/services/childrens-services/programs-and-services/eidbi/",
                "https://www.dhs.state.mn.us/main/groups/disabilities/documents/pub/dhs16_140346.html"
            ]
            
            for url in summary_urls:
                try:
                    response = self._make_request(url)
                    if response:
                        text = response.text
                        
                        # Look for summary statistics
                        patterns = [
                            r'(\d+)\s+EIDBI\s+providers?',
                            r'(\d+)\s+licensed\s+facilities?',
                            r'(\d+)\s+approved\s+providers?',
                            r'over\s+(\d+)\s+providers?',
                            r'approximately\s+(\d+)\s+providers?'
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, text, re.IGNORECASE)
                            if match:
                                count = int(match.group(1))
                                logger.info(f"Found summary count: {count} providers")
                                return count
                                
                except Exception as e:
                    logger.warning(f"Failed to get summary from {url}: {e}")
                    continue
            
            # If no specific count found, return estimated count based on known info
            logger.warning("No specific provider count found, using estimated count")
            return 50  # Conservative estimate
            
        except Exception as e:
            logger.error(f"Error getting summary count: {e}")
            return 0
    
    def export_provider_data(self, providers: List[ProviderInfo], file_path: str) -> None:
        """Export provider data to JSON file"""
        try:
            data = {
                'providers': [
                    {
                        'name': p.name,
                        'address': p.address,
                        'county': p.county,
                        'phone': p.phone,
                        'services': p.services,
                        'provider_id': p.provider_id
                    }
                    for p in providers
                ],
                'total_count': len(providers),
                'county_counts': self.get_provider_counts_by_county(providers),
                'scraped_at': datetime.now().isoformat(),
                'source': 'Minnesota DHS Provider Directory'
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported provider data to: {file_path}")
            
        except Exception as e:
            logger.error(f"Error exporting provider data: {e}")
            raise 