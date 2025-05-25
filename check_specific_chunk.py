#!/usr/bin/env python3
"""
Check why the EIDBI definition chunk isn't being retrieved
"""

import json
import hashlib
import numpy as np

def generate_mock_embedding(text):
    """Generate the same mock embedding as the backend"""
    # Use SHA-256 hash of the text
    hash_obj = hashlib.sha256(text.encode('utf-8'))
    hash_bytes = hash_obj.digest()
    
    # Convert bytes to floats in range [-1, 1]
    embedding = []
    for i in range(0, len(hash_bytes), 4):
        # Get 4 bytes and convert to float
        if i + 4 <= len(hash_bytes):
            value = int.from_bytes(hash_bytes[i:i+4], byteorder='big')
            # Normalize to [-1, 1]
            normalized = (value / (2**32 - 1)) * 2 - 1
            embedding.append(normalized)
    
    # Pad or truncate to 768 dimensions
    while len(embedding) < 768:
        embedding.extend(embedding[:min(768 - len(embedding), len(embedding))])
    
    return embedding[:768]

def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return np.dot(a, b) / (a_norm * b_norm)

def main():
    # Load chunks
    chunks = []
    with open('backend/local_scraped_data_with_embeddings.jsonl', 'r') as f:
        for line in f:
            chunks.append(json.loads(line))
    
    # Find the EIDBI definition chunk
    eidbi_def_chunk = None
    for chunk in chunks:
        if 'benefit is a Minnesota Health Care Program' in chunk.get('content', ''):
            eidbi_def_chunk = chunk
            break
    
    if not eidbi_def_chunk:
        print("EIDBI definition chunk not found!")
        return
    
    print(f"Found EIDBI definition chunk: {eidbi_def_chunk['id']}")
    print(f"Content preview: {eidbi_def_chunk['content'][:200]}...")
    
    # Generate embeddings for test queries
    queries = [
        "What is EIDBI?",
        "EIDBI definition",
        "Early Intensive Developmental and Behavioral Intervention",
        "EIDBI benefit Minnesota Health Care Program",
        "What does EIDBI stand for?"
    ]
    
    print("\nChecking similarity scores for different queries:")
    print("=" * 60)
    
    for query in queries:
        query_embedding = generate_mock_embedding(query)
        
        # Calculate similarity with definition chunk
        chunk_embedding = eidbi_def_chunk['embedding']
        similarity = cosine_similarity(query_embedding, chunk_embedding)
        
        print(f"\nQuery: '{query}'")
        print(f"Similarity with definition chunk: {similarity:.4f}")
        
        # Find rank among all chunks
        similarities = []
        for chunk in chunks:
            if 'embedding' in chunk and chunk['embedding']:
                sim = cosine_similarity(query_embedding, chunk['embedding'])
                similarities.append((chunk['id'], sim))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Find rank of definition chunk
        rank = None
        for i, (chunk_id, _) in enumerate(similarities):
            if chunk_id == eidbi_def_chunk['id']:
                rank = i + 1
                break
        
        print(f"Definition chunk rank: {rank} out of {len(similarities)}")
        print(f"Top 3 retrieved chunks:")
        for i in range(min(3, len(similarities))):
            chunk_id, sim = similarities[i]
            # Find chunk content
            for c in chunks:
                if c['id'] == chunk_id:
                    content_preview = c['content'][:100].replace('\n', ' ')
                    print(f"  {i+1}. {chunk_id} (similarity: {sim:.4f})")
                    print(f"     Content: {content_preview}...")
                    break

if __name__ == "__main__":
    main() 