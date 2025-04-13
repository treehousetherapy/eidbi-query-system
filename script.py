def fetch_html_content(url: str, timeout: int = 10) -> str | None:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f'Error fetching {url}: {str(e)}')
        return None
def parse_html_content(html_content: str) -> str | None:
    if not html_content:
        return None
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Try common content areas
        content_area = soup.find(['main', 'article', 'div'], id='content')
        if not content_area:
            content_area = soup  # fallback to entire document
        # Get all text, normalize whitespace
        text = ' '.join(content_area.get_text(separator=' ').split())
        return text
    except Exception as e:
        print(f'Error parsing HTML content: {str(e)}')
        return None
def clean_text(text: str) -> str:
    # Remove leading/trailing whitespace and normalize internal spaces
    return ' '.join(text.strip().split())
def chunk_text(text: str, url: str, title: str, chunk_size: int = 1000, overlap: int = 200) -> list[dict]:
    chunks = []
    doc_id = str(uuid.uuid4())
    start = 0
    while start < len(text):
        # Find end of chunk, trying not to break words
        end = start + chunk_size
        if end < len(text):
            # Extend to end of last word
            while end < len(text) and not text[end].isspace():
                end += 1
        chunk = {
            'id': str(uuid.uuid4()),
            'content': text[start:end],
            'metadata': {
                'url': url,
                'title': title,
                'doc_id': doc_id,
                'start_char': start,
                'end_char': end
            }
        }
        chunks.append(chunk)
        # Move start position accounting for overlap
        start = end - overlap
        # Ensure we don't break words on overlap
        while start > 0 and not text[start].isspace():
            start += 1
    return chunks
def upload_to_gcs(data: dict, bucket_name: str, blob_name: str) -> bool:
    try:
        storage_client = Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        # Convert dict to JSON string
        json_data = json.dumps(data)
        # Upload to GCS
        blob.upload_from_string(json_data, content_type='application/json')
        return True
    except Exception as e:
        print(f'Error uploading to GCS: {str(e)}')
        return False
