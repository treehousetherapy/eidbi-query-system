import json
import os
import numpy as np
from typing import List, Dict, Any

# Path to the scraped data file
SCRAPED_DATA_PATH = os.path.join('scraper', 'local_scraped_data_20250413_141447.jsonl')

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate the cosine similarity between two vectors."""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return np.dot(a, b) / (a_norm * b_norm)

def load_data() -> List[Dict[str, Any]]:
    """Load the scraped data from the JSONL file."""
    data = []
    with open(SCRAPED_DATA_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                chunk = json.loads(line)
                data.append(chunk)
            except json.JSONDecodeError:
                print(f"Error decoding JSON line: {line[:50]}...")
    print(f"Loaded {len(data)} chunks from {SCRAPED_DATA_PATH}")
    return data

def generate_mock_embedding(text: str) -> List[float]:
    """
    Generate a mock embedding for the given text.
    In a real system, this would use the same embedding model as the scraper.
    """
    # Use a simple hash-based approach to create a deterministic embedding
    # This is just for demonstration - not a real embedding
    import hashlib
    
    # Convert text to bytes and hash it
    hash_obj = hashlib.sha256(text.encode('utf-8'))
    hash_bytes = hash_obj.digest()
    
    # Convert hash bytes to a list of 768 float values between -1 and 1
    embedding = []
    for i in range(768):
        byte_idx = i % 32
        value = (hash_bytes[byte_idx] / 128.0) - 1.0
        embedding.append(value)
    
    # Normalize the vector
    embedding_np = np.array(embedding)
    norm = np.linalg.norm(embedding_np)
    if norm > 0:
        embedding_np = embedding_np / norm
    
    return embedding_np.tolist()

def search(query: str, data: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Search the data for chunks most similar to the query.
    
    Args:
        query: The search query text
        data: The data to search (list of chunks with embeddings)
        top_k: Number of most similar chunks to return
        
    Returns:
        List of the most similar chunks with similarity score
    """
    # Generate embedding for the query
    query_embedding = generate_mock_embedding(query)
    
    # Calculate similarity with each chunk
    results = []
    for chunk in data:
        if 'embedding' not in chunk:
            continue
            
        similarity = cosine_similarity(query_embedding, chunk['embedding'])
        
        results.append({
            'chunk': chunk,
            'similarity': similarity
        })
    
    # Sort by similarity (highest first) and take top_k
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results[:top_k]

def format_result(result: Dict[str, Any]) -> str:
    """Format a search result for display."""
    chunk = result['chunk']
    similarity = result['similarity']
    
    return f"""
Score: {similarity:.4f}
URL: {chunk.get('metadata', {}).get('url', 'No URL')}
Title: {chunk.get('metadata', {}).get('title', 'No Title')}
Content: {chunk.get('content', '')[:200]}...
""".strip()

def main():
    """Main function to demonstrate searching the scraped data."""
    print("Loading data...")
    data = load_data()
    
    while True:
        query = input("\nEnter your query (or 'exit' to quit): ")
        if query.lower() in ('exit', 'quit', 'q'):
            break
            
        print(f"\nSearching for: {query}")
        results = search(query, data)
        
        if not results:
            print("No results found.")
            continue
            
        print("\nTop results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {format_result(result)}")
            
        print("\n" + "="*50)

if __name__ == "__main__":
    main() 