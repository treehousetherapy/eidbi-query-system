# backend/app/services/data_source_integration.py

import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import json
import time
from urllib.parse import urljoin, urlparse
import re

logger = logging.getLogger(__name__)

class DataSourceType(Enum):
    """Types of data sources for integration."""
    DHS_WEBSITE = "dhs_website"
    DHS_API = "dhs_api"
    POLICY_MANUAL = "policy_manual"
    FAQ_DATABASE = "faq_database"
    PROVIDER_DIRECTORY = "provider_directory"
    FORMS_DOCUMENTS = "forms_documents"
    NEWS_UPDATES = "news_updates"

@dataclass
class DataSource:
    """Represents a data source configuration."""
    name: str
    source_type: DataSourceType
    base_url: str
    endpoints: List[str]
    update_frequency: int  # hours
    last_updated: Optional[float] = None
    active: bool = True
    priority: int = 1  # 1=highest, 5=lowest
    metadata: Optional[Dict[str, Any]] = None

class DataSourceIntegrationService:
    """Service for integrating multiple DHS data sources."""
    
    def __init__(self):
        self.data_sources = self._initialize_data_sources()
        self.content_cache: Dict[str, Dict[str, Any]] = {}
        self.update_queue: List[str] = []
        
    def _initialize_data_sources(self) -> Dict[str, DataSource]:
        """Initialize available data sources."""
        sources = {
            "dhs_main": DataSource(
                name="DHS Main Website",
                source_type=DataSourceType.DHS_WEBSITE,
                base_url="https://www.dhs.state.mn.us",
                endpoints=[
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=DHS-293662",  # Main EIDBI
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs-305956",  # Policy Manual
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs-292229",  # Provider Info
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=DHS-293657",  # Service Options
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs-292657",  # Covered Services
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_155989",  # FAQ
                ],
                update_frequency=24,  # Daily
                priority=1
            ),
            
            "dhs_autism_resources": DataSource(
                name="DHS Autism Resources",
                source_type=DataSourceType.DHS_WEBSITE,
                base_url="https://www.dhs.state.mn.us",
                endpoints=[
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_166648",  # Autism Services
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_166649",  # Autism Support
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_166650",  # Family Resources
                ],
                update_frequency=48,  # Every 2 days
                priority=2
            ),
            
            "dhs_disability_services": DataSource(
                name="DHS Disability Services",
                source_type=DataSourceType.DHS_WEBSITE,
                base_url="https://www.dhs.state.mn.us",
                endpoints=[
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_140344",  # Disability Services
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_140345",  # Children's Services
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_140346",  # Early Intervention
                ],
                update_frequency=72,  # Every 3 days
                priority=3
            ),
            
            "dhs_medical_assistance": DataSource(
                name="DHS Medical Assistance",
                source_type=DataSourceType.DHS_WEBSITE,
                base_url="https://www.dhs.state.mn.us",
                endpoints=[
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_140347",  # MA Coverage
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_140348",  # MA Eligibility
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_140349",  # MA Services
                ],
                update_frequency=168,  # Weekly
                priority=4
            ),
            
            "dhs_provider_directory": DataSource(
                name="DHS Provider Directory",
                source_type=DataSourceType.PROVIDER_DIRECTORY,
                base_url="https://www.dhs.state.mn.us",
                endpoints=[
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_140350",  # Provider Search
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_140351",  # EIDBI Providers
                ],
                update_frequency=168,  # Weekly
                priority=3
            ),
            
            "dhs_forms": DataSource(
                name="DHS Forms and Documents",
                source_type=DataSourceType.FORMS_DOCUMENTS,
                base_url="https://www.dhs.state.mn.us",
                endpoints=[
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_140352",  # EIDBI Forms
                    "/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_140353",  # Application Forms
                ],
                update_frequency=336,  # Bi-weekly
                priority=4
            )
        }
        
        logger.info(f"Initialized {len(sources)} data sources")
        return sources
    
    async def fetch_content_from_source(
        self, 
        source: DataSource, 
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Fetch content from a single data source."""
        content_items = []
        errors = []
        
        for endpoint in source.endpoints:
            try:
                url = urljoin(source.base_url, endpoint)
                logger.info(f"Fetching content from {url}")
                
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        
                        # Parse content (you would integrate with your existing parsing logic)
                        parsed_content = await self._parse_html_content(html_content, url)
                        if parsed_content:
                            content_items.append(parsed_content)
                            logger.info(f"Successfully fetched content from {url}")
                    else:
                        error_msg = f"HTTP {response.status} for {url}"
                        errors.append(error_msg)
                        logger.warning(error_msg)
                        
            except Exception as e:
                error_msg = f"Error fetching {endpoint}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                
            # Rate limiting
            await asyncio.sleep(2)
        
        return {
            "source_name": source.name,
            "source_type": source.source_type.value,
            "content_items": content_items,
            "errors": errors,
            "fetch_timestamp": time.time()
        }
    
    async def _parse_html_content(self, html_content: str, url: str) -> Optional[Dict[str, Any]]:
        """Parse HTML content and extract relevant information."""
        try:
            # This would integrate with your existing parsing logic
            # For now, we'll do basic extraction
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            title = title_tag.get_text().strip() if title_tag else "No Title"
            
            # Extract main content
            # Look for common content containers
            content_selectors = [
                'main', '.main-content', '#main-content', 
                '.content', '#content', 'article', '.article'
            ]
            
            content_text = ""
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    content_text = content_element.get_text(separator=' ', strip=True)
                    break
            
            # If no specific content area found, get body text
            if not content_text:
                body = soup.find('body')
                if body:
                    content_text = body.get_text(separator=' ', strip=True)
            
            # Clean up content
            content_text = re.sub(r'\s+', ' ', content_text).strip()
            
            if len(content_text) < 100:  # Skip very short content
                return None
                
            return {
                "url": url,
                "title": title,
                "content": content_text,
                "content_length": len(content_text),
                "extraction_timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error parsing content from {url}: {e}")
            return None
    
    async def update_all_sources(self, force_update: bool = False) -> Dict[str, Any]:
        """Update content from all active data sources."""
        logger.info("Starting update of all data sources")
        
        sources_to_update = []
        current_time = time.time()
        
        for source_id, source in self.data_sources.items():
            if not source.active:
                continue
                
            # Check if update is needed
            if force_update or self._needs_update(source, current_time):
                sources_to_update.append((source_id, source))
        
        if not sources_to_update:
            logger.info("No sources need updating")
            return {"updated_sources": 0, "total_content_items": 0}
        
        logger.info(f"Updating {len(sources_to_update)} sources")
        
        # Fetch content from all sources concurrently
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.fetch_content_from_source(source, session)
                for _, source in sources_to_update
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        total_content_items = 0
        updated_sources = 0
        errors = []
        
        for i, result in enumerate(results):
            source_id, source = sources_to_update[i]
            
            if isinstance(result, Exception):
                error_msg = f"Failed to update {source.name}: {str(result)}"
                errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            # Cache the content
            self.content_cache[source_id] = result
            
            # Update last_updated timestamp
            source.last_updated = current_time
            
            content_count = len(result.get("content_items", []))
            total_content_items += content_count
            updated_sources += 1
            
            logger.info(f"Updated {source.name}: {content_count} content items")
        
        summary = {
            "updated_sources": updated_sources,
            "total_content_items": total_content_items,
            "errors": errors,
            "update_timestamp": current_time
        }
        
        logger.info(f"Update complete: {updated_sources} sources, {total_content_items} content items")
        return summary
    
    def _needs_update(self, source: DataSource, current_time: float) -> bool:
        """Check if a source needs updating based on its update frequency."""
        if source.last_updated is None:
            return True
            
        hours_since_update = (current_time - source.last_updated) / 3600
        return hours_since_update >= source.update_frequency
    
    def get_content_for_query(self, query: str, max_sources: int = 3) -> List[Dict[str, Any]]:
        """Get relevant content from cached sources for a query."""
        relevant_content = []
        
        # Sort sources by priority
        sorted_sources = sorted(
            self.data_sources.items(),
            key=lambda x: x[1].priority
        )
        
        sources_used = 0
        for source_id, source in sorted_sources:
            if sources_used >= max_sources:
                break
                
            if source_id not in self.content_cache:
                continue
                
            cached_data = self.content_cache[source_id]
            content_items = cached_data.get("content_items", [])
            
            # Find relevant content items
            for item in content_items:
                if self._is_content_relevant(item, query):
                    relevant_content.append({
                        **item,
                        "source_name": source.name,
                        "source_type": source.source_type.value,
                        "source_priority": source.priority
                    })
            
            if content_items:  # Count source as used if it had any content
                sources_used += 1
        
        # Sort by relevance score (if implemented) or by source priority
        relevant_content.sort(key=lambda x: x.get("source_priority", 5))
        
        return relevant_content[:10]  # Limit to top 10 items
    
    def _is_content_relevant(self, content_item: Dict[str, Any], query: str) -> bool:
        """Check if a content item is relevant to the query."""
        query_lower = query.lower()
        content_text = content_item.get("content", "").lower()
        title = content_item.get("title", "").lower()
        
        # Simple keyword matching (could be enhanced with semantic similarity)
        query_words = set(query_lower.split())
        content_words = set(content_text.split())
        title_words = set(title.split())
        
        # Check for keyword overlap
        title_overlap = len(query_words.intersection(title_words))
        content_overlap = len(query_words.intersection(content_words))
        
        # Consider relevant if there's significant overlap
        return title_overlap >= 1 or content_overlap >= 2
    
    def get_source_status(self) -> Dict[str, Any]:
        """Get status information for all data sources."""
        status = {
            "total_sources": len(self.data_sources),
            "active_sources": sum(1 for s in self.data_sources.values() if s.active),
            "cached_sources": len(self.content_cache),
            "sources": []
        }
        
        current_time = time.time()
        
        for source_id, source in self.data_sources.items():
            source_status = {
                "id": source_id,
                "name": source.name,
                "type": source.source_type.value,
                "active": source.active,
                "priority": source.priority,
                "update_frequency_hours": source.update_frequency,
                "last_updated": source.last_updated,
                "needs_update": self._needs_update(source, current_time),
                "cached_content_items": 0
            }
            
            if source_id in self.content_cache:
                cached_data = self.content_cache[source_id]
                source_status["cached_content_items"] = len(cached_data.get("content_items", []))
                source_status["cache_timestamp"] = cached_data.get("fetch_timestamp")
            
            status["sources"].append(source_status)
        
        return status
    
    def add_custom_source(
        self, 
        source_id: str, 
        name: str, 
        source_type: DataSourceType,
        base_url: str,
        endpoints: List[str],
        update_frequency: int = 168,
        priority: int = 5
    ) -> bool:
        """Add a custom data source."""
        try:
            if source_id in self.data_sources:
                logger.warning(f"Source {source_id} already exists")
                return False
            
            new_source = DataSource(
                name=name,
                source_type=source_type,
                base_url=base_url,
                endpoints=endpoints,
                update_frequency=update_frequency,
                priority=priority
            )
            
            self.data_sources[source_id] = new_source
            logger.info(f"Added custom data source: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding custom source: {e}")
            return False

# Global data source integration service instance
data_integration_service = DataSourceIntegrationService() 