"""
Structured Data Ingestion Service

This module handles ingestion of structured data snippets (JSON/CSV) containing
key facts like provider counts, with metadata tracking for source and updates.
"""

import json
import csv
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class StructuredDataEntry:
    """Represents a structured data entry with metadata"""
    id: str
    category: str  # e.g., "provider_count", "program_stats", "contact_info"
    key: str  # e.g., "total_eidbi_providers", "active_providers_by_county"
    value: Union[str, int, float, Dict, List]
    source: str  # e.g., "Minnesota DHS Provider Directory"
    source_url: Optional[str] = None
    last_updated: str = None
    data_type: str = "structured"
    confidence_level: str = "high"  # high, medium, low
    notes: Optional[str] = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()

class StructuredDataService:
    """Service for managing structured data ingestion and retrieval"""
    
    def __init__(self, data_dir: str = "data/structured"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.structured_data_file = self.data_dir / "structured_data.json"
        self.structured_data: Dict[str, StructuredDataEntry] = {}
        self.load_existing_data()
    
    def load_existing_data(self) -> None:
        """Load existing structured data from file"""
        try:
            if self.structured_data_file.exists():
                with open(self.structured_data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for entry_id, entry_data in data.items():
                        self.structured_data[entry_id] = StructuredDataEntry(**entry_data)
                logger.info(f"Loaded {len(self.structured_data)} structured data entries")
            else:
                logger.info("No existing structured data file found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading structured data: {e}")
            self.structured_data = {}
    
    def save_data(self) -> None:
        """Save structured data to file"""
        try:
            data_dict = {
                entry_id: asdict(entry) 
                for entry_id, entry in self.structured_data.items()
            }
            with open(self.structured_data_file, 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.structured_data)} structured data entries")
        except Exception as e:
            logger.error(f"Error saving structured data: {e}")
            raise
    
    def add_entry(self, entry: StructuredDataEntry) -> None:
        """Add or update a structured data entry"""
        try:
            entry.last_updated = datetime.now().isoformat()
            self.structured_data[entry.id] = entry
            self.save_data()
            logger.info(f"Added/updated structured data entry: {entry.id}")
        except Exception as e:
            logger.error(f"Error adding structured data entry {entry.id}: {e}")
            raise
    
    def ingest_json_file(self, file_path: str, source: str, source_url: Optional[str] = None) -> int:
        """Ingest structured data from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            count = 0
            if isinstance(data, dict):
                for key, value in data.items():
                    entry = StructuredDataEntry(
                        id=f"json_{source.lower().replace(' ', '_')}_{key}",
                        category="imported_data",
                        key=key,
                        value=value,
                        source=source,
                        source_url=source_url
                    )
                    self.add_entry(entry)
                    count += 1
            
            logger.info(f"Ingested {count} entries from JSON file: {file_path}")
            return count
            
        except Exception as e:
            logger.error(f"Error ingesting JSON file {file_path}: {e}")
            raise
    
    def ingest_csv_file(self, file_path: str, source: str, source_url: Optional[str] = None,
                       key_column: str = "key", value_column: str = "value", 
                       category_column: Optional[str] = None) -> int:
        """Ingest structured data from CSV file"""
        try:
            df = pd.read_csv(file_path)
            count = 0
            
            for _, row in df.iterrows():
                key = str(row[key_column])
                value = row[value_column]
                category = row[category_column] if category_column and category_column in df.columns else "imported_data"
                
                # Try to convert numeric values
                if isinstance(value, str) and value.isdigit():
                    value = int(value)
                elif isinstance(value, str):
                    try:
                        value = float(value)
                    except ValueError:
                        pass  # Keep as string
                
                entry = StructuredDataEntry(
                    id=f"csv_{source.lower().replace(' ', '_')}_{key.lower().replace(' ', '_')}",
                    category=category,
                    key=key,
                    value=value,
                    source=source,
                    source_url=source_url
                )
                self.add_entry(entry)
                count += 1
            
            logger.info(f"Ingested {count} entries from CSV file: {file_path}")
            return count
            
        except Exception as e:
            logger.error(f"Error ingesting CSV file {file_path}: {e}")
            raise
    
    def get_entries_by_category(self, category: str) -> List[StructuredDataEntry]:
        """Get all entries in a specific category"""
        return [entry for entry in self.structured_data.values() if entry.category == category]
    
    def get_entry_by_key(self, key: str) -> Optional[StructuredDataEntry]:
        """Get entry by key (first match)"""
        for entry in self.structured_data.values():
            if entry.key.lower() == key.lower():
                return entry
        return None
    
    def search_entries(self, query: str) -> List[StructuredDataEntry]:
        """Search entries by key, value, or source"""
        query_lower = query.lower()
        results = []
        
        for entry in self.structured_data.values():
            if (query_lower in entry.key.lower() or 
                query_lower in str(entry.value).lower() or 
                query_lower in entry.source.lower()):
                results.append(entry)
        
        return results
    
    def get_stale_entries(self, max_age_days: int = 30) -> List[StructuredDataEntry]:
        """Get entries that are older than max_age_days"""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        stale_entries = []
        
        for entry in self.structured_data.values():
            try:
                entry_date = datetime.fromisoformat(entry.last_updated.replace('Z', '+00:00'))
                if entry_date.replace(tzinfo=None) < cutoff_date:
                    stale_entries.append(entry)
            except (ValueError, AttributeError):
                # If we can't parse the date, consider it stale
                stale_entries.append(entry)
        
        return stale_entries
    
    def update_provider_count(self, total_count: int, by_county: Optional[Dict[str, int]] = None,
                            source: str = "Minnesota DHS Provider Directory", 
                            source_url: Optional[str] = None) -> None:
        """Update provider count data"""
        try:
            # Total provider count
            total_entry = StructuredDataEntry(
                id="eidbi_total_provider_count",
                category="provider_count",
                key="total_eidbi_providers",
                value=total_count,
                source=source,
                source_url=source_url,
                confidence_level="high",
                notes=f"Total number of EIDBI providers in Minnesota as of {datetime.now().strftime('%Y-%m-%d')}"
            )
            self.add_entry(total_entry)
            
            # County breakdown if provided
            if by_county:
                county_entry = StructuredDataEntry(
                    id="eidbi_providers_by_county",
                    category="provider_count",
                    key="eidbi_providers_by_county",
                    value=by_county,
                    source=source,
                    source_url=source_url,
                    confidence_level="high",
                    notes=f"EIDBI providers by county in Minnesota as of {datetime.now().strftime('%Y-%m-%d')}"
                )
                self.add_entry(county_entry)
            
            logger.info(f"Updated provider count data: {total_count} total providers")
            
        except Exception as e:
            logger.error(f"Error updating provider count: {e}")
            raise
    
    def get_provider_stats(self) -> Dict[str, Any]:
        """Get current provider statistics"""
        stats = {}
        
        # Get total provider count
        total_entry = self.get_entry_by_key("total_eidbi_providers")
        if total_entry:
            stats["total_providers"] = total_entry.value
            stats["total_providers_last_updated"] = total_entry.last_updated
            stats["total_providers_source"] = total_entry.source
        
        # Get county breakdown
        county_entry = self.get_entry_by_key("eidbi_providers_by_county")
        if county_entry:
            stats["providers_by_county"] = county_entry.value
            stats["county_data_last_updated"] = county_entry.last_updated
        
        return stats
    
    def to_vector_db_format(self) -> List[Dict[str, Any]]:
        """Convert structured data to format compatible with vector database"""
        vector_entries = []
        
        for entry in self.structured_data.values():
            # Create a text representation for embedding
            if isinstance(entry.value, (dict, list)):
                value_text = json.dumps(entry.value, indent=2)
            else:
                value_text = str(entry.value)
            
            content = f"Key Fact: {entry.key}\nValue: {value_text}\nSource: {entry.source}"
            if entry.notes:
                content += f"\nNotes: {entry.notes}"
            
            vector_entry = {
                "id": f"structured_{entry.id}",
                "content": content,
                "metadata": {
                    "type": "structured_data",
                    "category": entry.category,
                    "key": entry.key,
                    "source": entry.source,
                    "source_url": entry.source_url,
                    "last_updated": entry.last_updated,
                    "confidence_level": entry.confidence_level,
                    "data_type": entry.data_type
                },
                "source_metadata": {
                    "url": entry.source_url or entry.source,
                    "source_type": "structured_data",
                    "document_type": "fact"
                }
            }
            vector_entries.append(vector_entry)
        
        return vector_entries
    
    def export_to_json(self, file_path: str) -> None:
        """Export all structured data to JSON file"""
        try:
            data_dict = {
                entry_id: asdict(entry) 
                for entry_id, entry in self.structured_data.items()
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, indent=2, ensure_ascii=False)
            logger.info(f"Exported structured data to: {file_path}")
        except Exception as e:
            logger.error(f"Error exporting structured data: {e}")
            raise
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of structured data"""
        categories = {}
        sources = {}
        total_entries = len(self.structured_data)
        
        for entry in self.structured_data.values():
            categories[entry.category] = categories.get(entry.category, 0) + 1
            sources[entry.source] = sources.get(entry.source, 0) + 1
        
        return {
            "total_entries": total_entries,
            "categories": categories,
            "sources": sources,
            "last_updated": max([entry.last_updated for entry in self.structured_data.values()]) if self.structured_data else None
        } 