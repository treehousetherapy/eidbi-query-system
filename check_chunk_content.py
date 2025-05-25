#!/usr/bin/env python3
"""
Check the content of specific chunks by ID
"""

import json
import sys

def find_chunk_by_id(chunk_id, file_path):
    """Find a chunk by its ID in the JSONL file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                chunk = json.loads(line)
                if chunk.get('id') == chunk_id:
                    return chunk
            except:
                continue
    return None

def main():
    # The chunk IDs from the log
    chunk_ids = [
        '2f9f79b6-9413-4a86-a0f5-ca57fbabe4c5',
        '0be6482b-3da1-49d9-a729-43aaea27911f',
        'd445242c-545a-404b-94bb-cc7eefd462f3'
    ]
    
    file_path = 'backend/local_scraped_data_with_embeddings.jsonl'
    
    print("Checking content of chunks retrieved for 'What is EIDBI?' query:")
    print("="*80)
    
    for i, chunk_id in enumerate(chunk_ids, 1):
        print(f"\nChunk {i} (ID: {chunk_id}):")
        print("-"*40)
        
        chunk = find_chunk_by_id(chunk_id, file_path)
        if chunk:
            content = chunk.get('content', 'No content')
            print(f"Content (first 500 chars):")
            print(content[:500] + "..." if len(content) > 500 else content)
        else:
            print("Chunk not found in file")

if __name__ == "__main__":
    main() 