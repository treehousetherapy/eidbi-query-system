# Deploying EIDBI Query System to Cloud Run

This document provides instructions for both manual deployment and automated CI/CD pipeline setup for the EIDBI Query System.

## Prerequisites
- Your GitHub repository is set up at: https://github.com/treehousetherapy/eidbi-query-system.git
- Your GCP project is: `lyrical-ward-454915-e6`
- You have a service account: `id-eidbi-service-account@lyrical-ward-454915-e6.iam.gserviceaccount.com`
- You have a Cloud Storage bucket: `eidbi-system-bucket-lyrical-ward`

## Manual Deployment Steps

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

## Automated CI/CD Pipeline Setup with Cloud Build and GitHub

To automate deployments for both backend and frontend, follow these steps to set up a robust CI/CD pipeline using Google Cloud Build and GitHub:

### 1. Set Required IAM Permissions

Run the provided `set_gcp_permissions.ps1` script to grant necessary permissions to service accounts:

```powershell
.\set_gcp_permissions.ps1
```

This script grants the following roles to the Cloud Build service account:
- Cloud Run Admin (`roles/run.admin`)
- Service Account User (`roles/iam.serviceAccountUser`)
- Storage Admin (`roles/storage.admin`)
- Artifact Registry Admin (`roles/artifactregistry.admin`)
- Logging Writer (`roles/logging.logWriter`)

### 2. Create Artifact Registry Repository

Before running the CI/CD pipeline, create an Artifact Registry repository to store container images:

```bash
gcloud artifacts repositories create cloud-run-source-deploy \
  --project=lyrical-ward-454915-e6 \
  --repository-format=docker \
  --location=us-central1 \
  --description="Repository for EIDBI Query System"
```

Note: The updated CI/CD pipeline will automatically try to create this repository if it doesn't exist.

### 3. Connect GitHub to Google Cloud

1. Go to the [Cloud Build Triggers page](https://console.cloud.google.com/cloud-build/triggers) in the Google Cloud Console.
2. Click "Create Trigger."
3. Select "GitHub" as the source and follow the prompts to connect your repository if you haven't already.

### 4. Create a Build Trigger

Configure the trigger with these settings:
- **Name:** `eidbi-main-deploy`
- **Event:** Push to branch
- **Branch:** `main` (or your preferred branch)
- **Repository:** `treehousetherapy/eidbi-query-system`
- **Build Configuration:** Use `cloudbuild.yaml` in the root directory

Alternatively, you can import the trigger configuration using the provided `trigger-config.json` file:

```bash
gcloud beta builds triggers import --source=trigger-config.json
```

### 5. Manually Trigger Your First Build

To start your first build:

1. Go to Cloud Build Triggers in the console
2. Find your trigger and click "Run Trigger"
3. Specify the branch (usually "main")
4. Click "Run"

You can also trigger a build by pushing a small change to your repository.

### 6. Verify Deployment

After the build completes:
1. Check Cloud Build logs for any errors
2. Verify both services are deployed in Cloud Run
3. Open the frontend service URL in your browser to test the application

## Troubleshooting

If you encounter any issues with the CI/CD pipeline:

1. **Artifact Registry Issues**:
   - Verify the repository exists: `gcloud artifacts repositories describe cloud-run-source-deploy --location=us-central1`
   - Check that the Cloud Build service account has the `artifactregistry.admin` role

2. **Permission Issues**:
   - Check service account roles: 
     ```
     gcloud projects get-iam-policy lyrical-ward-454915-e6 --flatten="bindings[].members" --format="table(bindings.role)" --filter="bindings.members:[SERVICE_ACCOUNT_EMAIL]"
     ```
   - Ensure all required roles from step 1 are granted

3. **Deployment Failures**:
   - Check Cloud Build logs for detailed error messages
   - Verify environment variables are set correctly
   - Inspect the service logs in Cloud Run for runtime errors

4. **Image Access Issues**:
   - Ensure the service account used for deployment has access to Artifact Registry
   - Check that image paths and project IDs are correct in all configuration files

5. **Run with Debug Flags**:
   - The updated pipeline includes debug flags (`--verbosity=debug`, `--log-http`) for detailed logging
   - Review these logs for specific error messages that can help isolate the issue 