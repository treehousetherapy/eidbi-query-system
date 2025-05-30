# EIDBI AI Query System

**Objective:**

Develop an AI-powered application enabling users to efficiently query and retrieve detailed, accurate information regarding the Early Intensive Developmental and Behavioral Intervention (EIDBI) program from the Minnesota Department of Human Services website.

**Architecture Overview:**

This project implements a Retrieval-Augmented Generation (RAG) system using the following components:

1.  **Scraper (`scraper/`):** A Python script that fetches content from specified EIDBI program pages on the MN DHS website, parses the HTML, cleans the text, chunks it, generates vector embeddings for each chunk using Vertex AI, and stores the results (chunks + embeddings) in Google Cloud Storage (GCS).
2.  **Vector Database (Vertex AI Matching Engine):** Stores the vector embeddings of the scraped text chunks, enabling efficient semantic search.
3.  **Backend (`backend/`):** A FastAPI application that provides an API endpoint (`/query`). When queried:
    *   It generates an embedding for the user's query using Vertex AI.
    *   It searches the Vertex AI Matching Engine index for the most relevant text chunks based on semantic similarity.
    *   It retrieves the full text content of these chunks from GCS.
    *   It constructs a prompt containing the user's query and the retrieved context.
    *   It sends the prompt to a Vertex AI Large Language Model (LLM - e.g., `text-bison`) to generate a synthesized answer based *only* on the provided context.
    *   It returns the generated answer.
4.  **Frontend Options:**
    *   **Streamlit Frontend (`frontend/`):** A Streamlit application providing a simple web interface for users to input their queries and view the answers generated by the backend.
    *   **Modern Web Frontend (`web-frontend/`):** A ChatGPT-style chat interface built with HTML, Tailwind CSS, and vanilla JavaScript, offering a more modern and responsive user experience.
5.  **Google Cloud Platform (GCP):** Hosts the necessary services:
    *   Vertex AI: For embedding generation, vector search (Matching Engine), and text generation (LLM).
    *   Google Cloud Storage (GCS): To store the scraped and processed text chunks.
    *   Cloud Run: To host the backend (FastAPI) and frontend (Streamlit) applications as containerized services.
    *   Cloud Build (Optional): To automate the container build and deployment process.

**Features:**

*   Scrape EIDBI program information from the MN DHS website.
*   Process and chunk text content.
*   Generate vector embeddings for text chunks.
*   Store chunks in GCS and embeddings in Vertex AI Matching Engine.
*   Query the system using natural language.
*   Receive AI-generated answers based on the scraped EIDBI context.
*   **NEW:** Modern ChatGPT-style web interface with:
    *   Dark theme with rounded chat bubbles
    *   Typing indicators and smooth animations
    *   Message history persistence
    *   Mobile-responsive design
    *   Query expansion and reranking for better results

**Project Structure:**

```
eidbi-query-system/
├── .env                  # Local environment variables (sensitive, DO NOT COMMIT)
├── .env.example          # Template for .env file
├── .gitignore            # Specifies intentionally untracked files that Git should ignore
├── cloudbuild.yaml       # Configuration for Google Cloud Build (optional)
├── README.md             # This file
├── config/               # Shared configuration loading
│   ├── default.yaml      # Default configuration values
│   └── settings.py       # Pydantic settings management
├── backend/              # FastAPI backend application
│   ├── app/
│   │   ├── services/     # Business logic (embeddings, vector db, llm)
│   │   │   ├── embedding_service.py
│   │   │   ├── llm_service.py
│   │   │   ├── vector_db_service.py
│   │   │   ├── query_enhancer.py    # NEW: Query expansion
│   │   │   └── reranker.py          # NEW: Result reranking
│   │   └── __init__.py
│   ├── Dockerfile        # Container definition for backend
│   ├── main.py           # FastAPI app definition and endpoints
│   └── requirements.txt  # Backend Python dependencies
├── frontend/             # Streamlit frontend application
│   ├── Dockerfile        # Container definition for frontend
│   ├── requirements.txt  # Frontend Python dependencies
│   └── streamlit_app.py  # Main Streamlit application code
├── web-frontend/         # NEW: Modern web frontend
│   ├── index.html        # Main HTML with Tailwind CSS
│   ├── js/
│   │   └── chat.js       # Chat functionality
│   ├── css/              # Custom CSS (if needed)
│   ├── assets/           # Images/icons (if needed)
│   ├── server.py         # Simple Python HTTP server
│   ├── Dockerfile        # Container definition for web frontend
│   ├── nginx.conf        # Nginx configuration
│   └── README.md         # Web frontend documentation
├── scraper/              # Data scraping and processing scripts
│   ├── requirements.txt  # Scraper Python dependencies
│   ├── scraper.py        # Main scraper orchestration script
│   └── utils/            # Utility functions for scraper & backend
│       ├── chunking.py
│       ├── embedding_service.py # Note: Also used by scraper
│       ├── gcs_utils.py
│       ├── http.py
│       ├── parsing.py
│       └── vertex_ai_utils.py # Note: Also used by scraper
└── scripts/              # Helper scripts (e.g., for DB upload)
    └── upload_to_vector_db.py # Placeholder script for Vector DB batch update
```

**Setup Instructions:**

1.  **Prerequisites:**
    *   Python 3.10+
    *   `pip` (Python package installer)
    *   Git
    *   Google Cloud SDK (`gcloud` CLI) installed and initialized (`gcloud init`).
    *   A Google Cloud Platform project with billing enabled.
    *   APIs Enabled in your GCP project:
        *   Vertex AI API
        *   Cloud Storage API
        *   Cloud Build API (if using `cloudbuild.yaml`)
        *   Cloud Run API
    *   A Vertex AI Matching Engine Index and Index Endpoint created (note their IDs).

2.  **Clone Repository:**
    ```bash
    git clone <your-repository-url>
    cd eidbi-query-system
    ```

3.  **Configuration (`.env` file):**
    *   Copy the template: `cp .env.example .env` (use `copy` on Windows CMD).
    *   Edit the `.env` file in the project root (`eidbi-query-system/.env`) and fill in your actual values:
        *   `GCP_PROJECT_ID`: Your Google Cloud project ID.
        *   `GCP_BUCKET_NAME`: The name of the GCS bucket you want to use/create for storing chunks.
        *   `GCP_REGION`: The GCP region for Vertex AI services (e.g., `us-central1`). Verify service availability.
        *   `VECTOR_DB_INDEX_ID`: The ID of your pre-created Vertex AI Matching Engine Index.
        *   `VECTOR_DB_INDEX_ENDPOINT_ID`: The ID of your pre-created Vertex AI Matching Engine Index Endpoint.
    *   **Authentication:** For local development, download a service account key file with appropriate permissions (Vertex AI User, Storage Admin) and set the environment variable:
        ```bash
        # Linux/macOS/Git Bash
        export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/keyfile.json"
        # Windows CMD
        set GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your\keyfile.json"
        # Windows PowerShell
        $env:GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/keyfile.json"
        ```

4.  **Install Dependencies:** Install requirements for each component:
    ```bash
    # From project root (eidbi-query-system/)
    py -m pip install -r scraper/requirements.txt
    py -m pip install -r backend/requirements.txt
    py -m pip install -r frontend/requirements.txt
    ```
    *(Use `python3 -m pip` or `pip` if `py` is not available)*

**Running Locally:**

1.  **Run the Scraper:**
    *   **(Crucial Manual Step):** Before the first run, inspect the target MN DHS EIDBI webpages and **update the CSS selectors** in `scraper/utils/parsing.py` to accurately extract the main content.
    *   Navigate to the scraper directory: `cd scraper`
    *   Run the scraper (GCS upload defaults to `False`, local save defaults to `True`):
        ```bash
        py scraper.py
        ```
    *   This will generate embeddings (requires Vertex AI auth) and save a `.jsonl` file (e.g., `local_scraped_data_with_embeddings_....jsonl`) in the `scraper` directory.
    *   To upload to GCS (after refining parser): Set `ENABLE_GCS_UPLOAD = True` in `scraper.py` and ensure `GCP_BUCKET_NAME` is set in `.env`.

2.  **Populate the Vector Database:**
    *   The `scripts/upload_to_vector_db.py` script reads the `.jsonl` file generated by the scraper.
    *   **Note:** This script currently acts as a **placeholder**. Vertex AI Matching Engine updates are best done via batch jobs.
    *   **Recommended Process:**
        1.  Run the scraper (Step 1) with `ENABLE_GCS_UPLOAD = True` to get the `.jsonl` file containing IDs and embeddings uploaded to GCS.
        2.  Follow the [Vertex AI documentation](https://cloud.google.com/vertex-ai/docs/matching-engine/update-rebuild-index) to format the data from the `.jsonl` file into the required JSON format for batch updates.
        3.  Upload the formatted batch update file(s) to GCS.
        4.  Use the `gcloud ai indexes update` command or the Google Cloud Console to update your Matching Engine Index using the batch file(s) on GCS.
    *   *Running the placeholder script (optional):*
        ```bash
        # From project root
        py scripts/upload_to_vector_db.py scraper/local_scraped_data_with_embeddings_....jsonl
        ```
        (Replace the filename; this will just log the intent).

3.  **Run the Backend:**
    *   Ensure GCP authentication is set (e.g., `GOOGLE_APPLICATION_CREDENTIALS`).
    *   Navigate to the backend directory: `cd backend`
    *   Start the FastAPI server with Uvicorn:
        ```bash
        uvicorn main:app --reload --port 8000
        ```
    *   The server will be running on `http://127.0.0.1:8000`. Check the terminal logs for successful Vertex AI initialization during startup.

4.  **Run the Frontend (Choose one):**
    
    **Option A: Streamlit Frontend**
    *   Navigate to the frontend directory: `cd frontend`
    *   Run the Streamlit app:
        ```bash
        streamlit run streamlit_app.py
        ```
    *   Streamlit will provide a URL (usually `http://localhost:8501`) to open in your browser.
    
    **Option B: Modern Web Frontend (Recommended)**
    *   Navigate to the web-frontend directory: `cd web-frontend`
    *   Run the simple Python server:
        ```bash
        python server.py
        ```
    *   Open `http://localhost:8080` in your browser for a ChatGPT-style interface.
    *   Alternatively, use the PowerShell script: `./start_web_frontend.ps1`

**Deployment (Cloud Run via Cloud Build):**

*(Assumes you have enabled Cloud Build API and granted necessary permissions)*

1.  **Prerequisites:**
    *   Create two Cloud Run services (e.g., `eidbi-backend-service`, `eidbi-frontend-service`) in your GCP project and desired region. Configure basic settings (like CPU, memory) as needed.
    *   Ensure the Cloud Build service account (`[PROJECT_NUMBER]@cloudbuild.gserviceaccount.com`) has roles like `Cloud Run Admin` and `Storage Object Admin` (and potentially `Service Account User` if the Cloud Run services use a specific service account).
2.  **Configure `cloudbuild.yaml`:**
    *   Replace `YOUR_DEPLOYED_BACKEND_URL_HERE` in the frontend deployment step with the actual HTTPS URL provided by Cloud Run after the backend service is created/deployed.
3.  **Submit Build:** From the project root (`eidbi-query-system/`), run:
    ```bash
    gcloud builds submit --config cloudbuild.yaml .
    ```
    *(This will build the Docker images using the Dockerfiles, push them to GCR, and deploy them to the specified Cloud Run services).*
4.  **Access:** Use the URLs provided by Cloud Run for the frontend and backend services.

**Scraper Maintenance:**

*   The EIDBI information may change. Consider scheduling the scraper (`scraper.py`) to run periodically (e.g., using Google Cloud Scheduler and Cloud Functions, or a cron job on a VM) to keep the data fresh.
*   After each scrape and embedding generation, the Vector Database Index needs to be updated using the batch update process described above.

**Future Enhancements:**

*   Implement user feedback loops for answer quality.
*   Add support for multilingual queries or voice input.
*   Integrate analytics to track usage patterns and popular queries.
*   Develop personalized recommendations based on user query history.
*   Implement robust chunk content retrieval in the backend instead of just returning IDs.
*   Refine the LLM prompting for better answer synthesis.

**Cost Considerations:**

*   Google Cloud services (Vertex AI, GCS, Cloud Run) incur costs based on usage.
*   **Vertex AI:** Pricing for Embeddings API, Matching Engine (index hosting and queries), and LLM (text-bison) predictions depends on the amount of data processed/stored and requests made.
*   **GCS:** Storage costs depend on the amount of data stored and network egress.
*   **Cloud Run:** Costs depend on container instance uptime, CPU/memory usage, and requests served.
*   Refer to the official GCP pricing pages for detailed information. The estimates provided in the initial prompt ($280 - $770 monthly) are plausible but depend heavily on traffic, data volume, and specific configurations. 