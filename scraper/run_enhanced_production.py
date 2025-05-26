#!/usr/bin/env python3
"""
Production run of Enhanced EIDBI Scraper
Designed for safe deployment with reasonable limits
"""

import logging
import os
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler(f'enhanced_scraper_production_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_enhanced_scraper_production():
    """Run the enhanced scraper in production mode with reasonable limits"""
    print("🚀 Starting Enhanced EIDBI Scraper - Production Mode")
    print("=" * 70)
    
    # Configure for production use
    os.environ["USE_MOCK_EMBEDDINGS"] = "false"  # Try real embeddings first
    
    try:
        from enhanced_scraper import EnhancedEIDBI_Scraper
        from utils.vertex_ai_utils import initialize_vertex_ai_once
        
        print("\n📋 Configuration:")
        print(f"  • Use Mock Embeddings: {os.getenv('USE_MOCK_EMBEDDINGS', 'false')}")
        print(f"  • Max Documents per Source: 15")
        print(f"  • Target: 5 data sources")
        
        # Test Vertex AI initialization
        print("\n🧠 Testing Vertex AI initialization...")
        if initialize_vertex_ai_once():
            print("✅ Vertex AI initialized successfully")
        else:
            print("⚠️ Vertex AI initialization failed, will use mock embeddings")
        
        # Initialize scraper
        print("\n🕷️ Initializing enhanced scraper...")
        scraper = EnhancedEIDBI_Scraper()
        print(f"✅ Scraper initialized with {len(scraper.data_sources)} data sources:")
        
        for i, source in enumerate(scraper.data_sources, 1):
            print(f"  {i}. {source.name} ({source.source_type.value})")
            print(f"     Rate limit: {source.rate_limit_per_minute}/min")
        
        # Run comprehensive scraping with production limits
        print(f"\n🔄 Starting comprehensive scraping (max 15 docs per source)...")
        print("This may take 10-20 minutes depending on response times...")
        
        start_time = datetime.now()
        results = scraper.run_comprehensive_scrape(max_docs_per_source=15)
        end_time = datetime.now()
        
        duration = end_time - start_time
        
        if results:
            print(f"\n✅ Enhanced scraping completed successfully!")
            print(f"⏱️ Duration: {duration}")
            print(f"📊 Results:")
            print(f"  • Total chunks collected: {len(results)}")
            
            unique_sources = len(set(chunk['source_metadata']['url'] for chunk in results))
            print(f"  • Unique documents: {unique_sources}")
            
            doc_types = set(chunk['source_metadata']['document_type'].value for chunk in results)
            print(f"  • Document types: {doc_types}")
            
            source_types = set(chunk['source_metadata']['source_type'].value for chunk in results)
            print(f"  • Source types: {source_types}")
            
            # Check embedding types
            sample_chunk = results[0]
            if 'embedding' in sample_chunk:
                print(f"  • Embedding dimension: {len(sample_chunk['embedding'])}")
                embedding_type = "Real Vertex AI" if not os.getenv("USE_MOCK_EMBEDDINGS", "false").lower() == "true" else "Mock"
                print(f"  • Embedding type: {embedding_type}")
            
            print(f"\n📁 Output files available in current directory")
            return True
        else:
            print(f"\n❌ No data was collected. Duration: {duration}")
            print("Check logs for specific errors.")
            return False
            
    except KeyboardInterrupt:
        print(f"\n⏹️ Scraping interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Production run failed: {e}")
        logger.error("Production run failed", exc_info=True)
        return False

def main():
    success = run_enhanced_scraper_production()
    
    print("\n" + "=" * 70)
    if success:
        print("🎉 Enhanced EIDBI scraper deployment successful!")
        print("\n📋 Next steps:")
        print("1. Review the generated .jsonl files")
        print("2. Check the summary .json files for statistics")
        print("3. Integrate with the existing EIDBI system")
        print("4. Set up regular scraping schedule if desired")
    else:
        print("⚠️ Enhanced scraper encountered issues.")
        print("Check the log files for details.")
    
    return success

if __name__ == "__main__":
    main() 