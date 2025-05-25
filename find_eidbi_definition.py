#!/usr/bin/env python3
"""Find the chunk containing the EIDBI definition"""

import json

with open('backend/local_scraped_data_with_embeddings.jsonl', 'r') as f:
    for i, line in enumerate(f):
        chunk = json.loads(line)
        content = chunk.get('content', '')
        if 'benefit is a Minnesota Health Care Program' in content and 'EIDBI' in content:
            print(f"Found EIDBI definition in chunk:")
            print(f"Chunk ID: {chunk['id']}")
            print(f"Content preview: {content[:200]}...")
            break 