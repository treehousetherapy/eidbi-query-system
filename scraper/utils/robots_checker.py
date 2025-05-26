"""
Robots.txt Compliance Checker for Enhanced EIDBI Scraper

This module provides utilities for checking robots.txt compliance
with caching, error handling, and proper user-agent support.

Features:
- Robots.txt parsing and caching
- User-agent specific checks  
- Crawl delay extraction
- Sitemap discovery
- Error handling for inaccessible robots.txt

Author: Enhanced EIDBI Scraper
"""

import logging
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from typing import Dict, Optional, List, Tuple
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RobotsChecker:
    """
    Enhanced robots.txt checker with caching and comprehensive compliance checking
    """
    
    def __init__(self, user_agent: str = "*", cache_duration_hours: int = 24):
        """
        Initialize the robots checker
        
        Args:
            user_agent: User agent string to use for robots.txt checks
            cache_duration_hours: How long to cache robots.txt files (in hours)
        """
        self.user_agent = user_agent
        self.cache_duration = timedelta(hours=cache_duration_hours)
        
        # Cache for robots.txt parsers
        self.robots_cache: Dict[str, Dict] = {}
        
        # Session for making requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/plain',
            'Cache-Control': 'no-cache'
        })
        
        logger.info(f"RobotsChecker initialized with user-agent: {user_agent}")
    
    def _get_robots_url(self, url: str) -> str:
        """
        Get the robots.txt URL for a given URL
        
        Args:
            url: URL to get robots.txt for
            
        Returns:
            robots.txt URL
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    
    def _get_domain_key(self, url: str) -> str:
        """
        Get cache key for a domain
        
        Args:
            url: URL to get domain key for
            
        Returns:
            Domain cache key
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """
        Check if cache entry is still valid
        
        Args:
            cache_entry: Cache entry to check
            
        Returns:
            True if cache is valid
        """
        if 'timestamp' not in cache_entry:
            return False
        
        cache_time = cache_entry['timestamp']
        return datetime.now() - cache_time < self.cache_duration
    
    def _fetch_robots_txt(self, robots_url: str) -> Optional[str]:
        """
        Fetch robots.txt content from URL
        
        Args:
            robots_url: URL to fetch robots.txt from
            
        Returns:
            robots.txt content or None if failed
        """
        try:
            logger.debug(f"Fetching robots.txt from {robots_url}")
            response = self.session.get(robots_url, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                logger.debug(f"Successfully fetched robots.txt from {robots_url} ({len(content)} chars)")
                return content
            elif response.status_code == 404:
                logger.debug(f"No robots.txt found at {robots_url} (404)")
                return ""  # Empty robots.txt means everything is allowed
            else:
                logger.warning(f"Unexpected status {response.status_code} for robots.txt at {robots_url}")
                return None
                
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch robots.txt from {robots_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching robots.txt from {robots_url}: {e}")
            return None
    
    def _parse_robots_txt(self, content: str, robots_url: str) -> Dict:
        """
        Parse robots.txt content and extract relevant information
        
        Args:
            content: robots.txt content
            robots_url: URL where robots.txt was fetched from
            
        Returns:
            Dictionary with parsed robots.txt information
        """
        result = {
            'parser': None,
            'crawl_delay': None,
            'sitemaps': [],
            'user_agents': [],
            'disallowed_paths': [],
            'allowed_paths': [],
            'parsing_errors': []
        }
        
        try:
            # Create and configure parser
            rp = RobotFileParser()
            rp.set_url(robots_url)
            
            # Parse content
            rp.read()
            result['parser'] = rp
            
            # Extract additional information by parsing manually
            lines = content.split('\n')
            current_user_agent = None
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    if ':' in line:
                        directive, value = line.split(':', 1)
                        directive = directive.strip().lower()
                        value = value.strip()
                        
                        if directive == 'user-agent':
                            current_user_agent = value
                            if value not in result['user_agents']:
                                result['user_agents'].append(value)
                        
                        elif directive == 'crawl-delay':
                            try:
                                delay = float(value)
                                # Only set crawl delay if it applies to our user agent
                                if (current_user_agent == '*' or 
                                    current_user_agent == self.user_agent or
                                    current_user_agent is None):
                                    result['crawl_delay'] = delay
                            except ValueError:
                                result['parsing_errors'].append(f"Line {line_num}: Invalid crawl-delay value: {value}")
                        
                        elif directive == 'disallow':
                            if value and (current_user_agent == '*' or 
                                        current_user_agent == self.user_agent):
                                result['disallowed_paths'].append(value)
                        
                        elif directive == 'allow':
                            if value and (current_user_agent == '*' or 
                                        current_user_agent == self.user_agent):
                                result['allowed_paths'].append(value)
                        
                        elif directive == 'sitemap':
                            if value and value not in result['sitemaps']:
                                result['sitemaps'].append(value)
                
                except Exception as e:
                    result['parsing_errors'].append(f"Line {line_num}: Error parsing '{line}': {e}")
            
            if result['parsing_errors']:
                logger.warning(f"Found {len(result['parsing_errors'])} parsing errors in {robots_url}")
                for error in result['parsing_errors']:
                    logger.debug(f"Robots.txt parsing error: {error}")
            
        except Exception as e:
            logger.error(f"Failed to parse robots.txt from {robots_url}: {e}")
            result['parsing_errors'].append(f"Parser initialization failed: {e}")
        
        return result
    
    def _get_robots_info(self, url: str) -> Dict:
        """
        Get robots.txt information for a URL, using cache when possible
        
        Args:
            url: URL to get robots.txt info for
            
        Returns:
            Dictionary with robots.txt information
        """
        domain_key = self._get_domain_key(url)
        
        # Check cache first
        if domain_key in self.robots_cache:
            cache_entry = self.robots_cache[domain_key]
            if self._is_cache_valid(cache_entry):
                logger.debug(f"Using cached robots.txt for {domain_key}")
                return cache_entry
        
        # Fetch and parse robots.txt
        robots_url = self._get_robots_url(url)
        content = self._fetch_robots_txt(robots_url)
        
        if content is None:
            # If we can't fetch robots.txt, assume everything is allowed
            logger.info(f"Could not fetch robots.txt for {domain_key}, assuming crawling is allowed")
            robots_info = {
                'parser': None,
                'crawl_delay': None,
                'sitemaps': [],
                'user_agents': [],
                'disallowed_paths': [],
                'allowed_paths': [],
                'parsing_errors': [],
                'fetch_failed': True,
                'allow_all': True
            }
        else:
            robots_info = self._parse_robots_txt(content, robots_url)
            robots_info['fetch_failed'] = False
            robots_info['allow_all'] = False
        
        # Add timestamp and cache
        robots_info['timestamp'] = datetime.now()
        robots_info['robots_url'] = robots_url
        self.robots_cache[domain_key] = robots_info
        
        logger.info(f"Cached robots.txt info for {domain_key} (crawl-delay: {robots_info['crawl_delay']})")
        return robots_info
    
    def can_fetch(self, url: str, user_agent: str = None) -> bool:
        """
        Check if a URL can be fetched according to robots.txt
        
        Args:
            url: URL to check
            user_agent: User agent to check for (defaults to instance user_agent)
            
        Returns:
            True if URL can be fetched
        """
        if user_agent is None:
            user_agent = self.user_agent
        
        try:
            robots_info = self._get_robots_info(url)
            
            # If we couldn't fetch robots.txt, allow crawling
            if robots_info.get('fetch_failed', False) or robots_info.get('allow_all', False):
                return True
            
            # Use the parser if available
            parser = robots_info.get('parser')
            if parser:
                return parser.can_fetch(user_agent, url)
            
            # If no parser available, allow crawling
            return True
            
        except Exception as e:
            logger.error(f"Error checking robots.txt for {url}: {e}")
            # On error, allow crawling to be safe
            return True
    
    def get_crawl_delay(self, url: str) -> Optional[float]:
        """
        Get the crawl delay for a URL according to robots.txt
        
        Args:
            url: URL to get crawl delay for
            
        Returns:
            Crawl delay in seconds, or None if not specified
        """
        try:
            robots_info = self._get_robots_info(url)
            return robots_info.get('crawl_delay')
        except Exception as e:
            logger.error(f"Error getting crawl delay for {url}: {e}")
            return None
    
    def get_sitemaps(self, url: str) -> List[str]:
        """
        Get sitemap URLs for a domain
        
        Args:
            url: URL to get sitemaps for
            
        Returns:
            List of sitemap URLs
        """
        try:
            robots_info = self._get_robots_info(url)
            return robots_info.get('sitemaps', [])
        except Exception as e:
            logger.error(f"Error getting sitemaps for {url}: {e}")
            return []
    
    def get_robots_summary(self, url: str) -> Dict:
        """
        Get a comprehensive summary of robots.txt information for a URL
        
        Args:
            url: URL to get robots.txt summary for
            
        Returns:
            Dictionary with comprehensive robots.txt information
        """
        try:
            robots_info = self._get_robots_info(url)
            
            return {
                'domain': self._get_domain_key(url),
                'robots_url': robots_info.get('robots_url'),
                'can_fetch': self.can_fetch(url),
                'crawl_delay': robots_info.get('crawl_delay'),
                'sitemaps': robots_info.get('sitemaps', []),
                'user_agents': robots_info.get('user_agents', []),
                'disallowed_paths': robots_info.get('disallowed_paths', []),
                'allowed_paths': robots_info.get('allowed_paths', []),
                'fetch_failed': robots_info.get('fetch_failed', False),
                'parsing_errors': robots_info.get('parsing_errors', []),
                'cached_at': robots_info.get('timestamp')
            }
        except Exception as e:
            logger.error(f"Error getting robots.txt summary for {url}: {e}")
            return {
                'domain': self._get_domain_key(url),
                'error': str(e),
                'can_fetch': True  # Default to allowing on error
            }
    
    def clear_cache(self, domain: str = None):
        """
        Clear robots.txt cache
        
        Args:
            domain: Specific domain to clear, or None to clear all
        """
        if domain:
            if domain in self.robots_cache:
                del self.robots_cache[domain]
                logger.info(f"Cleared robots.txt cache for {domain}")
        else:
            self.robots_cache.clear()
            logger.info("Cleared all robots.txt cache")
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        total_entries = len(self.robots_cache)
        valid_entries = sum(1 for entry in self.robots_cache.values() 
                           if self._is_cache_valid(entry))
        
        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': total_entries - valid_entries,
            'cache_duration_hours': self.cache_duration.total_seconds() / 3600
        }

# Convenience functions for simple usage
def check_robots_permission(url: str, user_agent: str = "*") -> bool:
    """
    Simple function to check if a URL can be crawled
    
    Args:
        url: URL to check
        user_agent: User agent string
        
    Returns:
        True if crawling is allowed
    """
    checker = RobotsChecker(user_agent)
    return checker.can_fetch(url)

def get_crawl_delay(url: str, user_agent: str = "*") -> Optional[float]:
    """
    Simple function to get crawl delay for a URL
    
    Args:
        url: URL to check
        user_agent: User agent string
        
    Returns:
        Crawl delay in seconds or None
    """
    checker = RobotsChecker(user_agent)
    return checker.get_crawl_delay(url) 