# EIDBI Query System - Google Cloud Run Deployment Script (PowerShell)
# This script automates the deployment of the EIDBI Query System to Google Cloud Run

param(
    [Parameter(Mandatory=$false)]
    [string]$ProjectId,
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-central1",
    
    [Parameter(Mandatory=$false)]
    [string]$BucketName
)

# Display header
Write-Host "EIDBI Query System - Google Cloud Run Deployment" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "This script will deploy the application to Google Cloud Run."
Write-Host "Please ensure you have gcloud CLI installed and configured.`n"

# Get GCP information if not provided as parameters
if ([string]::IsNullOrWhiteSpace($ProjectId)) {
    $ProjectId = Read-Host -Prompt "Enter your GCP Project ID"
    if ([string]::IsNullOrWhiteSpace($ProjectId)) {
        Write-Host "Error: Project ID cannot be empty." -ForegroundColor Red
        exit 1
    }
}

if ([string]::IsNullOrWhiteSpace($Region)) {
    $Region = Read-Host -Prompt "Enter GCP Region (e.g., us-central1)"
    if ([string]::IsNullOrWhiteSpace($Region)) {
        Write-Host "Error: Region cannot be empty." -ForegroundColor Red
        exit 1
    }
}

if ([string]::IsNullOrWhiteSpace($BucketName)) {
    $BucketName = Read-Host -Prompt "Enter Cloud Storage Bucket Name (lowercase letters, numbers, hyphens only)"
    if ([string]::IsNullOrWhiteSpace($BucketName)) {
        Write-Host "Error: Bucket name cannot be empty." -ForegroundColor Red
        exit 1
    }
}

# Display the values we're using
Write-Host "`nDeploying with:" -ForegroundColor Yellow
Write-Host "  Project ID: $ProjectId" -ForegroundColor Yellow
Write-Host "  Region:     $Region" -ForegroundColor Yellow
Write-Host "  Bucket:     $BucketName" -ForegroundColor Yellow

# Bucket name validation
if ($BucketName -notmatch "^[a-z0-9][-a-z0-9]+[a-z0-9]$") {
    Write-Host "Error: Bucket name must use only lowercase letters, numbers, and hyphens." -ForegroundColor Red
    Write-Host "Bucket names must start and end with a letter or number, be 3-63 characters long," -ForegroundColor Red
    Write-Host "and cannot begin with 'goog' or contain consecutive hyphens." -ForegroundColor Red
    exit 1
}

# Configure gcloud with the project
Write-Host "`nConfiguring gcloud with your project..." -ForegroundColor Yellow
gcloud config set project $ProjectId

# Enable required services
Write-Host "`nEnabling required GCP services..." -ForegroundColor Yellow
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com aiplatform.googleapis.com storage-api.googleapis.com

# Create Cloud Storage bucket if it doesn't exist
Write-Host "`nChecking if bucket exists..." -ForegroundColor Yellow
try {
    $BucketExists = gcloud storage buckets list --filter="name=gs://$BucketName" --format="value(name)"
    if ($BucketExists) {
        Write-Host "Bucket already exists: gs://$BucketName" -ForegroundColor Green
    } else {
        Write-Host "Creating bucket gs://$BucketName..." -ForegroundColor Yellow
        $BucketCreation = gcloud storage buckets create gs://$BucketName --location=$Region 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Bucket created: gs://$BucketName" -ForegroundColor Green
        } else {
            if ($BucketCreation -match "409" -or $BucketCreation -match "already own") {
                Write-Host "Bucket already exists and you own it: gs://$BucketName" -ForegroundColor Green
            } else {
                Write-Host "Failed to create bucket: $BucketCreation" -ForegroundColor Red
                Write-Host "Please check the bucket name and try again." -ForegroundColor Red
                exit 1
            }
        }
    }
} catch {
    Write-Host "Error checking/creating bucket: $_" -ForegroundColor Red
    exit 1
}

# Create service account
Write-Host "`nCreating and configuring service account..." -ForegroundColor Yellow
$SERVICE_ACCOUNT_NAME = "eidbi-service-account"
$SERVICE_ACCOUNT_EMAIL = "$SERVICE_ACCOUNT_NAME@$ProjectId.iam.gserviceaccount.com"

# Create service account if it doesn't exist
$ServiceAccountExists = gcloud iam service-accounts list --filter="email=$SERVICE_ACCOUNT_EMAIL" --format="value(email)"
if (-not $ServiceAccountExists) {
    gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME --display-name="EIDBI Service Account"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Service account created: $SERVICE_ACCOUNT_EMAIL" -ForegroundColor Green
    } else {
        Write-Host "Failed to create service account. Check permissions and try again." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Service account already exists: $SERVICE_ACCOUNT_EMAIL" -ForegroundColor Green
}

# Grant necessary permissions
Write-Host "Granting permissions to service account..." -ForegroundColor Yellow
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/storage.admin"
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/aiplatform.user"
Write-Host "Permissions granted to service account" -ForegroundColor Green

# Check for Cloud Build service account and grant permissions
Write-Host "`nChecking and configuring Cloud Build service account..." -ForegroundColor Yellow
# Get a known Cloud Build service account format
$PROJECT_NUMBER = gcloud projects describe $ProjectId --format="value(projectNumber)"
if (-not [string]::IsNullOrWhiteSpace($PROJECT_NUMBER)) {
    $CLOUDBUILD_SA = "$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"
    $COMPUTE_SA = "$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
    
    Write-Host "Using Cloud Build service account: $CLOUDBUILD_SA" -ForegroundColor Green
    Write-Host "Using Compute service account: $COMPUTE_SA" -ForegroundColor Green
    
    # Grant necessary permissions
    gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$CLOUDBUILD_SA" --role="roles/run.admin"
    gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$CLOUDBUILD_SA" --role="roles/iam.serviceAccountUser"
    gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$CLOUDBUILD_SA" --role="roles/storage.admin"
    
    # Grant compute service account access to the bucket directly
    Write-Host "Granting compute service account access to the deployment bucket..." -ForegroundColor Yellow
    gcloud storage buckets add-iam-policy-binding gs://$BucketName --member="serviceAccount:$COMPUTE_SA" --role="roles/storage.objectAdmin"
    Write-Host "Bucket permissions granted" -ForegroundColor Green
} else {
    Write-Host "Could not determine project number. Skipping Cloud Build permission setup." -ForegroundColor Yellow
}

# Build and deploy backend
Write-Host "`nBuilding and deploying backend service..." -ForegroundColor Yellow

# Check if backend directory exists
if (-not (Test-Path "backend")) {
    Write-Host "Backend directory not found. Please make sure you're running this script from the project root." -ForegroundColor Red
    exit 1
}

# Use a different deployment approach - build container with Cloud Build first
Write-Host "Building backend container image using Cloud Build..." -ForegroundColor Yellow
Set-Location -Path "backend"

# Create a Dockerfile if it doesn't exist
if (-not (Test-Path "Dockerfile")) {
    Write-Host "Creating a basic Dockerfile for backend..." -ForegroundColor Yellow
    @"
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
CMD ["python", "main.py"]
"@ | Out-File -FilePath "Dockerfile" -Encoding utf8
}

# Build the image
$BACKEND_IMAGE = "gcr.io/$ProjectId/eidbi-backend:latest"
gcloud builds submit --tag $BACKEND_IMAGE .

$BuildSuccess = $LASTEXITCODE -eq 0
if ($BuildSuccess) {
    Write-Host "Backend image built successfully: $BACKEND_IMAGE" -ForegroundColor Green
    
    # Deploy the built image to Cloud Run
    Write-Host "Deploying backend image to Cloud Run..." -ForegroundColor Yellow
    gcloud run deploy eidbi-backend-service `
        --image $BACKEND_IMAGE `
        --region=$Region `
        --platform=managed `
        --allow-unauthenticated `
        --service-account=$SERVICE_ACCOUNT_EMAIL `
        --set-env-vars="GCP_PROJECT_ID=$ProjectId,GCP_BUCKET_NAME=$BucketName,GCP_REGION=$Region"
    
    $DeploySuccess = $LASTEXITCODE -eq 0
} else {
    Write-Host "Backend image build failed. Review the error messages above." -ForegroundColor Red
    $DeploySuccess = $false
}

Set-Location -Path ".."

# Get backend service URL if deployment was successful
$BACKEND_URL = ""
if ($DeploySuccess) {
    $BACKEND_URL = gcloud run services describe eidbi-backend-service --region=$Region --format="value(status.url)"
    Write-Host "Backend deployed successfully at: $BACKEND_URL" -ForegroundColor Green
} else {
    Write-Host "Backend deployment failed. Review the error messages above." -ForegroundColor Red
}

# Build and deploy frontend
Write-Host "`nBuilding and deploying frontend service..." -ForegroundColor Yellow

# Check if frontend directory exists
if (-not (Test-Path "frontend")) {
    Write-Host "Frontend directory not found. Please make sure you're running this script from the project root." -ForegroundColor Red
    exit 1
}

# Use the same approach for frontend
Write-Host "Building frontend container image using Cloud Build..." -ForegroundColor Yellow
Set-Location -Path "frontend"

# Create a Dockerfile if it doesn't exist
if (-not (Test-Path "Dockerfile")) {
    Write-Host "Creating a basic Dockerfile for frontend..." -ForegroundColor Yellow
    @"
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
ENV BACKEND_URL=$BACKEND_URL

CMD ["streamlit", "run", "app.py", "--server.port", "\$PORT", "--server.address", "0.0.0.0"]
"@ | Out-File -FilePath "Dockerfile" -Encoding utf8
}

# Build the image
$FRONTEND_IMAGE = "gcr.io/$ProjectId/eidbi-frontend:latest"
gcloud builds submit --tag $FRONTEND_IMAGE .

$FrontendBuildSuccess = $LASTEXITCODE -eq 0
if ($FrontendBuildSuccess) {
    Write-Host "Frontend image built successfully: $FRONTEND_IMAGE" -ForegroundColor Green
    
    # Deploy the built image to Cloud Run
    Write-Host "Deploying frontend image to Cloud Run..." -ForegroundColor Yellow
    gcloud run deploy eidbi-frontend-service `
        --image $FRONTEND_IMAGE `
        --region=$Region `
        --platform=managed `
        --allow-unauthenticated `
        --service-account=$SERVICE_ACCOUNT_EMAIL `
        --set-env-vars="BACKEND_URL=$BACKEND_URL"
    
    $FrontendDeploySuccess = $LASTEXITCODE -eq 0
} else {
    Write-Host "Frontend image build failed. Review the error messages above." -ForegroundColor Red
    $FrontendDeploySuccess = $false
}

Set-Location -Path ".."

# Get frontend service URL
$FRONTEND_URL = ""
if ($FrontendDeploySuccess) {
    $FRONTEND_URL = gcloud run services describe eidbi-frontend-service --region=$Region --format="value(status.url)"
    Write-Host "Frontend deployed successfully at: $FRONTEND_URL" -ForegroundColor Green
} else {
    Write-Host "Frontend deployment failed. Review the error messages above." -ForegroundColor Red
}

# Update cloudbuild.yaml with the correct backend URL
if ($DeploySuccess -and (Test-Path "cloudbuild.yaml")) {
    Write-Host "`nUpdating cloudbuild.yaml with the correct backend URL..." -ForegroundColor Yellow
    $CloudBuildContent = Get-Content -Path "cloudbuild.yaml" -Raw
    $UpdatedContent = $CloudBuildContent -replace "BACKEND_URL=YOUR_DEPLOYED_BACKEND_URL_HERE", "BACKEND_URL=$BACKEND_URL"
    Set-Content -Path "cloudbuild.yaml" -Value $UpdatedContent
    Write-Host "cloudbuild.yaml updated successfully" -ForegroundColor Green
}

# Display deployment information
Write-Host "`n============== Deployment Status ==============" -ForegroundColor Cyan
if ($DeploySuccess) {
    Write-Host "Backend URL: $BACKEND_URL" -ForegroundColor Green
} else {
    Write-Host "Backend: DEPLOYMENT FAILED" -ForegroundColor Red
}

if ($FrontendDeploySuccess) {
    Write-Host "Frontend URL: $FRONTEND_URL" -ForegroundColor Green
} else {
    Write-Host "Frontend: DEPLOYMENT FAILED" -ForegroundColor Red
}

Write-Host "`nNext Steps:" -ForegroundColor Yellow
if ($DeploySuccess -and $FrontendDeploySuccess) {
    Write-Host "1. Run the scraper to populate your vector database"
    Write-Host "2. Use the frontend URL to access your application"
    Write-Host "3. For future deployments, you can use:"
    Write-Host "   gcloud builds submit --config=cloudbuild.yaml" -ForegroundColor Gray
} else {
    Write-Host "1. Review the error messages above"
    Write-Host "2. Fix any issues and try deploying again"
    Write-Host "3. You may need to check Cloud Build logs or project permissions"
}
Write-Host "=================================================" -ForegroundColor Cyan 