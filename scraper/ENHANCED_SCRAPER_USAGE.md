# Enhanced EIDBI Data Scraper Usage Guide

This guide explains how to use the enhanced EIDBI data scraper that includes comprehensive data source integration, PDF processing, robots.txt compliance, and advanced error handling.

## Features

### 🔧 Core Capabilities
- **Multi-format document processing**: HTML, PDF, DOC, DOCX, TXT
- **Multiple data source types**: Government (DHS, Medicaid), advocacy organizations, academic sources, legislation
- **Robots.txt compliance**: Automatic checking and respect for crawling restrictions
- **Rate limiting**: Configurable per-domain rate limits to avoid overloading servers
- **PDF text extraction**: Multiple extraction methods (pdfplumber, PyPDF2) with fallback
- **Comprehensive metadata**: Document type, source type, crawl date, checksums, etc.
- **Error recovery**: Robust error handling and logging for debugging

### 📊 Data Sources Included
1. **Minnesota DHS EIDBI**: Official program documentation and policies
2. **Minnesota Medicaid**: Provider manuals, billing guides, coverage information  
3. **Autism Society of Minnesota**: Advocacy resources and support information
4. **The Arc Minnesota**: Disability advocacy and policy resources
5. **Minnesota Legislature**: Relevant statutes and regulations (256B.0943, etc.)

## Installation

### 1. Install Dependencies

```bash
# Navigate to the scraper directory
cd scraper

# Install enhanced requirements
pip install -r enhanced_requirements.txt
```

### 2. Required Dependencies
- **Core**: `requests`, `beautifulsoup4`, `pydantic`, `google-cloud-aiplatform`
- **PDF Processing**: `PyPDF2`, `pdfplumber`, `pillow`
- **Enhanced Features**: `urllib3`, `chardet`, `python-dateutil`

## Basic Usage

### Quick Start

```python
from enhanced_scraper import EnhancedEIDBI_Scraper

# Initialize the scraper
scraper = EnhancedEIDBI_Scraper()

# Run comprehensive scraping across all configured data sources
results = scraper.run_comprehensive_scrape(max_docs_per_source=30)

print(f"Collected {len(results)} chunks from {len(set(chunk['source_metadata']['url'] for chunk in results))} documents")
```

### Command Line Usage

```bash
# Run the enhanced scraper directly
python enhanced_scraper.py

# The scraper will:
# 1. Process all configured data sources
# 2. Extract text from HTML and PDF documents
# 3. Generate embeddings for each text chunk
# 4. Save results locally with metadata
```

## Advanced Configuration

### Custom Data Sources

```python
from enhanced_scraper import DataSource, SourceType, EnhancedEIDBI_Scraper

# Define a custom data source
custom_source = DataSource(
    name="Custom EIDBI Resource",
    base_url="https://example.org",
    source_type=SourceType.ADVOCACY_ORG,
    seed_urls=[
        "https://example.org/eidbi-resources/",
        "https://example.org/autism-support/"
    ],
    allowed_domains=["example.org"],
    file_patterns=["*eidbi*", "*autism*", "*support*"],
    keywords=["eidbi", "autism", "support", "minnesota"],
    max_depth=2,
    delay_range=(4.0, 7.0),
    rate_limit_per_minute=10
)

# Initialize scraper and add custom source
scraper = EnhancedEIDBI_Scraper()
scraper.data_sources.append(custom_source)

# Run scraping with custom source included
results = scraper.run_comprehensive_scrape()
```

### PDF Processing Only

```python
from utils.pdf_processor import PDFProcessor

# Initialize PDF processor
pdf_processor = PDFProcessor()

# Read PDF file
with open('document.pdf', 'rb') as f:
    pdf_content = f.read()

# Extract text with metadata
result = pdf_processor.extract_text(pdf_content, url="document.pdf")

if result['success']:
    print(f"Extracted {len(result['text'])} characters")
    print(f"Pages: {result['page_count']}")
    print(f"Method: {result['extraction_method']}")
    print(f"Metadata: {result['metadata']}")
else:
    print(f"Extraction failed: {result['errors']}")
```

### Robots.txt Checking

```python
from utils.robots_checker import RobotsChecker

# Initialize robots checker
robots = RobotsChecker(user_agent="Enhanced-EIDBI-Scraper/1.0")

# Check if URL can be crawled
url = "https://www.dhs.state.mn.us/some-page"
if robots.can_fetch(url):
    print(f"✅ Crawling allowed for {url}")
    
    # Check crawl delay
    delay = robots.get_crawl_delay(url)
    if delay:
        print(f"⏱️ Recommended crawl delay: {delay} seconds")
else:
    print(f"❌ Crawling not allowed for {url}")

# Get comprehensive robots.txt info
summary = robots.get_robots_summary(url)
print(f"Domain: {summary['domain']}")
print(f"Sitemaps: {summary['sitemaps']}")
```

## Output Format

### Chunk Structure
Each processed text chunk includes:

```json
{
  "id": "unique_chunk_id",
  "content": "extracted_text_content",
  "url": "source_document_url", 
  "title": "document_title",
  "chunk_index": 0,
  "total_chunks": 5,
  "embedding": [0.1, 0.2, ...],
  "source_metadata": {
    "url": "source_url",
    "title": "document_title", 
    "document_type": "pdf",
    "source_type": "government_dhs",
    "source_name": "Minnesota DHS EIDBI",
    "file_size": 1024000,
    "crawl_date": "2024-01-15T10:30:00",
    "checksum": "md5_hash",
    "page_count": 10
  },
  "extraction_info": {
    "method": "pdfplumber",
    "pdf_metadata": {"Author": "MN DHS", "Title": "EIDBI Guide"}
  }
}
```

### File Outputs

The scraper generates several output files:

1. **Enhanced data files**: `enhanced_eidbi_data_[source]_[timestamp].jsonl`
2. **Summary files**: `enhanced_eidbi_summary_[source]_[timestamp].json`
3. **Combined results**: `enhanced_eidbi_data_combined_[timestamp].jsonl`

## Configuration Options

### Scraper Settings

```python
# Customize scraping behavior
scraper = EnhancedEIDBI_Scraper()

# Modify global settings
scraper.user_agent = "Custom-EIDBI-Bot/1.0"
scraper.cache_duration_hours = 48  # Cache robots.txt longer

# Run with custom limits
results = scraper.run_comprehensive_scrape(
    max_docs_per_source=50  # Increase document limit per source
)
```

### Data Source Customization

Each data source can be customized with:

- **Rate limiting**: `rate_limit_per_minute` (requests per minute)
- **Crawl depth**: `max_depth` (how deep to follow links)
- **Delay range**: `delay_range` (min, max seconds between requests)
- **File patterns**: `file_patterns` (what types of files to look for)
- **Keywords**: `keywords` (relevance filtering terms)
- **Domains**: `allowed_domains` (permitted domains to crawl)

## Error Handling

### Common Issues and Solutions

1. **PDF Extraction Failures**
   ```python
   # Check PDF processor availability
   from utils.pdf_processor import PYPDF2_AVAILABLE, PDFPLUMBER_AVAILABLE
   print(f"PyPDF2: {PYPDF2_AVAILABLE}, pdfplumber: {PDFPLUMBER_AVAILABLE}")
   ```

2. **Robots.txt Access Issues**
   ```python
   # Check robots.txt status
   summary = robots.get_robots_summary(url)
   if summary.get('fetch_failed'):
       print("Could not fetch robots.txt - proceeding with caution")
   ```

3. **Rate Limiting**
   ```python
   # Adjust delays for problematic domains
   source.delay_range = (10.0, 15.0)  # Increase delays
   source.rate_limit_per_minute = 5   # Reduce rate limit
   ```

### Logging Configuration

```python
import logging

# Enable debug logging for detailed troubleshooting
logging.getLogger('enhanced_scraper').setLevel(logging.DEBUG)
logging.getLogger('utils.pdf_processor').setLevel(logging.DEBUG)
logging.getLogger('utils.robots_checker').setLevel(logging.DEBUG)
```

## Integration with Existing System

### Adding Enhanced Data to Vector Database

```python
# After running enhanced scraper
enhanced_chunks = scraper.run_comprehensive_scrape()

# The chunks already include embeddings and can be directly added to your vector database
for chunk in enhanced_chunks:
    # Each chunk has:
    # - chunk['embedding']: Vector embedding
    # - chunk['content']: Text content  
    # - chunk['source_metadata']: Rich metadata
    # - chunk['extraction_info']: Processing details
    
    # Add to your existing vector database
    vector_db.add_chunk(chunk)
```

### Merging with Existing Data

```python
# Combine with existing scraped data
existing_data = load_existing_data("existing_chunks.jsonl")
enhanced_data = scraper.run_comprehensive_scrape()

# Merge and deduplicate
combined_data = merge_and_deduplicate(existing_data, enhanced_data)
```

## Performance Optimization

### Concurrent Processing

For large-scale scraping, consider:

1. **Batch processing**: Process documents in batches
2. **Parallel embedding generation**: Use multiple API calls
3. **Selective re-scraping**: Skip already processed documents based on checksums

### Memory Management

```python
# Process sources individually to manage memory
for source in scraper.data_sources:
    documents = scraper.scrape_data_source(source, max_documents=25)
    chunks = scraper.chunk_and_embed_documents(documents)
    
    # Save immediately and clear memory
    scraper.save_results(chunks, source.name.lower().replace(' ', '_'))
    del documents, chunks  # Free memory
```

## Monitoring and Maintenance

### Cache Management

```python
# Monitor robots.txt cache
stats = robots.get_cache_stats()
print(f"Cache entries: {stats['total_entries']}")
print(f"Valid entries: {stats['valid_entries']}")

# Clear expired cache entries
robots.clear_cache()
```

### Regular Updates

1. **Weekly runs**: Update data sources weekly
2. **Incremental updates**: Track document changes via checksums
3. **Source monitoring**: Monitor for new data sources or URL changes

## Troubleshooting

### Debug Information

```python
# Enable comprehensive logging
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Run with debug output
results = scraper.run_comprehensive_scrape()
```

### Common Error Messages

1. **"No PDF processing libraries available"**
   - Install: `pip install PyPDF2 pdfplumber`

2. **"Failed to initialize Vertex AI"**
   - Check authentication and project configuration
   - Verify API is enabled in Google Cloud Console

3. **"Robots.txt disallows crawling"**
   - Review robots.txt file for the domain
   - Consider contacting site owner for permission

## Best Practices

1. **Respect rate limits**: Always use appropriate delays between requests
2. **Monitor resource usage**: Check for memory leaks with large document sets
3. **Validate extractions**: Spot-check PDF extractions for quality
4. **Update regularly**: Keep data sources current with periodic re-scraping
5. **Error recovery**: Implement retry logic for transient failures
6. **Documentation**: Keep track of which sources provide the best quality data

For additional support or questions, check the logs and error messages which provide detailed debugging information. 