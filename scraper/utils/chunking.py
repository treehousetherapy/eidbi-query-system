import logging
import uuid
from typing import List, Dict, Any

# Default values - consider moving these to config/settings.py if they need to be configurable
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP = 200

logger = logging.getLogger(__name__)

def find_split_point(text: str, target_pos: int, max_len: int) -> int:
    """
    Finds the nearest whitespace boundary before the target position.
    Falls back to splitting at target_pos if no space is found nearby.
    """
    if target_pos >= max_len:
        return max_len

    # Search backward from the target position for whitespace
    split_pos = text.rfind(' ', max(0, target_pos - 50), target_pos + 1) # Search in a small window around the target

    if split_pos != -1 and split_pos > max(0, target_pos - (DEFAULT_CHUNK_SIZE // 2)) : # Ensure the found space isn't too far back
       return split_pos + 1 # Split after the space
    else:
        # If no suitable space found nearby, just split at the target position
        # In a more complex scenario, you might search for sentence boundaries ('.', '!', '?')
        # or split mid-word if absolutely necessary.
        return target_pos


def chunk_text(
    text: str,
    url: str,
    title: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP
) -> List[Dict[str, Any]]:
    """
    Splits text into overlapping chunks based on character count, trying to respect word boundaries.

    Args:
        text: The input text to chunk.
        url: The source URL of the text.
        title: The title associated with the text.
        chunk_size: The target maximum size of each chunk (in characters).
        overlap: The number of characters to overlap between consecutive chunks.

    Returns:
        A list of dictionaries, where each dictionary represents a chunk
        with 'id', 'content', and 'metadata'.
    """
    logger.info(f"Starting chunking for URL: {url} (Title: {title})")

    if not text:
        logger.warning(f"No text provided for chunking (URL: {url}). Returning empty list.")
        return []

    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    chunks: List[Dict[str, Any]] = []
    doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url)) # Generate a consistent ID based on URL
    text_len = len(text)
    current_pos = 0

    while current_pos < text_len:
        start_char = current_pos
        target_end_pos = current_pos + chunk_size

        # Find the best position to end the chunk, trying not to break words
        end_char = find_split_point(text, target_end_pos, text_len)

        # Ensure we don't create an empty chunk if split point is same as start
        if end_char <= start_char:
             # If stuck, force advance by chunk_size or to end of text
             end_char = min(start_char + chunk_size, text_len)


        chunk_content = text[start_char:end_char].strip()

        # Only add non-empty chunks
        if chunk_content:
            chunk_id = str(uuid.uuid4())
            chunk_data = {
                "id": chunk_id,
                "content": chunk_content,
                "metadata": {
                    "url": url,
                    "title": title,
                    "doc_id": doc_id,
                    "start_char": start_char,
                    "end_char": end_char,
                }
            }
            chunks.append(chunk_data)
            # logger.debug(f"Created chunk {chunk_id}: Start={start_char}, End={end_char}, Length={len(chunk_content)}")

        # Determine the starting position for the next chunk
        next_start_pos = current_pos + chunk_size - overlap

        # If the found split point was much earlier than target, adjust next start to avoid excessive overlap or getting stuck
        if end_char < target_end_pos - overlap:
             next_start_pos = end_char - overlap

        # Ensure we always move forward
        current_pos = max(end_char - overlap, start_char + 1) if end_char < text_len else text_len
        # Safety break to prevent infinite loops if logic fails to advance
        if current_pos <= start_char and current_pos < text_len:
             logger.warning(f"Chunking stuck at position {current_pos} for URL {url}. Forcing advance.")
             current_pos = start_char + 1 # Force minimal advance


    logger.info(f"Finished chunking for URL: {url}. Generated {len(chunks)} chunks.")
    return chunks

# --- Example Usage (for testing) ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sample_text = """This is the first sentence. It is relatively short.
This is the second sentence, and it's a bit longer to demonstrate chunking. We want to see how it handles overlaps and tries to split at spaces.
Here comes the third sentence. Maybe this one will cross a chunk boundary. Let's add more words to make sure it's long enough to potentially be split. We need more content here to test the overlap functionality properly. This sentence keeps going and going.
Finally, the fourth sentence provides a concluding point. This should also be included in the chunks. What happens with very short final text?
""" * 10 # Make it longer for testing

    sample_url = "http://example.com/sample"
    sample_title = "Sample Document Title"

    # Override defaults for testing
    test_chunk_size = 150
    test_overlap = 30

    generated_chunks = chunk_text(
        sample_text,
        sample_url,
        sample_title,
        chunk_size=test_chunk_size,
        overlap=test_overlap
    )

    print(f"\n--- Generated {len(generated_chunks)} Chunks ---")
    for i, chunk in enumerate(generated_chunks):
        print(f"\nChunk {i+1} (ID: {chunk['id']})")
        print(f"Metadata: {chunk['metadata']}")
        print(f"Content:\n{chunk['content']}")
        print("-" * 20)

    # Verification (Optional): Check overlap and boundaries
    if len(generated_chunks) > 1:
        first_chunk = generated_chunks[0]
        second_chunk = generated_chunks[1]
        overlap_start = second_chunk['metadata']['start_char']
        overlap_end = first_chunk['metadata']['end_char']
        actual_overlap_content = sample_text[overlap_start:overlap_end]
        print(f"\nExpected Overlap Length: {test_overlap}")
        print(f"Actual Overlap Length: {len(actual_overlap_content)}")
        # print(f"Overlap Content:\n{actual_overlap_content}") 