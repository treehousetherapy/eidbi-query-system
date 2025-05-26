"""
Enhanced EIDBI Data Scraper

This module extends the existing scraper to include:
- PDF document processing
- Multiple data source types (government, advocacy, academic)
- Robots.txt compliance
- Enhanced error handling and rate limiting
- Document type detection and metadata
- Comprehensive logging

Author: Enhanced for comprehensive EIDBI knowledge base
"""

import logging
from datetime import datetime, timedelta
import json
import time
import random
import hashlib
import re
from typing import List, Dict, Any, Set, Optional, Union
from urllib.parse import urljoin, urlparse, urlencode
from urllib.robotparser import RobotFileParser
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

# Standard library imports
import sys
import os

# Third-party imports
import requests
from bs4 import BeautifulSoup
import PyPDF2
import pdfplumber
from io import BytesIO

# Local imports - assuming the structure exists
try:
    from utils.http import fetch_url, create_session
    from utils.parsing import parse_html
    from utils.chunking import chunk_text
    from utils.gcs_utils import upload_string_to_gcs, upload_dict_to_gcs
    from utils.vertex_ai_utils import initialize_vertex_ai_once
    from utils.embedding_service import generate_embeddings
    
    # Config import
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from config.settings import settings
except ImportError as e:
    print(f"Error importing modules in enhanced_scraper: {e}")
    print("Please ensure all utility modules exist and config is properly set up")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)

class DocumentType(Enum):
    """Enumeration of supported document types"""
    HTML = "html"
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    TXT = "txt"
    UNKNOWN = "unknown"

class SourceType(Enum):
    """Enumeration of data source types"""
    GOVERNMENT_DHS = "government_dhs"
    GOVERNMENT_MEDICAID = "government_medicaid"
    ADVOCACY_ORG = "advocacy_org"
    ACADEMIC_RESEARCH = "academic_research"
    PROVIDER_MANUAL = "provider_manual"
    POLICY_DOCUMENT = "policy_document"
    LEGISLATION = "legislation"

@dataclass
class DataSource:
    """Configuration for a data source"""
    name: str
    base_url: str
    source_type: SourceType
    seed_urls: List[str]
    allowed_domains: List[str]
    file_patterns: List[str]
    keywords: List[str]
    max_depth: int = 2
    delay_range: tuple = (3.0, 6.0)
    respect_robots: bool = True
    rate_limit_per_minute: int = 10

@dataclass
class DocumentMetadata:
    """Metadata for processed documents"""
    url: str
    title: str
    document_type: DocumentType
    source_type: SourceType
    source_name: str
    file_size: Optional[int] = None
    last_modified: Optional[str] = None
    crawl_date: str = None
    language: str = "en"
    page_count: Optional[int] = None
    checksum: Optional[str] = None

class EnhancedEIDBI_Scraper:
    """Enhanced scraper for comprehensive EIDBI data collection"""
    
    def __init__(self):
        self.session = create_session()
        self.robots_cache: Dict[str, RobotFileParser] = {}
        self.crawl_delays: Dict[str, float] = {}
        self.last_request_times: Dict[str, datetime] = {}
        self.processed_urls: Set[str] = set()
        self.collected_documents: List[Dict[str, Any]] = []
        
        # Initialize data sources configuration
        self.data_sources = self._initialize_data_sources()
        
        # Initialize PDF processing
        self.pdf_extraction_methods = ['pdfplumber', 'pypdf2']
        
    def _initialize_data_sources(self) -> List[DataSource]:
        """Initialize comprehensive data source configurations"""
        return [
            # Minnesota DHS EIDBI Sources
            DataSource(
                name="Minnesota DHS EIDBI",
                base_url="https://www.dhs.state.mn.us",
                source_type=SourceType.GOVERNMENT_DHS,
                seed_urls=[
                    "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=DHS-293662",
                    "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs-305956",
                    "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs-292229",
                    "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=DHS-293657",
                ],
                allowed_domains=["dhs.state.mn.us", "mn.gov"],
                file_patterns=["*.pdf", "*eidbi*", "*autism*", "*developmental*"],
                keywords=["eidbi", "early intensive", "developmental", "behavioral intervention", "autism", "asd"],
                max_depth=3,
                delay_range=(2.0, 4.0),
                rate_limit_per_minute=15
            ),
            
            # Minnesota Medicaid Sources
            DataSource(
                name="Minnesota Medicaid Provider Manual",
                base_url="https://www.dhs.state.mn.us",
                source_type=SourceType.GOVERNMENT_MEDICAID,
                seed_urls=[
                    "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=id_006254",
                    "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_166706",
                ],
                allowed_domains=["dhs.state.mn.us", "mn.gov"],
                file_patterns=["*medicaid*", "*provider*manual*", "*billing*", "*policy*"],
                keywords=["medicaid", "provider manual", "billing", "services", "coverage", "eidbi"],
                max_depth=2,
                delay_range=(3.0, 5.0),
                rate_limit_per_minute=12
            ),
            
            # Autism Society of Minnesota
            DataSource(
                name="Autism Society of Minnesota",
                base_url="https://ausm.org",
                source_type=SourceType.ADVOCACY_ORG,
                seed_urls=[
                    "https://ausm.org/resources/",
                    "https://ausm.org/advocacy/",
                    "https://ausm.org/support-services/",
                ],
                allowed_domains=["ausm.org"],
                file_patterns=["*resources*", "*support*", "*services*", "*advocacy*"],
                keywords=["autism", "services", "support", "advocacy", "minnesota", "eidbi"],
                max_depth=2,
                delay_range=(4.0, 7.0),
                rate_limit_per_minute=8
            ),
            
            # The Arc Minnesota
            DataSource(
                name="The Arc Minnesota",
                base_url="https://arcminnesota.org",
                source_type=SourceType.ADVOCACY_ORG,
                seed_urls=[
                    "https://arcminnesota.org/advocacy/",
                    "https://arcminnesota.org/resources/",
                ],
                allowed_domains=["arcminnesota.org"],
                file_patterns=["*advocacy*", "*resources*", "*policy*"],
                keywords=["disability", "advocacy", "services", "minnesota", "developmental"],
                max_depth=2,
                delay_range=(4.0, 7.0),
                rate_limit_per_minute=8
            ),
            
            # Minnesota Legislature 
            DataSource(
                name="Minnesota Legislature",
                base_url="https://www.revisor.mn.gov",
                source_type=SourceType.LEGISLATION,
                seed_urls=[
                    "https://www.revisor.mn.gov/statutes/cite/256B.0943",
                    "https://www.revisor.mn.gov/statutes/cite/256B",
                ],
                allowed_domains=["revisor.mn.gov", "mn.gov"],
                file_patterns=["*256B*", "*statutes*", "*rules*"],
                keywords=["256B.0943", "medicaid", "eidbi", "developmental disabilities", "autism"],
                max_depth=1,
                delay_range=(3.0, 5.0),
                rate_limit_per_minute=10
            ),
        ]
    
    def check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt"""
        try:
            parsed_url = urlparse(url)
            domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            if domain not in self.robots_cache:
                robots_url = f"{domain}/robots.txt"
                rp = RobotFileParser()
                rp.set_url(robots_url)
                
                try:
                    rp.read()
                    self.robots_cache[domain] = rp
                    logger.info(f"Loaded robots.txt for {domain}")
                except Exception as e:
                    logger.warning(f"Could not load robots.txt for {domain}: {e}")
                    # If robots.txt can't be loaded, assume crawling is allowed
                    return True
            
            # Check if URL is allowed for our user agent
            user_agent = self.session.headers.get('User-Agent', '*')
            return self.robots_cache[domain].can_fetch(user_agent, url)
            
        except Exception as e:
            logger.error(f"Error checking robots.txt for {url}: {e}")
            return True  # Default to allowing if check fails
    
    def respect_rate_limit(self, domain: str, rate_limit: int):
        """Ensure we respect rate limits for each domain"""
        now = datetime.now()
        
        # Check last request time for this domain
        if domain in self.last_request_times:
            time_since_last = now - self.last_request_times[domain]
            min_interval = timedelta(seconds=60 / rate_limit)
            
            if time_since_last < min_interval:
                sleep_time = (min_interval - time_since_last).total_seconds()
                logger.info(f"Rate limiting: waiting {sleep_time:.2f}s for {domain}")
                time.sleep(sleep_time)
        
        self.last_request_times[domain] = datetime.now()
    
    def get_document_type(self, url: str, content_type: str = None) -> DocumentType:
        """Determine document type from URL and content type"""
        url_lower = url.lower()
        
        if content_type:
            if 'pdf' in content_type:
                return DocumentType.PDF
            elif 'html' in content_type:
                return DocumentType.HTML
        
        # Check file extension
        if url_lower.endswith('.pdf'):
            return DocumentType.PDF
        elif url_lower.endswith(('.doc', '.docx')):
            return DocumentType.DOC if url_lower.endswith('.doc') else DocumentType.DOCX
        elif url_lower.endswith('.txt'):
            return DocumentType.TXT
        elif any(ext in url_lower for ext in ['.html', '.htm', '.php', '.asp']):
            return DocumentType.HTML
        
        return DocumentType.HTML  # Default assumption
    
    def extract_pdf_text(self, pdf_content: bytes, url: str) -> Dict[str, Any]:
        """Extract text from PDF using multiple methods"""
        results = {
            'text': '',
            'metadata': {},
            'page_count': 0,
            'extraction_method': None,
            'success': False
        }
        
        # Try pdfplumber first (generally better for layout preservation)
        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                text_parts = []
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(f"\n--- Page {page_num + 1} ---\n{page_text}")
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num + 1} from {url}: {e}")
                        continue
                
                if text_parts:
                    results.update({
                        'text': '\n'.join(text_parts),
                        'page_count': len(pdf.pages),
                        'extraction_method': 'pdfplumber',
                        'success': True
                    })
                    
                    # Extract metadata if available
                    if pdf.metadata:
                        results['metadata'] = dict(pdf.metadata)
                    
                    logger.info(f"Successfully extracted {len(text_parts)} pages from PDF using pdfplumber")
                    return results
                    
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed for {url}: {e}")
        
        # Fallback to PyPDF2
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
            text_parts = []
            
            for page_num in range(len(pdf_reader.pages)):
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"\n--- Page {page_num + 1} ---\n{page_text}")
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num + 1} with PyPDF2: {e}")
                    continue
            
            if text_parts:
                results.update({
                    'text': '\n'.join(text_parts),
                    'page_count': len(pdf_reader.pages),
                    'extraction_method': 'pypdf2',
                    'success': True
                })
                
                # Extract metadata
                if pdf_reader.metadata:
                    results['metadata'] = {
                        k.replace('/', ''): v for k, v in pdf_reader.metadata.items()
                    }
                
                logger.info(f"Successfully extracted {len(text_parts)} pages from PDF using PyPDF2")
                return results
                
        except Exception as e:
            logger.error(f"PyPDF2 extraction also failed for {url}: {e}")
        
        logger.error(f"All PDF extraction methods failed for {url}")
        return results
    
    def fetch_document(self, url: str, source: DataSource) -> Optional[Dict[str, Any]]:
        """Fetch and process a document (HTML or PDF)"""
        try:
            # Check robots.txt if required
            if source.respect_robots and not self.check_robots_txt(url):
                logger.info(f"Robots.txt disallows crawling {url}")
                return None
            
            # Respect rate limits
            domain = urlparse(url).netloc
            self.respect_rate_limit(domain, source.rate_limit_per_minute)
            
            # Make the request
            logger.info(f"Fetching document: {url}")
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Get content type and size
            content_type = response.headers.get('content-type', '').lower()
            content_length = response.headers.get('content-length')
            file_size = int(content_length) if content_length else None
            
            # Determine document type
            doc_type = self.get_document_type(url, content_type)
            
            # Create metadata
            metadata = DocumentMetadata(
                url=url,
                title="",  # Will be extracted from content
                document_type=doc_type,
                source_type=source.source_type,
                source_name=source.name,
                file_size=file_size,
                last_modified=response.headers.get('last-modified'),
                crawl_date=datetime.now().isoformat(),
                checksum=None  # Will be calculated
            )
            
            # Process based on document type
            if doc_type == DocumentType.PDF:
                # Handle PDF documents
                pdf_content = response.content
                metadata.checksum = hashlib.md5(pdf_content).hexdigest()
                
                extraction_result = self.extract_pdf_text(pdf_content, url)
                if not extraction_result['success']:
                    logger.error(f"Failed to extract text from PDF: {url}")
                    return None
                
                # Update metadata with PDF-specific info
                metadata.title = extraction_result['metadata'].get('Title', 
                                 extraction_result['metadata'].get('title', 
                                 Path(urlparse(url).path).stem))
                metadata.page_count = extraction_result['page_count']
                
                return {
                    'content': extraction_result['text'],
                    'metadata': asdict(metadata),
                    'extraction_info': {
                        'method': extraction_result['extraction_method'],
                        'pdf_metadata': extraction_result['metadata']
                    }
                }
                
            else:
                # Handle HTML and other text documents
                html_content = response.text
                metadata.checksum = hashlib.md5(html_content.encode()).hexdigest()
                
                # Parse HTML content
                parsed_result = parse_html(html_content)
                if not parsed_result:
                    logger.warning(f"Failed to parse HTML content from {url}")
                    return None
                
                metadata.title = parsed_result.get('title', 'No Title Found')
                
                # Combine all text content
                page_text = parsed_result.get('text', '')
                
                # Add structured content
                tables = parsed_result.get('tables', [])
                lists = parsed_result.get('lists', [])
                
                if tables:
                    for table in tables:
                        caption = table.get('caption', 'Table')
                        page_text += f"\n\n{caption}:\n"
                        headers = table.get('headers', [])
                        for row in table.get('data', []):
                            row_text = " | ".join([f"{headers[i]}: {row.get(header, '')}" 
                                                 for i, header in enumerate(headers)])
                            page_text += f"\n{row_text}"
                
                if lists:
                    for list_item in lists:
                        title = list_item.get('title', 'List')
                        page_text += f"\n\n{title}:\n"
                        for item in list_item.get('items', []):
                            page_text += f"\n- {item}"
                
                return {
                    'content': page_text,
                    'metadata': asdict(metadata),
                    'extraction_info': {
                        'method': 'html_parsing',
                        'html_metadata': parsed_result
                    }
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error processing {url}: {e}", exc_info=True)
            return None
    
    def is_relevant_content(self, content: str, keywords: List[str], url: str) -> bool:
        """Check if content is relevant based on keywords"""
        content_lower = content.lower()
        url_lower = url.lower()
        
        # Always include if URL contains EIDBI
        if 'eidbi' in url_lower:
            return True
        
        # Count keyword matches
        matches = 0
        for keyword in keywords:
            if keyword.lower() in content_lower or keyword.lower() in url_lower:
                matches += 1
        
        # Require at least 2 keyword matches for relevance
        return matches >= 2
    
    def discover_links(self, html_content: str, base_url: str, source: DataSource) -> List[str]:
        """Discover relevant links from HTML content"""
        if not html_content:
            return []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            discovered_links = []
            
            # Find all links
            for a_tag in soup.find_all('a', href=True):
                href = a_tag.get('href', '').strip()
                if not href or href.startswith(('#', 'javascript:', 'mailto:')):
                    continue
                
                # Convert to absolute URL
                absolute_url = urljoin(base_url, href)
                
                # Check if domain is allowed
                domain = urlparse(absolute_url).netloc.lower()
                if not any(allowed_domain in domain for allowed_domain in source.allowed_domains):
                    continue
                
                # Check file patterns
                url_path = urlparse(absolute_url).path.lower()
                link_text = a_tag.get_text().strip().lower()
                
                # Check if matches file patterns or keywords
                pattern_match = any(
                    pattern.replace('*', '') in url_path or pattern.replace('*', '') in link_text
                    for pattern in source.file_patterns
                )
                
                keyword_match = any(
                    keyword.lower() in url_path or keyword.lower() in link_text
                    for keyword in source.keywords
                )
                
                if pattern_match or keyword_match:
                    discovered_links.append(absolute_url)
            
            return discovered_links
            
        except Exception as e:
            logger.error(f"Error discovering links from {base_url}: {e}")
            return []
    
    def scrape_data_source(self, source: DataSource, max_documents: int = 100) -> List[Dict[str, Any]]:
        """Scrape all documents from a specific data source"""
        logger.info(f"Starting scrape of data source: {source.name}")
        
        documents = []
        urls_to_visit = [(url, 0) for url in source.seed_urls]  # (url, depth)
        visited_urls = set()
        
        while urls_to_visit and len(documents) < max_documents:
            current_url, depth = urls_to_visit.pop(0)
            
            if current_url in visited_urls:
                continue
            
            visited_urls.add(current_url)
            
            # Fetch and process document
            document = self.fetch_document(current_url, source)
            if document:
                # Check relevance
                if self.is_relevant_content(document['content'], source.keywords, current_url):
                    documents.append(document)
                    logger.info(f"Collected relevant document: {current_url}")
                else:
                    logger.info(f"Document not relevant enough: {current_url}")
            
            # Discover more links if within depth limit
            if depth < source.max_depth and document and 'extraction_info' in document:
                if document['extraction_info']['method'] == 'html_parsing':
                    html_content = ""  # We'd need to modify fetch_document to return raw HTML
                    # For now, we'll skip link discovery from already processed documents
                    # In a full implementation, we'd want to separate fetching from processing
            
            # Add delay between requests
            delay = random.uniform(*source.delay_range)
            logger.info(f"Waiting {delay:.2f}s before next request...")
            time.sleep(delay)
        
        logger.info(f"Completed scraping {source.name}: {len(documents)} documents collected")
        return documents
    
    def chunk_and_embed_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process documents into chunks and generate embeddings"""
        logger.info(f"Processing {len(documents)} documents into chunks with embeddings...")
        
        all_chunks = []
        
        for doc in documents:
            try:
                # Create chunks from document content
                chunks = chunk_text(
                    text=doc['content'],
                    url=doc['metadata']['url'],
                    title=doc['metadata']['title']
                )
                
                if not chunks:
                    logger.warning(f"No chunks generated for document: {doc['metadata']['url']}")
                    continue
                
                # Add document metadata to each chunk
                for chunk in chunks:
                    chunk['source_metadata'] = doc['metadata']
                    chunk['extraction_info'] = doc.get('extraction_info', {})
                
                # Generate embeddings for all chunks at once
                chunk_contents = [chunk['content'] for chunk in chunks]
                embeddings = generate_embeddings(chunk_contents)
                
                if embeddings:
                    successful_chunks = 0
                    for i, chunk in enumerate(chunks):
                        if embeddings[i] is not None:
                            chunk['embedding'] = embeddings[i]
                            all_chunks.append(chunk)
                            successful_chunks += 1
                    
                    logger.info(f"Successfully processed {successful_chunks}/{len(chunks)} chunks "
                               f"from {doc['metadata']['title']}")
                else:
                    logger.error(f"Failed to generate embeddings for document: {doc['metadata']['url']}")
                
            except Exception as e:
                logger.error(f"Error processing document {doc['metadata']['url']}: {e}", exc_info=True)
                continue
        
        logger.info(f"Total chunks with embeddings: {len(all_chunks)}")
        return all_chunks
    
    def _prepare_chunk_for_json(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a chunk for JSON serialization by converting enum values to strings"""
        import copy
        chunk_copy = copy.deepcopy(chunk)
        
        if 'source_metadata' in chunk_copy:
            metadata = chunk_copy['source_metadata']
            for key, value in metadata.items():
                if hasattr(value, 'value'):  # Check if it's an enum
                    metadata[key] = value.value
        
        return chunk_copy
    
    def save_results(self, chunks: List[Dict[str, Any]], source_name: str = "enhanced_scrape") -> str:
        """Save scraping results locally and optionally to GCS"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"enhanced_eidbi_data_{source_name}_{timestamp}.jsonl"
        
        # Save locally
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for chunk in chunks:
                    # Convert enum values to strings for JSON serialization
                    chunk_copy = self._prepare_chunk_for_json(chunk)
                    f.write(json.dumps(chunk_copy, ensure_ascii=False) + '\n')
            
            logger.info(f"Successfully saved {len(chunks)} chunks to {filename}")
            
            # Save summary file
            summary = {
                'timestamp': timestamp,
                'total_chunks': len(chunks),
                'unique_sources': len(set(chunk['source_metadata']['url'] for chunk in chunks)),
                'source_types': list(set(
                    chunk['source_metadata']['source_type'].value if hasattr(chunk['source_metadata']['source_type'], 'value') 
                    else chunk['source_metadata']['source_type'] for chunk in chunks
                )),
                'document_types': list(set(
                    chunk['source_metadata']['document_type'].value if hasattr(chunk['source_metadata']['document_type'], 'value')
                    else chunk['source_metadata']['document_type'] for chunk in chunks
                ))
            }
            
            summary_filename = f"enhanced_eidbi_summary_{source_name}_{timestamp}.json"
            with open(summary_filename, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved summary to {summary_filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            return ""
    
    def run_comprehensive_scrape(self, max_docs_per_source: int = 50) -> List[Dict[str, Any]]:
        """Run comprehensive scraping across all configured data sources"""
        logger.info("Starting comprehensive EIDBI data scraping...")
        
        # Initialize Vertex AI for embeddings
        if not initialize_vertex_ai_once():
            logger.error("Failed to initialize Vertex AI. Cannot generate embeddings.")
            return []
        
        all_chunks = []
        
        for source in self.data_sources:
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing data source: {source.name}")
                logger.info(f"Source type: {source.source_type.value}")
                logger.info(f"Base URL: {source.base_url}")
                logger.info(f"{'='*60}")
                
                # Scrape documents from this source
                documents = self.scrape_data_source(source, max_docs_per_source)
                
                if documents:
                    # Process documents into chunks with embeddings
                    source_chunks = self.chunk_and_embed_documents(documents)
                    all_chunks.extend(source_chunks)
                    
                    # Save intermediate results for this source
                    if source_chunks:
                        source_filename = self.save_results(
                            source_chunks, 
                            source.name.lower().replace(' ', '_')
                        )
                        logger.info(f"Saved {len(source_chunks)} chunks from {source.name}")
                
                # Add delay between different sources
                delay = random.uniform(5.0, 10.0)
                logger.info(f"Waiting {delay:.2f}s before next data source...")
                time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error processing data source {source.name}: {e}", exc_info=True)
                continue
        
        # Save combined results
        if all_chunks:
            combined_filename = self.save_results(all_chunks, "combined")
            logger.info(f"\nScraping complete! Total chunks collected: {len(all_chunks)}")
            logger.info(f"Combined results saved to: {combined_filename}")
        else:
            logger.warning("No chunks were collected from any data source!")
        
        return all_chunks

def main():
    """Main function to run the enhanced scraper"""
    scraper = EnhancedEIDBI_Scraper()
    
    # Run comprehensive scraping
    results = scraper.run_comprehensive_scrape(max_docs_per_source=30)
    
    if results:
        print(f"\n✅ Enhanced scraping completed successfully!")
        print(f"📊 Total chunks collected: {len(results)}")
        print(f"🔗 Unique sources: {len(set(chunk['source_metadata']['url'] for chunk in results))}")
        print(f"📄 Document types: {set(chunk['source_metadata']['document_type'].value for chunk in results)}")
        print(f"🏢 Source types: {set(chunk['source_metadata']['source_type'].value for chunk in results)}")
    else:
        print("❌ No data was collected. Check logs for errors.")

if __name__ == "__main__":
    main() 