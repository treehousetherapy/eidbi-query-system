# EIDBI Query System Deployment Guide

This guide provides instructions for deploying the EIDBI Query System in a production environment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Deployment](#local-deployment)
3. [Docker Deployment](#docker-deployment)
4. [Google Cloud Deployment](#google-cloud-deployment)
5. [Configuration Options](#configuration-options)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose (for containerized deployment)
- Google Cloud SDK (for GCP deployment)
- Git

## Local Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/eidbi-query-system.git
cd eidbi-query-system
```

### 2. Create and Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit the .env file with your settings
# For local deployment, you can use mock values
```

### 3. Install Dependencies

```bash
# Install backend dependencies
pip install -r backend/requirements.txt

# Install frontend dependencies
pip install -r frontend/requirements.txt

# Install scraper dependencies (optional)
pip install -r scraper/requirements.txt
```

### 4. Run the Application

For Windows:
```bash
# Start the backend
start_backend.bat

# In a new terminal, start the frontend
start_frontend.bat
```

For Linux/macOS:
```bash
# Start the backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# In a new terminal, start the frontend
cd frontend && python -m streamlit run streamlit_app.py
```

The backend will be available at http://localhost:8000 and the frontend at http://localhost:8501.

## Docker Deployment

### 1. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit the .env file with your settings
```

### 2. Build and Start the Containers

```bash
docker-compose up -d
```

This will:
- Build the backend and frontend containers
- Start the services
- Make the backend available at http://localhost:8000
- Make the frontend available at http://localhost:8501

### 3. View Logs

```bash
# View logs for all services
docker-compose logs -f

# View logs for a specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 4. Stop the Services

```bash
docker-compose down
```

## Google Cloud Deployment

### 1. Create a Google Cloud Project

If you don't already have a project:
```bash
gcloud projects create your-project-id
gcloud config set project your-project-id
```

### 2. Enable Required APIs

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

### 3. Create a Docker Repository

```bash
gcloud artifacts repositories create eidbi-repo \
    --repository-format=docker \
    --location=us-central1
```

### 4. Build and Deploy with Cloud Build

```bash
# Authenticate Docker with GCP
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build and deploy using Cloud Build
gcloud builds submit --config cloudbuild.yaml .
```

### 5. Access the Deployed Services

The deployment URLs will be shown in the Cloud Build logs, or you can find them in the Cloud Run console.

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GCP_PROJECT_ID` | Google Cloud project ID | `mock-project-id` |
| `GCP_BUCKET_NAME` | Google Cloud Storage bucket name | `mock-bucket-name` |
| `GCP_REGION` | Google Cloud region | `us-central1` |
| `BACKEND_URL` | URL of the backend service | `http://localhost:8000` |
| `DEFAULT_NUM_RESULTS` | Default number of context chunks | `3` |
| `MAX_NUM_RESULTS` | Maximum number of context chunks | `10` |
| `REQUEST_TIMEOUT` | Request timeout in seconds | `30` |

### Configuration Files

- `config/production.yaml`: Production configuration settings
- `config/settings.py`: Settings management

## Monitoring and Maintenance

### Health Checks

The backend provides a health check endpoint at `/health` that returns:
- Current status
- Version information
- Timestamp

You can use this endpoint for monitoring with tools like Prometheus, Datadog, or Google Cloud Monitoring.

### Logs

- Backend logs are written to stdout/stderr and can be viewed in the Docker logs or Cloud Run logs
- Frontend logs are also written to stdout/stderr

### Updating the System

1. Pull the latest code from the repository
2. Rebuild the Docker images
3. Restart the services

## Troubleshooting

### Common Issues

#### Backend Cannot Connect to Vector Database

Check the configuration in the `.env` file or environment variables.

#### "Failed to retrieve content for search results"

This usually means the backend cannot find the chunks in the local JSONL file. Ensure:
- The scraper has been run successfully
- The correct JSONL file path is configured in `vector_db_service.py`

#### Frontend Cannot Connect to Backend

Check:
- The backend is running
- The `BACKEND_URL` is correctly set
- Network connectivity between the services

### Getting Help

If you encounter issues not covered here, please check the project's GitHub issues or contact the maintainers.

# EIDBI Query System Google Cloud Run Deployment Guide

This guide provides detailed instructions for deploying the EIDBI Query System to Google Cloud Run.

## Prerequisites

1. **Google Cloud Platform Account**
   - If you don't have one, sign up at [cloud.google.com](https://cloud.google.com)
   - Create a new project or use an existing one

2. **Google Cloud SDK (gcloud CLI)**
   - Download and install from [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install)
   - Run `gcloud init` to authenticate and set up your project

3. **Docker**
   - Install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop)

4. **Enable Required APIs**
   ```bash
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable artifactregistry.googleapis.com
   gcloud services enable aiplatform.googleapis.com
   gcloud services enable storage-api.googleapis.com
   ```

## Step 1: Set Environment Variables

Create a `.env` file with your GCP project settings:

```bash
GCP_PROJECT_ID=your-project-id
GCP_BUCKET_NAME=your-eidbi-bucket
GCP_REGION=us-central1
```

## Step 2: Create Required GCP Resources

1. **Create a Cloud Storage Bucket** for storing text chunks:
   ```bash
   gcloud storage buckets create gs://$GCP_BUCKET_NAME --location=$GCP_REGION
   ```

2. **Set up a Service Account** for deployment:
   ```bash
   # Create service account
   gcloud iam service-accounts create eidbi-service-account \
       --display-name="EIDBI Service Account"
   
   # Grant necessary permissions
   gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
       --member="serviceAccount:eidbi-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/storage.admin"
   
   gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
       --member="serviceAccount:eidbi-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/aiplatform.user"
   ```

## Step 3: Build and Deploy Backend Service

1. **Build the backend Docker image:**
   ```bash
   cd backend
   gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/eidbi-backend
   ```

2. **Deploy the backend to Cloud Run:**
   ```bash
   gcloud run deploy eidbi-backend-service \
       --image gcr.io/$GCP_PROJECT_ID/eidbi-backend \
       --region $GCP_REGION \
       --platform managed \
       --allow-unauthenticated \
       --service-account=eidbi-service-account@$GCP_PROJECT_ID.iam.gserviceaccount.com \
       --set-env-vars=GCP_PROJECT_ID=$GCP_PROJECT_ID,GCP_BUCKET_NAME=$GCP_BUCKET_NAME,GCP_REGION=$GCP_REGION
   ```

3. **Note the backend service URL** - you'll need it for the frontend deployment.

## Step 4: Build and Deploy Frontend Service

1. **Build the frontend Docker image:**
   ```bash
   cd frontend
   gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/eidbi-frontend
   ```

2. **Deploy the frontend to Cloud Run:**
   ```bash
   gcloud run deploy eidbi-frontend-service \
       --image gcr.io/$GCP_PROJECT_ID/eidbi-frontend \
       --region $GCP_REGION \
       --platform managed \
       --allow-unauthenticated \
       --set-env-vars=BACKEND_URL=https://eidbi-backend-service-XXXXX-uc.a.run.app
   ```
   
   Replace the `BACKEND_URL` with the actual URL you received when deploying the backend service.

## Step 5: Automated Deployment with Cloud Build

For automated CI/CD deployment, you can use the existing `cloudbuild.yaml` file:

1. **Update the `cloudbuild.yaml` file** with your backend service URL:
   - Find the line with `BACKEND_URL=YOUR_DEPLOYED_BACKEND_URL_HERE`
   - Replace it with your actual backend URL

2. **Deploy using Cloud Build:**
   ```bash
   gcloud builds submit --config=cloudbuild.yaml
   ```

## Step 6: Populating the Vector Database (First-Time Setup)

After deployment, you need to run the scraper to populate the data:

1. **Set up local authentication:**
   ```bash
   gcloud auth application-default login
   ```

2. **Update environment variables:**
   - Edit your `.env` file to include the GCP project settings

3. **Run the scraper locally:**
   ```bash
   python scraper/scraper.py
   ```

## Monitoring and Maintenance

- **View Cloud Run Logs:**
  ```bash
  gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=eidbi-backend-service"
  ```

- **Monitor Service:**
  ```bash
  gcloud run services describe eidbi-backend-service --region $GCP_REGION
  ```

## Troubleshooting

If you encounter issues:

1. **Check service status:**
   ```bash
   gcloud run services describe eidbi-backend-service --region $GCP_REGION
   gcloud run services describe eidbi-frontend-service --region $GCP_REGION
   ```

2. **View detailed logs:**
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=eidbi-backend-service" --limit 50
   ```

3. **Check if the backend is healthy:**
   Visit `https://your-backend-url/health` in your browser

## Cost Management

Google Cloud Run is billed based on:
- Number of requests
- Memory allocation
- CPU allocation
- Duration of requests

You can set up budget alerts in the Google Cloud Console to monitor costs. 