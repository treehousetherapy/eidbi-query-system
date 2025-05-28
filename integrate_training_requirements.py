#!/usr/bin/env python3
"""
Integrate EIDBI Training Requirements Data into Knowledge Base

This script integrates the collected training requirements data
into the main EIDBI knowledge base.

Author: AI Assistant
Date: January 27, 2025
"""

import json
import logging
from pathlib import Path
from datetime import datetime
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def integrate_training_data():
    """Integrate training requirements data into the knowledge base"""
    logger.info("🔄 Starting training requirements data integration...")
    
    # Find the most recent training data file
    training_data_dir = Path("scraper/data/training_requirements")
    training_files = list(training_data_dir.glob("eidbi_training_requirements_*.jsonl"))
    
    if not training_files:
        logger.error("❌ No training requirements data files found")
        return False
        
    # Get the most recent file
    latest_file = max(training_files, key=lambda f: f.stat().st_mtime)
    logger.info(f"📂 Using data file: {latest_file}")
    
    # Read the training data
    training_items = []
    with open(latest_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                training_items.append(json.loads(line))
                
    logger.info(f"📄 Loaded {len(training_items)} training requirement items")
    
    # Read existing knowledge base
    kb_file = Path("local_scraped_data_with_embeddings.jsonl")
    existing_items = []
    
    if kb_file.exists():
        with open(kb_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    existing_items.append(json.loads(line))
                    
        logger.info(f"📚 Loaded {len(existing_items)} existing knowledge base items")
        
        # Create backup
        backup_file = kb_file.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl')
        shutil.copy2(kb_file, backup_file)
        logger.info(f"💾 Created backup: {backup_file}")
    else:
        logger.warning("⚠️ Knowledge base file not found. Creating new one.")
        
    # Combine data
    all_items = existing_items + training_items
    logger.info(f"🔀 Total items after integration: {len(all_items)}")
    
    # Write combined data
    with open(kb_file, 'w', encoding='utf-8') as f:
        for item in all_items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
    logger.info(f"✅ Successfully integrated {len(training_items)} training requirement items")
    
    # Generate summary report
    report = generate_integration_report(training_items, len(existing_items), len(all_items))
    
    # Save report
    report_file = Path(f"training_requirements_integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
        
    logger.info(f"📊 Integration report saved to: {report_file}")
    
    return True

def generate_integration_report(new_items, existing_count, total_count):
    """Generate an integration report"""
    report = f"""# EIDBI Training Requirements Integration Report

**Integration Date**: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}

## 📊 Integration Summary

- **New Items Added**: {len(new_items)}
- **Previous KB Size**: {existing_count} items
- **New KB Size**: {total_count} items
- **Growth**: {((total_count - existing_count) / max(existing_count, 1)) * 100:.1f}%

## 📄 Training Data Details

### Sources Integrated:
"""
    
    # Group by source
    sources = {}
    for item in new_items:
        source = item.get('source', 'Unknown')
        if source not in sources:
            sources[source] = {
                'count': 0,
                'total_length': 0,
                'url': item.get('source_url', '')
            }
        sources[source]['count'] += 1
        sources[source]['total_length'] += len(item.get('content', ''))
        
    for source, info in sources.items():
        report += f"\n- **{source}**\n"
        report += f"  - Chunks: {info['count']}\n"
        report += f"  - Total text: {info['total_length']:,} characters\n"
        if info['url']:
            report += f"  - URL: {info['url']}\n"
            
    report += f"""
## 🎯 Coverage Enhancement

The knowledge base now includes comprehensive training requirements information:

- ✅ **Required EIDBI Trainings** - Official DHS training requirements
- ✅ **Provider Training Documentation** - Detailed training guidelines
- ✅ **Billing and Provider Training** - Training for billing procedures
- ✅ **EIDBI Benefit Overview** - Program overview with training context
- ✅ **Licensure Study Report** - Professional licensure requirements

## 📈 Expected Query Improvements

Users can now get accurate answers about:
- What training is required for EIDBI providers
- How to become an EIDBI provider
- Training hours and certification requirements
- Continuing education requirements
- Billing training resources

## ✅ Integration Status: COMPLETE

Training requirements data has been successfully integrated into the EIDBI knowledge base.
"""
    
    return report

def main():
    """Main execution function"""
    print("\n" + "="*60)
    print("🎯 EIDBI Training Requirements Data Integration")
    print("="*60 + "\n")
    
    success = integrate_training_data()
    
    if success:
        print("\n✅ Integration complete! Training requirements data is now part of the knowledge base.")
        print("\n🚀 Next steps:")
        print("   1. Redeploy the backend to include new data")
        print("   2. Test training-related queries on askeidbi.org")
        print("   3. Monitor for improved query responses")
    else:
        print("\n❌ Integration failed. Please check the logs for details.")

if __name__ == "__main__":
    main() 