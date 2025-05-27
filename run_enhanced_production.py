#!/usr/bin/env python3
"""
Enhanced EIDBI Production Deployment Script

This script initializes and starts the enhanced EIDBI system with all
enhanced capabilities including structured data, provider scraping,
enhanced search, improved prompts, and data refresh scheduling.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

def setup_logging():
    """Set up comprehensive logging for the enhanced system"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',
        handlers=[
            logging.FileHandler('logs/enhanced_system.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Enhanced EIDBI System - Logging initialized")
    return logger

def initialize_enhanced_services():
    """Initialize all enhanced services"""
    logger = logging.getLogger(__name__)
    
    try:
        # Import enhanced services
        logger.info("Initializing enhanced services...")
        
        from app.services.structured_data_service import StructuredDataService
        from app.services.provider_scraper import ProviderDirectoryScraper
        from app.services.data_refresh_scheduler import data_refresh_scheduler
        from app.services.vector_db_service import get_structured_data_service
        
        # Initialize structured data service
        logger.info("Setting up structured data service...")
        structured_service = StructuredDataService()
        logger.info(f"Structured data service initialized with {len(structured_service.structured_data)} entries")
        
        # Initialize provider scraper
        logger.info("Setting up provider directory scraper...")
        provider_scraper = ProviderDirectoryScraper()
        logger.info("Provider scraper initialized successfully")
        
        # Initialize and start data refresh scheduler
        logger.info("Starting data refresh scheduler...")
        data_refresh_scheduler.start_scheduler()
        
        # Get scheduler status
        scheduler_status = data_refresh_scheduler.get_job_status()
        logger.info(f"Scheduler running: {scheduler_status['scheduler_running']}")
        logger.info(f"Configured jobs: {list(scheduler_status['jobs'].keys())}")
        
        logger.info("✅ All enhanced services initialized successfully!")
        
        return {
            'structured_data_service': structured_service,
            'provider_scraper': provider_scraper,
            'scheduler': data_refresh_scheduler,
            'scheduler_status': scheduler_status
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize enhanced services: {e}")
        raise

def run_system_tests():
    """Run basic system tests to ensure everything is working"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Running enhanced system validation tests...")
        
        # Test structured data
        from app.services.structured_data_service import StructuredDataService
        service = StructuredDataService()
        test_results = service.get_summary()
        logger.info(f"✅ Structured data test passed: {test_results}")
        
        # Test vector database integration
        from app.services.vector_db_service import search_structured_data
        structured_results = search_structured_data(["test"])
        logger.info(f"✅ Vector database integration test passed: {len(structured_results)} results")
        
        # Test prompt engineering
        from app.services.prompt_engineering import PromptEngineeringService
        prompt_service = PromptEngineeringService()
        query_type = prompt_service.classify_query_type("How many EIDBI providers are there?")
        logger.info(f"✅ Prompt engineering test passed: query classified as {query_type.value}")
        
        logger.info("✅ All system tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ System tests failed: {e}")
        return False

def start_enhanced_application():
    """Start the enhanced FastAPI application"""
    logger = logging.getLogger(__name__)
    
    try:
        import uvicorn
        from main import app
        
        # Configure application settings
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 8080))
        
        logger.info(f"🚀 Starting Enhanced EIDBI System on {host}:{port}")
        logger.info("Enhanced capabilities include:")
        logger.info("  📊 Structured data ingestion and management")
        logger.info("  🕷️ Automated provider directory scraping")
        logger.info("  🔍 Enhanced vector search with improved coverage")
        logger.info("  📝 Intelligent prompt engineering with fallback handling")
        logger.info("  ⏰ Automated data refresh scheduling")
        
        # Start the application
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        raise

def main():
    """Main deployment function"""
    print("🚀 Enhanced EIDBI System - Production Deployment")
    print("=" * 80)
    
    # Setup logging
    logger = setup_logging()
    
    try:
        # Initialize enhanced services
        services = initialize_enhanced_services()
        
        # Run system tests
        if not run_system_tests():
            logger.error("System tests failed! Please check the logs.")
            sys.exit(1)
        
        # Start the application
        start_enhanced_application()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
        
        # Graceful shutdown
        try:
            from app.services.data_refresh_scheduler import data_refresh_scheduler
            data_refresh_scheduler.stop_scheduler()
            logger.info("✅ Data refresh scheduler stopped")
        except:
            pass
        
        logger.info("✅ Enhanced EIDBI System shutdown complete")
        
    except Exception as e:
        logger.error(f"❌ Critical error in enhanced system: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 