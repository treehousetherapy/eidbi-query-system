#!/usr/bin/env python3
"""
Enhanced Data Integration Script

This script integrates the enhanced scraper data into the main EIDBI system's vector database.
It combines the enhanced data with existing data and creates a unified dataset.
"""

import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_jsonl_file(file_path: str) -> List[Dict[str, Any]]:
    """Load chunks from a JSONL file"""
    chunks = []
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return chunks
    
    try:
        logger.info(f"Loading chunks from: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        chunk = json.loads(line)
                        if 'id' in chunk and 'embedding' in chunk and 'content' in chunk:
                            chunks.append(chunk)
                        else:
                            logger.warning(f"Skipping line {line_num}: missing required fields")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Skipping line {line_num}: JSON decode error: {e}")
        
        logger.info(f"Successfully loaded {len(chunks)} chunks from {file_path}")
        return chunks
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {e}")
        return []

def save_jsonl_file(chunks: List[Dict[str, Any]], file_path: str) -> bool:
    """Save chunks to a JSONL file"""
    try:
        logger.info(f"Saving {len(chunks)} chunks to: {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
        
        logger.info(f"Successfully saved {len(chunks)} chunks to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving file {file_path}: {e}")
        return False

def get_existing_data_files() -> List[str]:
    """Find existing data files in the system"""
    possible_files = [
        # In scraper directory
        'scraper/local_scraped_data_with_embeddings.jsonl',
        'scraper/local_scraped_data_with_embeddings_20250511_152056.jsonl',
        'scraper/local_scraped_data_with_embeddings_20250511_154715.jsonl',
        # In project root
        'local_scraped_data_with_embeddings.jsonl',
        'local_scraped_data_with_embeddings_20250511_152056.jsonl',
    ]
    
    existing_files = []
    for file_path in possible_files:
        if os.path.exists(file_path):
            existing_files.append(file_path)
            logger.info(f"Found existing data file: {file_path}")
    
    return existing_files

def get_enhanced_data_files() -> List[str]:
    """Find enhanced data files"""
    enhanced_files = []
    
    # Look for the combined enhanced data file first
    combined_file = "enhanced_eidbi_data_combined_20250525_200458.jsonl"
    if os.path.exists(combined_file):
        enhanced_files.append(combined_file)
        logger.info(f"Found enhanced combined data file: {combined_file}")
        return enhanced_files
    
    # Look for individual enhanced data files
    possible_patterns = [
        "enhanced_eidbi_data_*.jsonl",
        "scraper/enhanced_eidbi_data_*.jsonl"
    ]
    
    import glob
    for pattern in possible_patterns:
        files = glob.glob(pattern)
        for file_path in files:
            if os.path.exists(file_path):
                enhanced_files.append(file_path)
                logger.info(f"Found enhanced data file: {file_path}")
    
    return enhanced_files

def remove_duplicates(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate chunks based on content hash"""
    seen_hashes = set()
    unique_chunks = []
    
    for chunk in chunks:
        # Create a hash of the content to detect duplicates
        content = chunk.get('content', '')
        url = chunk.get('metadata', {}).get('url', chunk.get('url', ''))
        
        # Simple deduplication based on content + URL
        hash_key = hash(content + url)
        
        if hash_key not in seen_hashes:
            seen_hashes.add(hash_key)
            unique_chunks.append(chunk)
        else:
            logger.debug(f"Removing duplicate chunk: {chunk.get('id', 'unknown')}")
    
    removed_count = len(chunks) - len(unique_chunks)
    if removed_count > 0:
        logger.info(f"Removed {removed_count} duplicate chunks")
    
    return unique_chunks

def integrate_enhanced_data():
    """Main function to integrate enhanced data with existing data"""
    logger.info("🚀 Starting Enhanced Data Integration")
    logger.info("=" * 60)
    
    # Find existing data files
    existing_files = get_existing_data_files()
    enhanced_files = get_enhanced_data_files()
    
    if not enhanced_files:
        logger.error("❌ No enhanced data files found!")
        logger.info("Please run the enhanced scraper first to generate data.")
        return False
    
    # Load existing data
    all_existing_chunks = []
    for file_path in existing_files:
        chunks = load_jsonl_file(file_path)
        all_existing_chunks.extend(chunks)
    
    logger.info(f"📊 Loaded {len(all_existing_chunks)} existing chunks from {len(existing_files)} files")
    
    # Load enhanced data
    all_enhanced_chunks = []
    for file_path in enhanced_files:
        chunks = load_jsonl_file(file_path)
        all_enhanced_chunks.extend(chunks)
    
    logger.info(f"✨ Loaded {len(all_enhanced_chunks)} enhanced chunks from {len(enhanced_files)} files")
    
    # Combine all data
    all_chunks = all_existing_chunks + all_enhanced_chunks
    logger.info(f"🔄 Combined total: {len(all_chunks)} chunks")
    
    # Remove duplicates
    unique_chunks = remove_duplicates(all_chunks)
    logger.info(f"🎯 After deduplication: {len(unique_chunks)} unique chunks")
    
    # Create timestamp for new file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save integrated data to multiple locations for the backend to find
    output_files = [
        f"local_scraped_data_with_embeddings_integrated_{timestamp}.jsonl",
        "local_scraped_data_with_embeddings.jsonl",  # Primary file the backend looks for
    ]
    
    success_count = 0
    for output_file in output_files:
        if save_jsonl_file(unique_chunks, output_file):
            success_count += 1
    
    if success_count > 0:
        logger.info("✅ Enhanced data integration completed successfully!")
        logger.info(f"📁 Integrated data saved to {success_count} files")
        logger.info(f"📊 Final dataset contains:")
        logger.info(f"  • Total chunks: {len(unique_chunks)}")
        logger.info(f"  • Original chunks: {len(all_existing_chunks)}")
        logger.info(f"  • Enhanced chunks: {len(all_enhanced_chunks)}")
        logger.info(f"  • Removed duplicates: {len(all_chunks) - len(unique_chunks)}")
        
        # Analyze data sources in the integrated dataset
        source_types = set()
        doc_types = set()
        for chunk in unique_chunks:
            source_metadata = chunk.get('source_metadata', {})
            if 'source_type' in source_metadata:
                source_types.add(source_metadata['source_type'])
            if 'document_type' in source_metadata:
                doc_types.add(source_metadata['document_type'])
        
        if source_types:
            logger.info(f"  • Source types: {sorted(source_types)}")
        if doc_types:
            logger.info(f"  • Document types: {sorted(doc_types)}")
        
        logger.info("\n🎉 The EIDBI system now has access to enhanced data!")
        logger.info("Users should now get comprehensive responses about EIDBI programs.")
        
        return True
    else:
        logger.error("❌ Failed to save integrated data")
        return False

def main():
    """Main entry point"""
    success = integrate_enhanced_data()
    
    if success:
        logger.info("\n" + "=" * 60)
        logger.info("📋 Next Steps:")
        logger.info("1. Restart the EIDBI backend to load the new integrated data")
        logger.info("2. Test queries about EIDBI to verify enhanced responses")
        logger.info("3. Monitor system performance with the expanded dataset")
    else:
        logger.error("Integration failed. Please check the logs and try again.")
    
    return success

if __name__ == "__main__":
    main() 