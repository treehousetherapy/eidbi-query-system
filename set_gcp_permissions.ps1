# PowerShell Script to set GCP IAM Permissions for EIDBI Query System Deployment
# Project ID: lyrical-ward-454915-e6
#
# IMPORTANT:
# 1. Run this script from a terminal where you are authenticated with gcloud CLI.
# 2. Ensure you have sufficient permissions (e.g., Project Owner or IAM Admin)
#    on the GCP project to grant these roles.

# --- Configuration ---
$GcpProjectId = "lyrical-ward-454915-e6"
$ComputeServiceAccount = "171738705900-compute@developer.gserviceaccount.com"
$CloudBuildServiceAccount = "171738705900@cloudbuild.gserviceaccount.com"
$CloudBuildSourceBucket = "gs://lyrical-ward-454915-e6_cloudbuild" # Default Cloud Build source bucket
$BackendDataBucket = "gs://eidbi-system-bucket-lyrical-ward"      # Bucket defined in cloudbuild.yaml

# --- Script ---

Write-Host "Setting active GCP project to: $GcpProjectId" -ForegroundColor Yellow
gcloud config set project $GcpProjectId
if ($LASTEXITCODE -ne 0) { Write-Host "Failed to set project. Exiting." -ForegroundColor Red; exit 1 }

Write-Host "`n--- Granting permissions to Compute Engine default service account ($ComputeServiceAccount) ---" -ForegroundColor Cyan

# Grant Storage Object Admin to the Compute service account for the project
# This allows it to access GCS objects, which is needed by Cloud Build when resolving source.
Write-Host "Granting roles/storage.objectAdmin to $ComputeServiceAccount for project $GcpProjectId..." -ForegroundColor Yellow
gcloud projects add-iam-policy-binding $GcpProjectId `
  --member="serviceAccount:$ComputeServiceAccount" `
  --role="roles/storage.objectAdmin"
if ($LASTEXITCODE -ne 0) { Write-Host "Failed. Check permissions or if the service account exists." -ForegroundColor Red } else { Write-Host "Done." -ForegroundColor Green }

# Grant Storage Object Admin to the Compute service account for the Cloud Build source bucket
# This is often where Cloud Build stores source code archives.
Write-Host "Granting roles/storage.objectAdmin to $ComputeServiceAccount for bucket $CloudBuildSourceBucket..." -ForegroundColor Yellow
gcloud storage buckets add-iam-policy-binding $CloudBuildSourceBucket `
  --member="serviceAccount:$ComputeServiceAccount" `
  --role="roles/storage.objectAdmin"
if ($LASTEXITCODE -ne 0) { Write-Host "Failed. Check if bucket $CloudBuildSourceBucket exists or if you have permissions." -ForegroundColor Red } else { Write-Host "Done." -ForegroundColor Green }


Write-Host "`n--- Granting permissions to Cloud Build service account ($CloudBuildServiceAccount) ---" -ForegroundColor Cyan

# Grant Run Admin to the Cloud Build service account
Write-Host "Granting roles/run.admin to $CloudBuildServiceAccount..." -ForegroundColor Yellow
gcloud projects add-iam-policy-binding $GcpProjectId `
  --member="serviceAccount:$CloudBuildServiceAccount" `
  --role="roles/run.admin"
if ($LASTEXITCODE -ne 0) { Write-Host "Failed." -ForegroundColor Red } else { Write-Host "Done." -ForegroundColor Green }

# Grant IAM Service Account User to the Cloud Build service account
# This allows Cloud Build to act as/use other service accounts if specified in build steps (e.g., for deployment)
Write-Host "Granting roles/iam.serviceAccountUser to $CloudBuildServiceAccount..." -ForegroundColor Yellow
gcloud projects add-iam-policy-binding $GcpProjectId `
  --member="serviceAccount:$CloudBuildServiceAccount" `
  --role="roles/iam.serviceAccountUser"
if ($LASTEXITCODE -ne 0) { Write-Host "Failed." -ForegroundColor Red } else { Write-Host "Done." -ForegroundColor Green }

# Grant Storage Admin to the Cloud Build service account
# This allows Cloud Build to push images to GCR and access other GCS resources if needed.
Write-Host "Granting roles/storage.admin to $CloudBuildServiceAccount..." -ForegroundColor Yellow
gcloud projects add-iam-policy-binding $GcpProjectId `
  --member="serviceAccount:$CloudBuildServiceAccount" `
  --role="roles/storage.admin"
if ($LASTEXITCODE -ne 0) { Write-Host "Failed." -ForegroundColor Red } else { Write-Host "Done." -ForegroundColor Green }

# Grant Artifact Registry Admin to the Cloud Build service account
# This allows Cloud Build to create and manage Artifact Registry repositories
Write-Host "Granting roles/artifactregistry.admin to $CloudBuildServiceAccount..." -ForegroundColor Yellow
gcloud projects add-iam-policy-binding $GcpProjectId `
  --member="serviceAccount:$CloudBuildServiceAccount" `
  --role="roles/artifactregistry.admin"
if ($LASTEXITCODE -ne 0) { Write-Host "Failed." -ForegroundColor Red } else { Write-Host "Done." -ForegroundColor Green }

# Grant Cloud Build Writer permission to the Cloud Build service account
# This enables writing build logs
Write-Host "Granting roles/logging.logWriter to $CloudBuildServiceAccount..." -ForegroundColor Yellow
gcloud projects add-iam-policy-binding $GcpProjectId `
  --member="serviceAccount:$CloudBuildServiceAccount" `
  --role="roles/logging.logWriter"
if ($LASTEXITCODE -ne 0) { Write-Host "Failed." -ForegroundColor Red } else { Write-Host "Done." -ForegroundColor Green }

Write-Host "`n--- Permissions script finished. ---" -ForegroundColor Cyan
Write-Host "Please ensure the following bucket exists for the backend service:" -ForegroundColor Yellow
Write-Host "$BackendDataBucket" -ForegroundColor Yellow
Write-Host "You can create it with: gcloud storage buckets create $BackendDataBucket --project=$GcpProjectId --location=us-central1" -ForegroundColor Yellow
Write-Host "`nAfter confirming permissions and bucket creation, you can submit your build:" -ForegroundColor Yellow
Write-Host "gcloud builds submit --config=cloudbuild.yaml --project=$GcpProjectId ." -ForegroundColor Yellow 