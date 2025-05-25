#!/usr/bin/env python3
"""
Inspect the content of chunks retrieved for a query
"""

import requests
import json
import sys

BACKEND_URL = "https://eidbi-backend-service-5geiseeama-uc.a.run.app"

def get_chunk_content(chunk_id):
    """Retrieve the content of a specific chunk"""
    # Read the local scraped data file
    import os
    
    # Try different paths
    possible_paths = [
        'backend/local_scraped_data_with_embeddings_20250511_154715.jsonl',
        'scraper/local_scraped_data_with_embeddings_20250511_154715.jsonl'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        chunk = json.loads(line)
                        if chunk.get('id') == chunk_id:
                            return chunk
                    except:
                        continue
    return None

def inspect_query(query_text):
    """Query the backend and inspect the retrieved chunks"""
    print(f"\nQuery: '{query_text}'")
    print("="*80)
    
    # Query the backend
    url = f"{BACKEND_URL}/query"
    data = {
        "query_text": query_text,
        "num_results": 5
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            
            print(f"\nBackend Answer:")
            print("-"*40)
            print(result['answer'])
            
            print(f"\n\nRetrieved {len(result['retrieved_chunk_ids'])} chunks:")
            print("-"*40)
            
            # Inspect each chunk
            for i, chunk_id in enumerate(result['retrieved_chunk_ids'], 1):
                print(f"\n--- Chunk {i} (ID: {chunk_id}) ---")
                chunk = get_chunk_content(chunk_id)
                if chunk:
                    print(f"URL: {chunk.get('url', 'N/A')}")
                    print(f"Title: {chunk.get('title', 'N/A')}")
                    print(f"Content preview:")
                    content = chunk.get('content', 'No content')
                    # Show first 500 characters
                    print(content[:500] + "..." if len(content) > 500 else content)
                else:
                    print("Could not retrieve chunk content locally")
                print()
        else:
            print(f"Query failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        inspect_query(query)
    else:
        # Default queries to inspect
        queries = [
            "What is EIDBI?",
            "EIDBI definition",
            "Early Intensive Developmental and Behavioral Intervention"
        ]
        
        for query in queries:
            inspect_query(query)

if __name__ == "__main__":
    main() 