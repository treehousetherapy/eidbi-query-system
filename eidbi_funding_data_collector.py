#!/usr/bin/env python3
"""
EIDBI Funding and Budget Data Collector

Targeted collector for Minnesota EIDBI funding, budget, and financial data
to improve coverage from 60% to >80%.

Author: AI Assistant
Date: January 27, 2025
"""

import json
import asyncio
import aiohttp
import logging
from datetime import datetime
from pathlib import Path
import hashlib
import re
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EIDBIFundingDataCollector:
    """Specialized collector for EIDBI funding and budget information"""
    
    def __init__(self):
        self.funding_sources = [
            # Minnesota State Budget Documents
            {
                "name": "Minnesota Management and Budget - DHS Budget",
                "url": "https://mn.gov/mmb/budget/current-budget/",
                "type": "state_budget"
            },
            {
                "name": "Minnesota DHS Budget Documents",
                "url": "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_166421",
                "type": "dhs_budget"
            },
            {
                "name": "Minnesota Legislative Budget - EIDBI Appropriations",
                "url": "https://www.house.leg.state.mn.us/hrd/pubs/hhs_budget.pdf",
                "type": "legislative_budget"
            },
            {
                "name": "DHS Expenditure Reports",
                "url": "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs-284713",
                "type": "expenditure_report"
            },
            {
                "name": "Minnesota Medicaid Forecast",
                "url": "https://mn.gov/dhs/partners-and-providers/news-initiatives-reports-workgroups/forecasts-and-reports/",
                "type": "medicaid_forecast"
            },
            {
                "name": "DHS Financial Reports",
                "url": "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_141926",
                "type": "financial_reports"
            },
            {
                "name": "EIDBI Rate Setting Documentation",
                "url": "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_196849",
                "type": "rate_setting"
            },
            {
                "name": "Medical Assistance Expenditure Data",
                "url": "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_196638",
                "type": "ma_expenditure"
            },
            {
                "name": "Legislative Fiscal Analysis - EIDBI",
                "url": "https://www.senate.mn/departments/fiscalpol/tracking/2024/HHS_DHS_EIDBI.pdf",
                "type": "fiscal_analysis"
            },
            {
                "name": "DHS Provider Rates and Fees",
                "url": "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_166602",
                "type": "provider_rates"
            }
        ]
        
        self.collected_data = []
        self.session = None
        
    async def collect_all_funding_data(self) -> Dict[str, Any]:
        """Collect all funding and budget data"""
        logger.info("🎯 Starting targeted EIDBI funding data collection...")
        start_time = datetime.now()
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=5)
        ) as session:
            self.session = session
            
            tasks = []
            for source in self.funding_sources:
                task = self._collect_from_source(source)
                tasks.append(task)
                # Rate limiting
                await asyncio.sleep(1)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            successful_sources = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error collecting from {self.funding_sources[i]['name']}: {result}")
                elif result:
                    successful_sources += 1
                    self.collected_data.extend(result)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Generate summary
        summary = {
            "collection_id": hashlib.md5(f"{start_time}".encode()).hexdigest()[:8],
            "timestamp": start_time.isoformat(),
            "duration_seconds": duration,
            "sources_attempted": len(self.funding_sources),
            "sources_successful": successful_sources,
            "total_items_collected": len(self.collected_data),
            "items_per_source": self._count_items_by_source(),
            "coverage_improvement_estimate": self._estimate_coverage_improvement()
        }
        
        logger.info(f"✅ Funding data collection complete: {len(self.collected_data)} items from {successful_sources} sources")
        
        return summary
    
    async def _collect_from_source(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect data from a single source"""
        logger.info(f"📊 Collecting from: {source['name']}")
        
        try:
            async with self.session.get(source['url']) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Extract funding-related content
                    items = self._extract_funding_content(content, source)
                    
                    logger.info(f"✅ Extracted {len(items)} funding items from {source['name']}")
                    return items
                else:
                    logger.warning(f"HTTP {response.status} for {source['name']}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error accessing {source['name']}: {e}")
            return []
    
    def _extract_funding_content(self, html_content: str, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract funding and budget related content"""
        items = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Look for funding-related patterns
            funding_patterns = [
                r'(?i)eidbi.{0,50}(?:budget|funding|appropriation|allocation)',
                r'(?i)(?:budget|funding|appropriation|allocation).{0,50}eidbi',
                r'(?i)eidbi.{0,50}\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion))?',
                r'(?i)\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion))?.{0,50}eidbi',
                r'(?i)(?:fiscal year|fy).{0,50}eidbi',
                r'(?i)eidbi.{0,50}(?:expenditure|spending|cost|rate)',
                r'(?i)(?:medicaid|medical assistance|ma).{0,50}eidbi.{0,50}(?:payment|reimbursement|rate)',
                r'(?i)eidbi.{0,50}(?:forecast|projection|estimate)'
            ]
            
            # Extract chunks containing funding information
            for pattern in funding_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Extract context around the match
                    start = max(0, match.start() - 200)
                    end = min(len(text), match.end() + 200)
                    context = text[start:end].strip()
                    
                    if len(context) > 100:  # Minimum content threshold
                        item_id = hashlib.md5(f"{source['url']}_{context[:50]}".encode()).hexdigest()
                        
                        item = {
                            "id": f"funding_{item_id[:12]}",
                            "content": context,
                            "metadata": {
                                "title": f"{source['name']} - Funding Information",
                                "source": source['name'],
                                "url": source['url'],
                                "type": "funding_budget",
                                "category": source['type'],
                                "extraction_pattern": pattern,
                                "extracted_date": datetime.now().isoformat(),
                                "confidence_score": 0.85
                            }
                        }
                        items.append(item)
            
            # Also look for tables with budget data
            tables = soup.find_all('table')
            for table in tables:
                table_text = table.get_text()
                if any(keyword in table_text.lower() for keyword in ['eidbi', 'early intensive', 'behavioral intervention']):
                    table_id = hashlib.md5(f"{source['url']}_table_{table_text[:50]}".encode()).hexdigest()
                    
                    item = {
                        "id": f"funding_table_{table_id[:12]}",
                        "content": f"Budget/Financial Table: {table_text}",
                        "metadata": {
                            "title": f"{source['name']} - Financial Table",
                            "source": source['name'],
                            "url": source['url'],
                            "type": "funding_budget",
                            "category": f"{source['type']}_table",
                            "extracted_date": datetime.now().isoformat(),
                            "confidence_score": 0.90
                        }
                    }
                    items.append(item)
        
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
        
        return items
    
    def _count_items_by_source(self) -> Dict[str, int]:
        """Count items collected by source"""
        counts = {}
        for item in self.collected_data:
            source = item['metadata']['source']
            counts[source] = counts.get(source, 0) + 1
        return counts
    
    def _estimate_coverage_improvement(self) -> float:
        """Estimate coverage improvement based on collected data"""
        # Base coverage was 60%, estimate improvement based on items collected
        base_coverage = 0.60
        items_collected = len(self.collected_data)
        
        # Rough estimate: each 10 items improves coverage by ~5%
        improvement = (items_collected / 10) * 0.05
        new_coverage = min(base_coverage + improvement, 1.0)
        
        return round(new_coverage, 3)
    
    def save_collected_data(self, output_dir: str = "data/funding"):
        """Save collected funding data"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as JSONL for easy integration
        jsonl_file = output_path / f"eidbi_funding_data_{timestamp}.jsonl"
        with open(jsonl_file, 'w', encoding='utf-8') as f:
            for item in self.collected_data:
                f.write(json.dumps(item) + '\n')
        
        logger.info(f"💾 Saved {len(self.collected_data)} funding items to {jsonl_file}")
        
        # Save summary
        summary_file = output_path / f"funding_collection_summary_{timestamp}.json"
        summary = {
            "collection_date": datetime.now().isoformat(),
            "total_items": len(self.collected_data),
            "items_by_source": self._count_items_by_source(),
            "data_file": str(jsonl_file)
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        return jsonl_file, summary_file


async def main():
    """Main execution function"""
    print("🎯 EIDBI Funding Data Collection - Targeted Enhancement")
    print("=" * 60)
    
    collector = EIDBIFundingDataCollector()
    
    # Collect funding data
    print("\n📊 Collecting funding and budget data...")
    summary = await collector.collect_all_funding_data()
    
    print(f"\n✅ Collection Results:")
    print(f"   • Sources processed: {summary['sources_successful']}/{summary['sources_attempted']}")
    print(f"   • Total items collected: {summary['total_items_collected']}")
    print(f"   • Estimated coverage improvement: {summary['coverage_improvement_estimate']:.1%}")
    print(f"   • Duration: {summary['duration_seconds']:.1f} seconds")
    
    # Save collected data
    if collector.collected_data:
        print("\n💾 Saving collected data...")
        data_file, summary_file = collector.save_collected_data()
        print(f"   • Data saved to: {data_file}")
        print(f"   • Summary saved to: {summary_file}")
    
    print("\n🎯 Funding data collection complete!")
    
    return summary


if __name__ == "__main__":
    asyncio.run(main()) 