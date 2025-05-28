#!/usr/bin/env python3
"""
EIDBI Training Requirements Data Collector

Specialized collector for Minnesota EIDBI provider training requirements
from official DHS sources.

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
import pdfplumber
from urllib.parse import urljoin, urlparse
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('eidbi_training_requirements_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EIDIBITrainingRequirementsCollector:
    """Collector for EIDBI training requirements data"""
    
    def __init__(self):
        self.data_dir = Path("data/training_requirements")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Official sources for EIDBI training requirements
        self.sources = [
            {
                "name": "Minnesota DHS Required EIDBI Trainings",
                "url": "https://mn.gov/dhs/partners-and-providers/training-conferences/minnesota-health-care-programs/provider-training/required-eidbi-trainings.jsp",
                "type": "webpage",
                "topic": "Training Requirements"
            },
            {
                "name": "DHS Provider Training Document",
                "url": "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs-292819",
                "type": "document",
                "topic": "Training Requirements"
            },
            {
                "name": "EIDBI Billing and Provider Training",
                "url": "https://mn.gov/dhs/partners-and-providers/training-conferences/minnesota-health-care-programs/provider-training/eidbi-billing-lab.jsp",
                "type": "webpage",
                "topic": "Training Requirements"
            },
            {
                "name": "EIDBI Benefit Overview",
                "url": "https://mn.gov/dhs/partners-and-providers/news-initiatives-reports-workgroups/long-term-services-and-supports/eidbi/eidbi.jsp",
                "type": "webpage",
                "topic": "Training Requirements"
            },
            {
                "name": "State Plan Amendment 23-17",
                "url": "https://mn.gov/dhs/assets/23-17-spa_tcm1053-584561.pdf",
                "type": "pdf",
                "topic": "Training Requirements"
            },
            {
                "name": "EIDBI Licensure Study Report",
                "url": "https://mn.gov/dhs/partners-and-providers/news-initiatives-reports-workgroups/long-term-services-and-supports/eidbi/licensure-study.jsp",
                "type": "webpage",
                "topic": "Training Requirements"
            }
        ]
        
        self.session = None
        self.collected_data = []
        self.stats = {
            "sources_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "total_chunks": 0,
            "total_text_length": 0
        }
        
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
            
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\-.,;:!?()\[\]{}\'\"/@#$%&*+=]', ' ', text)
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        return text.strip()
        
    def chunk_text(self, text: str, max_chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """Split text into chunks suitable for embedding"""
        chunks = []
        
        # Split by paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_chunk = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # If adding this paragraph would exceed limit, save current chunk
            if current_chunk and len(current_chunk) + len(para) + 1 > max_chunk_size:
                chunks.append({
                    "text": current_chunk.strip(),
                    "length": len(current_chunk.strip())
                })
                current_chunk = para
            else:
                current_chunk += (" " + para) if current_chunk else para
                
        # Add any remaining text
        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "length": len(current_chunk.strip())
            })
            
        return chunks
        
    async def extract_webpage_content(self, url: str) -> Optional[str]:
        """Extract text content from a webpage"""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                        
                    # Extract main content
                    main_content = soup.find('main') or soup.find('div', class_='content') or soup.body
                    
                    if main_content:
                        text = main_content.get_text(separator='\n')
                        return self.clean_text(text)
                    else:
                        return self.clean_text(soup.get_text(separator='\n'))
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
        except Exception as e:
            logger.error(f"Error extracting webpage {url}: {e}")
            return None
            
    def extract_pdf_content(self, url: str) -> Optional[str]:
        """Extract text content from a PDF"""
        try:
            # Download PDF
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                pdf_path = self.data_dir / f"temp_{hashlib.md5(url.encode()).hexdigest()}.pdf"
                
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                    
                # Extract text from PDF
                text = ""
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                            
                # Clean up temp file
                pdf_path.unlink()
                
                return self.clean_text(text) if text else None
            else:
                logger.warning(f"HTTP {response.status_code} for PDF {url}")
                return None
        except Exception as e:
            logger.error(f"Error extracting PDF {url}: {e}")
            return None
            
    def generate_embedding(self, text: str) -> List[float]:
        """Generate mock embedding for text"""
        # In production, this would use actual embedding service
        # For now, generate deterministic mock embedding
        hash_val = hashlib.md5(text.encode()).hexdigest()
        embedding = []
        for i in range(0, min(len(hash_val), 768), 2):
            val = int(hash_val[i:i+2], 16) / 255.0
            embedding.append(val)
            
        # Pad to 768 dimensions
        while len(embedding) < 768:
            embedding.append(0.0)
            
        return embedding[:768]
        
    async def process_source(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a single source and return collected data items"""
        logger.info(f"📄 Processing: {source['name']}")
        items = []
        
        try:
            # Extract content based on type
            if source['type'] == 'pdf':
                content = self.extract_pdf_content(source['url'])
            else:
                content = await self.extract_webpage_content(source['url'])
                
            if content:
                # Chunk the content
                chunks = self.chunk_text(content)
                
                for i, chunk in enumerate(chunks):
                    # Generate unique ID
                    chunk_id = hashlib.md5(
                        f"{source['url']}_chunk_{i}_{chunk['text'][:50]}".encode()
                    ).hexdigest()
                    
                    # Generate embedding
                    embedding = self.generate_embedding(chunk['text'])
                    
                    # Create data item
                    item = {
                        "id": f"training_{chunk_id}",
                        "title": f"{source['name']} - Part {i+1}",
                        "content": chunk['text'],
                        "source": source['name'],
                        "source_url": source['url'],
                        "category": "Training Requirements",
                        "topic": source['topic'],
                        "metadata": {
                            "extraction_date": datetime.now().isoformat(),
                            "chunk_number": i + 1,
                            "total_chunks": len(chunks),
                            "text_length": chunk['length'],
                            "document_type": source['type']
                        },
                        "embedding": embedding,
                        "last_updated": datetime.now().isoformat()
                    }
                    
                    items.append(item)
                    
                self.stats['successful_extractions'] += 1
                self.stats['total_chunks'] += len(chunks)
                self.stats['total_text_length'] += sum(c['length'] for c in chunks)
                logger.info(f"✅ Extracted {len(chunks)} chunks from {source['name']}")
                
            else:
                self.stats['failed_extractions'] += 1
                logger.warning(f"❌ No content extracted from {source['name']}")
                
        except Exception as e:
            self.stats['failed_extractions'] += 1
            logger.error(f"❌ Error processing {source['name']}: {e}")
            
        # Respectful delay
        await asyncio.sleep(2)
        
        return items
        
    async def collect_all_data(self):
        """Collect data from all sources"""
        logger.info("🚀 Starting EIDBI Training Requirements data collection...")
        
        for source in self.sources:
            self.stats['sources_processed'] += 1
            items = await self.process_source(source)
            self.collected_data.extend(items)
            
        logger.info(f"✅ Collection complete: {len(self.collected_data)} total items")
        
    def save_data(self):
        """Save collected data to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as JSONL for knowledge base ingestion
        jsonl_file = self.data_dir / f"eidbi_training_requirements_{timestamp}.jsonl"
        with open(jsonl_file, 'w', encoding='utf-8') as f:
            for item in self.collected_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
                
        logger.info(f"💾 Saved {len(self.collected_data)} items to {jsonl_file}")
        
        # Save summary report
        summary = {
            "collection_date": datetime.now().isoformat(),
            "stats": self.stats,
            "sources": self.sources,
            "total_items": len(self.collected_data),
            "output_file": str(jsonl_file)
        }
        
        summary_file = self.data_dir / f"collection_summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
            
        return jsonl_file, summary_file
        
    def generate_report(self) -> str:
        """Generate a summary report"""
        report = f"""
# EIDBI Training Requirements Data Collection Report

**Collection Date**: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}

## 📊 Collection Statistics

- **Sources Processed**: {self.stats['sources_processed']}/{len(self.sources)}
- **Successful Extractions**: {self.stats['successful_extractions']}
- **Failed Extractions**: {self.stats['failed_extractions']}
- **Total Text Chunks**: {self.stats['total_chunks']}
- **Total Text Length**: {self.stats['total_text_length']:,} characters

## 📄 Sources Processed

"""
        for i, source in enumerate(self.sources, 1):
            report += f"{i}. **{source['name']}**\n"
            report += f"   - URL: {source['url']}\n"
            report += f"   - Type: {source['type']}\n\n"
            
        report += f"""
## 📈 Data Volume Summary

- **Total Items Collected**: {len(self.collected_data)}
- **Average Chunk Size**: {self.stats['total_text_length'] // max(self.stats['total_chunks'], 1):,} characters
- **Coverage**: Training Requirements topic

## 🎯 Next Steps

1. Integrate collected data into main knowledge base
2. Test queries related to training requirements
3. Verify improved coverage for training-related questions
4. Monitor user queries for additional training topics

## ✅ Status: Collection Complete

All specified sources have been processed and data is ready for integration.
"""
        return report


async def main():
    """Main execution function"""
    print("\n" + "="*60)
    print("🎯 EIDBI Training Requirements Data Collection")
    print("="*60 + "\n")
    
    async with EIDIBITrainingRequirementsCollector() as collector:
        # Collect data
        await collector.collect_all_data()
        
        # Save data
        jsonl_file, summary_file = collector.save_data()
        
        # Generate and display report
        report = collector.generate_report()
        print(report)
        
        # Save report
        report_file = collector.data_dir / f"collection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
            
        print(f"\n📁 Output files:")
        print(f"   - Data: {jsonl_file}")
        print(f"   - Summary: {summary_file}")
        print(f"   - Report: {report_file}")
        
        return jsonl_file


if __name__ == "__main__":
    asyncio.run(main()) 