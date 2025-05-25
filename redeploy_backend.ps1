#!/usr/bin/env pwsh
# PowerShell script to redeploy the EIDBI backend service to Cloud Run

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "EIDBI Backend Service Redeployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Set variables
$PROJECT_ID = "lyrical-ward-454915-e6"
$SERVICE_NAME = "eidbi-backend-service"
$REGION = "us-central1"
$SERVICE_ACCOUNT = "id-eidbi-service-account@$PROJECT_ID.iam.gserviceaccount.com"

Write-Host "`nProject: $PROJECT_ID" -ForegroundColor Yellow
Write-Host "Service: $SERVICE_NAME" -ForegroundColor Yellow
Write-Host "Region: $REGION" -ForegroundColor Yellow

# Check if gcloud is configured correctly
Write-Host "`nChecking gcloud configuration..." -ForegroundColor Green
$currentProject = gcloud config get-value project 2>$null
if ($currentProject -ne $PROJECT_ID) {
    Write-Host "Setting gcloud project to $PROJECT_ID..." -ForegroundColor Yellow
    gcloud config set project $PROJECT_ID
}

# Build and deploy using Cloud Build
Write-Host "`nBuilding and deploying backend service..." -ForegroundColor Green
Write-Host "This will:" -ForegroundColor Cyan
Write-Host "  1. Build a new Docker image with updated requirements" -ForegroundColor White
Write-Host "  2. Deploy it to Cloud Run" -ForegroundColor White
Write-Host "  3. Update the service with the new image" -ForegroundColor White

Write-Host "`nExecuting deployment command..." -ForegroundColor Green

# Execute the deployment command directly
& gcloud run deploy $SERVICE_NAME `
    --source backend `
    --region $REGION `
    --platform managed `
    --allow-unauthenticated `
    --service-account $SERVICE_ACCOUNT `
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=$REGION,GCP_BUCKET_NAME=eidbi-system-bucket-lyrical-ward" `
    --memory 1Gi `
    --cpu 1 `
    --timeout 300 `
    --max-instances 10

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "Backend deployment successful!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    
    # Get the service URL
    $serviceUrl = gcloud run services describe $SERVICE_NAME --region $REGION --format "value(status.url)" 2>$null
    if ($serviceUrl) {
        Write-Host "`nService URL: $serviceUrl" -ForegroundColor Cyan
        Write-Host "`nYou can test the service with:" -ForegroundColor Yellow
        Write-Host "  curl $serviceUrl/health" -ForegroundColor White
        Write-Host "  python diagnose_backend.py" -ForegroundColor White
    }
} else {
    Write-Host "`n========================================" -ForegroundColor Red
    Write-Host "Backend deployment failed!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Please check the error messages above." -ForegroundColor Yellow
    exit 1
}

Write-Host "`nNote: It may take a few minutes for the new version to be fully deployed." -ForegroundColor Yellow
Write-Host "You can monitor the deployment at: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/logs?project=$PROJECT_ID" -ForegroundColor Cyan 