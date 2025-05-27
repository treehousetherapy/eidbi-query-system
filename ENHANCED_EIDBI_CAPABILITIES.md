# Enhanced EIDBI Query System - Comprehensive Capabilities

## Overview

The Enhanced EIDBI Query System now includes advanced capabilities for structured data ingestion, provider directory scraping, improved search and retrieval, enhanced prompt engineering, and automated data refresh scheduling. These enhancements significantly improve the system's ability to provide accurate, up-to-date information about Minnesota EIDBI programs.

## 🆕 New Capabilities

### 1. Structured Data Ingestion

**Purpose**: Handle structured data snippets (JSON/CSV) containing key facts like provider counts, with metadata tracking.

**Features**:
- JSON and CSV file ingestion
- Metadata tracking (source, last updated, confidence level)
- Search and retrieval of structured facts
- Integration with vector database
- Provider statistics management

**Usage Examples**:
```python
from app.services.structured_data_service import StructuredDataService, StructuredDataEntry

# Initialize service
service = StructuredDataService()

# Add provider count data
provider_entry = StructuredDataEntry(
    id="mn_eidbi_providers_2025",
    category="provider_count",
    key="total_eidbi_providers",
    value=85,
    source="Minnesota DHS Provider Directory",
    source_url="https://www.dhs.state.mn.us/...",
    notes="Official count as of January 2025"
)
service.add_entry(provider_entry)

# Search for provider information
results = service.search_entries("provider count")

# Get current provider statistics
stats = service.get_provider_stats()
```

**File Locations**:
- `backend/app/services/structured_data_service.py`
- Data stored in: `data/structured/structured_data.json`

---

### 2. Provider Directory Scraper

**Purpose**: Automatically scrape Minnesota DHS Provider Directory to extract current EIDBI provider counts and information.

**Features**:
- Multiple search strategies (service type, keywords)
- Robots.txt compliance with rate limiting
- Provider information extraction (name, address, county, phone)
- Count aggregation and county breakdown
- Error handling and retry logic

**Usage Examples**:
```python
from app.services.provider_scraper import ProviderDirectoryScraper

# Initialize scraper
scraper = ProviderDirectoryScraper()

# Scrape current provider data
total_count, county_counts, providers = scraper.scrape_provider_data()

print(f"Found {total_count} EIDBI providers")
print(f"County breakdown: {county_counts}")

# Export detailed data
scraper.export_provider_data(providers, "provider_data_2025.json")
```

**Scraped Data Sources**:
- Minnesota DHS Provider Directory
- EIDBI Program Pages
- County-specific provider listings

**File Locations**:
- `backend/app/services/provider_scraper.py`

---

### 3. Enhanced Vector Database Integration

**Purpose**: Seamlessly integrate structured data with existing vector search capabilities and improve search coverage.

**Enhancements**:
- **Increased Top-K Results**: Default increased from 5 to 15 neighbors for better coverage
- **Structured Data Integration**: Structured facts now searchable alongside documents
- **Hybrid Search Enhancement**: Improved scoring with structured data prioritization
- **Provider-Specific Search**: Special handling for provider count queries

**New Functions**:
```python
from app.services.vector_db_service import (
    search_structured_data,
    get_provider_statistics,
    update_provider_data,
    hybrid_search
)

# Search structured data specifically
structured_results = search_structured_data(["provider", "count"])

# Get current provider statistics
provider_stats = get_provider_statistics()

# Update provider data
update_provider_data(
    total_count=75,
    by_county={"Hennepin": 25, "Ramsey": 20, "Dakota": 15},
    source="Minnesota DHS",
    source_url="https://www.dhs.state.mn.us/..."
)

# Enhanced hybrid search (increased coverage)
hybrid_results = hybrid_search(embedding, keywords, num_results=12)
```

**Configuration Changes**:
- `DEFAULT_NUM_NEIGHBORS`: 5 → 15
- `DEFAULT_KEYWORD_RESULTS`: 10 → 20  
- `DEFAULT_HYBRID_RESULTS`: 10 → 12

**File Locations**:
- `backend/app/services/vector_db_service.py` (enhanced)

---

### 4. Enhanced Prompt Engineering

**Purpose**: Provide better handling of missing data with appropriate fallback responses, especially for provider count queries.

**New Features**:
- **Provider Query Detection**: Automatically identifies provider count questions
- **Missing Data Handling**: Explicit statements when exact data is not available
- **Fallback Guidance**: Directs users to official sources when data is missing
- **Enhanced Templates**: Specific templates for different query types

**Provider Count Template Example**:
```
Instructions:
- If asking about provider counts/numbers: Check if exact numbers are available in the context
- If exact provider count NOT found in context, explicitly state: "The exact number of EIDBI providers is not specified in the available information."
- Provide fallback guidance: "For the most current and accurate provider count, please consult the official Minnesota DHS Provider Directory or contact Minnesota DHS directly."
```

**Query Type Classification**:
- Automatically detects provider count queries: "How many providers...", "Total number of...", etc.
- Enhanced pattern matching for better classification
- Appropriate response format selection

**File Locations**:
- `backend/app/services/prompt_engineering.py` (enhanced)

---

### 5. Data Refresh Scheduler

**Purpose**: Automatically refresh provider data and maintain system freshness through scheduled operations.

**Features**:
- **Scheduled Jobs**: Monthly provider refresh, weekly validation, daily cleanup
- **Manual Execution**: Run any job on-demand
- **Error Handling**: Retry logic with exponential backoff
- **Job Management**: Enable/disable jobs, view status and history

**Default Schedule**:
- **Monthly**: Provider count refresh (1st of month, 4 AM)
- **Weekly**: Data validation and freshness check (Sundays, 3 AM)  
- **Daily**: Cache cleanup and maintenance (Daily, 2 AM)

**Usage Examples**:
```python
from app.services.data_refresh_scheduler import data_refresh_scheduler

# Start the scheduler
data_refresh_scheduler.start_scheduler()

# Check job status
status = data_refresh_scheduler.get_job_status()
print(f"Scheduler running: {status['scheduler_running']}")

# Run a job manually
result = data_refresh_scheduler.run_job_manually("provider_count_refresh")

# Add custom job
def custom_validation():
    return {"status": "success", "validated": True}

data_refresh_scheduler.add_job(
    name="custom_validation",
    frequency=RefreshFrequency.WEEKLY,
    function=custom_validation
)
```

**File Locations**:
- `backend/app/services/data_refresh_scheduler.py`

---

## 🔧 Integration with Existing System

### Main Query Pipeline Enhancement

The enhanced system integrates seamlessly with the existing query pipeline:

1. **Query Reception**: Same FastAPI endpoints
2. **Enhanced Search**: Structured data is automatically included in searches
3. **Improved Prompts**: Enhanced prompt templates with fallback handling
4. **Response Generation**: Same LLM integration with better context

### Backward Compatibility

- All existing functionality remains unchanged
- Enhanced features are additive, not replacing
- Existing data and embeddings continue to work
- API endpoints maintain compatibility

### Configuration

Add to `backend/requirements.txt`:
```
pandas>=2.0.0
schedule>=1.2.0
```

Environment variables (optional):
```bash
# Structured data configuration
STRUCTURED_DATA_DIR=data/structured

# Scraper configuration  
SCRAPER_RATE_LIMIT=2  # seconds between requests
SCRAPER_MAX_RETRIES=3

# Scheduler configuration
SCHEDULER_ENABLED=true
```

---

## 📋 API Enhancements

### New Endpoints (Optional Implementation)

While the core enhancements work through existing endpoints, you can optionally add these management endpoints:

```python
# Provider data management
@app.get("/admin/provider-stats")
async def get_provider_stats():
    return get_provider_statistics()

@app.post("/admin/refresh-provider-data") 
async def refresh_provider_data():
    return data_refresh_scheduler.run_job_manually("provider_count_refresh")

# Structured data management
@app.get("/admin/structured-data")
async def get_structured_data():
    service = StructuredDataService()
    return service.get_summary()

# Scheduler management
@app.get("/admin/scheduler-status")
async def get_scheduler_status():
    return data_refresh_scheduler.get_job_status()
```

---

## 🧪 Testing the Enhanced System

Run the comprehensive test suite:

```bash
cd backend
python test_enhanced_system.py
```

The test suite validates:
- ✅ Structured data service functionality
- ✅ Provider directory scraper (network permitting)
- ✅ Enhanced vector search integration
- ✅ Improved prompt engineering
- ✅ Data refresh scheduler operations
- ✅ End-to-end system integration

---

## 📈 Expected Improvements

### Query Response Quality

**Before Enhancement**:
```
User: "How many EIDBI providers are there in Minnesota?"
System: "I'm sorry, but the context you provided does not contain information about the Minnesota EIDBI program."
```

**After Enhancement**:
```
User: "How many EIDBI providers are there in Minnesota?"
System: "Based on the most recent data, there are 75 EIDBI providers in Minnesota. This includes providers across multiple counties, with the highest concentrations in Hennepin (25 providers) and Ramsey (20 providers) counties. 

For the most current and accurate provider count, please consult the official Minnesota DHS Provider Directory at https://www.dhs.state.mn.us/"
```

### Search Coverage

- **Increased Results**: 15 results instead of 5 for better information coverage
- **Structured Data Priority**: Exact facts surfaced before general documents
- **Better Context**: More relevant information in prompts

### Data Freshness

- **Automated Updates**: Monthly provider data refresh
- **Validation**: Weekly data freshness checks
- **Maintenance**: Daily cache cleanup and optimization

---

## 🔄 Deployment Considerations

### Local Development

1. Install enhanced requirements:
   ```bash
   pip install pandas>=2.0.0 schedule>=1.2.0
   ```

2. Create data directory:
   ```bash
   mkdir -p data/structured
   ```

3. Run test suite to validate:
   ```bash
   python backend/test_enhanced_system.py
   ```

### Production Deployment

1. **Add Dependencies**: Update Docker containers with new requirements
2. **Data Persistence**: Ensure `data/structured` directory is persistent
3. **Scheduler Setup**: Start scheduler in production environment
4. **Monitoring**: Monitor scheduler job status and success rates

### Cloud Deployment Integration

The enhanced system is designed to work with the existing Google Cloud Run deployment:

- Structured data persists in mounted volumes or Cloud Storage
- Scheduler runs as background thread in the main container
- Provider scraping respects rate limits and robots.txt
- All enhancements are backward compatible

---

## 📞 Support and Maintenance

### Monitoring

- **Job Status**: Check scheduler status via admin endpoints
- **Data Freshness**: Weekly validation reports stale data
- **Error Handling**: Comprehensive logging for troubleshooting

### Manual Operations

```python
# Force provider data refresh
data_refresh_scheduler.run_job_manually("provider_count_refresh")

# Validate data freshness
data_refresh_scheduler.run_job_manually("data_validation")

# Clear caches
data_refresh_scheduler.run_job_manually("cache_cleanup")
```

### Troubleshooting

Common issues and solutions:

1. **Scraper Fails**: Check network connectivity and robots.txt compliance
2. **Scheduler Not Running**: Verify `start_scheduler()` called in main application
3. **Structured Data Missing**: Check data directory permissions and file paths
4. **Search Results Changed**: Expected behavior due to increased coverage and structured data integration

---

## 🎯 Future Enhancements

Potential future improvements:

1. **Multi-Source Integration**: Additional provider directories
2. **Real-Time Updates**: WebSocket integration for live data updates  
3. **Analytics Dashboard**: Visual monitoring of data freshness and usage
4. **Machine Learning**: Predictive models for provider availability
5. **Geographic Search**: Location-based provider recommendations

---

## 📝 Summary

The Enhanced EIDBI Query System now provides:

✅ **Structured Data Management** - Handle exact facts and statistics  
✅ **Automated Provider Scraping** - Keep provider data current  
✅ **Enhanced Search Coverage** - Better information retrieval  
✅ **Intelligent Fallback Responses** - Graceful handling of missing data  
✅ **Automated Maintenance** - Self-maintaining data freshness  
✅ **Comprehensive Testing** - Validated system reliability  

These enhancements transform the system from basic document search to a comprehensive, self-maintaining information system that provides accurate, current data about Minnesota EIDBI programs while gracefully handling edge cases and data limitations. 