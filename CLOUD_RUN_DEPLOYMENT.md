# Deploying EIDBI Query System to Cloud Run

Since we're encountering issues with the automated Cloud Build process, let's deploy the backend and frontend services directly using the Cloud Run console.

## Prerequisites
- Your GitHub repository is set up at: https://github.com/treehousetherapy/eidbi-query-system.git
- Your GCP project is: `lyrical-ward-454915-e6`
- You have a service account: `id-eidbi-service-account@lyrical-ward-454915-e6.iam.gserviceaccount.com`
- You have a Cloud Storage bucket: `eidbi-system-bucket-lyrical-ward`

## Deployment Steps

### 1. Deploy the Backend Service

1. Visit the Google Cloud Console: https://console.cloud.google.com/
2. Navigate to Cloud Run: https://console.cloud.google.com/run
3. Click "CREATE SERVICE"
4. Choose "Continuously deploy from a repository"
5. Click "Set up with Cloud Build"
6. Connect to your GitHub repository: https://github.com/treehousetherapy/eidbi-query-system.git
7. Select the main branch
8. Configure the backend service:
   - Set the service name to "eidbi-backend-service"
   - In the "Build configuration" section, select "Dockerfile"
   - Set the Dockerfile path to "backend/Dockerfile"
   - Set the "Source location" to "backend/"
   - Set region to "us-central1"
   - Choose "Allow unauthenticated invocations"
   - Set the service account to "id-eidbi-service-account@lyrical-ward-454915-e6.iam.gserviceaccount.com"
   - Set environment variables:
     - GCP_PROJECT_ID=lyrical-ward-454915-e6
     - GCP_REGION=us-central1
     - GCP_BUCKET_NAME=eidbi-system-bucket-lyrical-ward
   - Click "CREATE"

### 2. Deploy the Frontend Service

1. After the backend service is deployed, take note of its URL (should be something like "https://eidbi-backend-service-xxxxx-uc.a.run.app")
2. Go back to Cloud Run and click "CREATE SERVICE" again
3. Choose "Continuously deploy from a repository"
4. Click "Set up with Cloud Build"
5. Connect to your GitHub repository again
6. Configure the frontend service:
   - Set the service name to "eidbi-frontend-service"
   - In the "Build configuration" section, select "Dockerfile"
   - Set the Dockerfile path to "frontend/Dockerfile"
   - Set the "Source location" to "frontend/"
   - Set region to "us-central1"
   - Choose "Allow unauthenticated invocations"
   - Set the service account to "id-eidbi-service-account@lyrical-ward-454915-e6.iam.gserviceaccount.com"
   - Set environment variables:
     - BACKEND_URL=[your-backend-service-url]  (replace with the URL from step 1)
   - Click "CREATE"

### 3. Verify Deployment

1. Once both services are deployed, open the frontend service URL in your browser
2. Test the application to ensure it's working correctly and can communicate with the backend

## Troubleshooting

If you encounter any issues:

1. Check the Cloud Build logs for each service
2. Verify that the service accounts have the proper permissions
3. Check that environment variables are set correctly
4. Inspect the service logs in Cloud Run for runtime errors 