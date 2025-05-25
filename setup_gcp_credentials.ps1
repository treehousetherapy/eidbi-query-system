#!/usr/bin/env powershell
# Script to set up Google Cloud credentials for EIDBI Query System

Write-Host "=== Google Cloud Credentials Setup for EIDBI Query System ===" -ForegroundColor Cyan
Write-Host ""

# Configuration
$ProjectId = "lyrical-ward-454915-e6"
$ServiceAccountEmail = "id-eidbi-service-account@lyrical-ward-454915-e6.iam.gserviceaccount.com"
$KeyFileName = "eidbi-service-account-key.json"
$KeyFilePath = Join-Path $PSScriptRoot $KeyFileName

# Check if gcloud is installed
Write-Host "Checking for gcloud CLI installation..." -ForegroundColor Yellow
try {
    $gcloudVersion = gcloud version --format=json | ConvertFrom-Json
    Write-Host "✓ gcloud CLI is installed" -ForegroundColor Green
} catch {
    Write-Host "✗ gcloud CLI is not installed!" -ForegroundColor Red
    Write-Host "Please install Google Cloud SDK from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    Write-Host "After installation, restart this script." -ForegroundColor Yellow
    exit 1
}

# Check current authentication
Write-Host ""
Write-Host "Checking current authentication..." -ForegroundColor Yellow
$currentAccount = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null

if ($currentAccount) {
    Write-Host "Currently authenticated as: $currentAccount" -ForegroundColor Cyan
    $useExisting = Read-Host "Do you want to use this account? (Y/N)"
    
    if ($useExisting -ne 'Y' -and $useExisting -ne 'y') {
        Write-Host "Please run 'gcloud auth login' to authenticate with a different account" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "No active authentication found." -ForegroundColor Yellow
    Write-Host "Please authenticate with Google Cloud..." -ForegroundColor Cyan
    gcloud auth login
}

# Set the project
Write-Host ""
Write-Host "Setting active project to: $ProjectId" -ForegroundColor Yellow
gcloud config set project $ProjectId

# Check if service account key already exists
if (Test-Path $KeyFilePath) {
    Write-Host ""
    Write-Host "Service account key already exists at: $KeyFilePath" -ForegroundColor Yellow
    $overwrite = Read-Host "Do you want to create a new key? (Y/N)"
    
    if ($overwrite -eq 'Y' -or $overwrite -eq 'y') {
        Remove-Item $KeyFilePath -Force
    } else {
        Write-Host "Using existing key file." -ForegroundColor Green
    }
}

# Create service account key if it doesn't exist
if (-not (Test-Path $KeyFilePath)) {
    Write-Host ""
    Write-Host "Creating service account key..." -ForegroundColor Yellow
    
    try {
        gcloud iam service-accounts keys create $KeyFilePath `
            --iam-account=$ServiceAccountEmail `
            --project=$ProjectId
            
        if (Test-Path $KeyFilePath) {
            Write-Host "✓ Service account key created successfully at: $KeyFilePath" -ForegroundColor Green
        } else {
            throw "Key file was not created"
        }
    } catch {
        Write-Host "✗ Failed to create service account key!" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "This might be because:" -ForegroundColor Yellow
        Write-Host "1. You don't have permission to create keys for this service account" -ForegroundColor Yellow
        Write-Host "2. The service account doesn't exist" -ForegroundColor Yellow
        Write-Host "3. You've reached the key limit for this service account" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Please contact your GCP administrator or try:" -ForegroundColor Cyan
        Write-Host "1. Using your own Google account with 'gcloud auth application-default login'" -ForegroundColor Cyan
        Write-Host "2. Getting the key file from your GCP administrator" -ForegroundColor Cyan
        exit 1
    }
}

# Update the batch file to include the credential
Write-Host ""
Write-Host "Updating start_enhanced_backend.bat with credentials..." -ForegroundColor Yellow

$batchFilePath = Join-Path $PSScriptRoot "start_enhanced_backend.bat"
$batchContent = Get-Content $batchFilePath -Raw

# Check if GOOGLE_APPLICATION_CREDENTIALS is already set
if ($batchContent -notmatch "GOOGLE_APPLICATION_CREDENTIALS") {
    # Find the line with environment variables and add our credential
    $updatedContent = $batchContent -replace `
        '(set ENABLE_QUERY_CACHE=true)', `
        "`$1`r`nset GOOGLE_APPLICATION_CREDENTIALS=%~dp0$KeyFileName"
    
    Set-Content -Path $batchFilePath -Value $updatedContent -Encoding ASCII
    Write-Host "✓ Updated start_enhanced_backend.bat" -ForegroundColor Green
} else {
    Write-Host "✓ GOOGLE_APPLICATION_CREDENTIALS already set in batch file" -ForegroundColor Green
}

# Also update the batch file to use real responses
Write-Host ""
Write-Host "Disabling mock mode in start_enhanced_backend.bat..." -ForegroundColor Yellow

$batchContent = Get-Content $batchFilePath -Raw
$updatedContent = $batchContent -replace 'set USE_MOCK_EMBEDDINGS=true', 'set USE_MOCK_EMBEDDINGS=false'
$updatedContent = $updatedContent -replace 'set MOCK_LLM_RESPONSES=true', 'set MOCK_LLM_RESPONSES=false'
Set-Content -Path $batchFilePath -Value $updatedContent -Encoding ASCII

Write-Host "✓ Mock mode disabled" -ForegroundColor Green

# Test the authentication
Write-Host ""
Write-Host "Testing authentication..." -ForegroundColor Yellow

$env:GOOGLE_APPLICATION_CREDENTIALS = $KeyFilePath
$pythonScript = @"
import google.auth
try:
    credentials, project = google.auth.default()
    print('✓ Authentication test successful!')
    print(f'  Project: {project}')
except Exception as e:
    print('✗ Authentication test failed!')
    print(f'  Error: {e}')
"@

python -c $pythonScript

# Provide instructions
Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Your Google Cloud credentials have been configured!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Run 'start_enhanced_backend.bat' to start the backend with real AI responses" -ForegroundColor White
Write-Host "2. The system will now use Google Cloud's Vertex AI instead of mock responses" -ForegroundColor White
Write-Host ""
Write-Host "Important:" -ForegroundColor Yellow
Write-Host "- Keep the file '$KeyFileName' secure and don't commit it to git" -ForegroundColor White
Write-Host "- The key file has been added to the same directory as this script" -ForegroundColor White
Write-Host "- Make sure to add '$KeyFileName' to your .gitignore file" -ForegroundColor White

# Check if .gitignore exists and add the key file
$gitignorePath = Join-Path $PSScriptRoot ".gitignore"
if (Test-Path $gitignorePath) {
    $gitignoreContent = Get-Content $gitignorePath -Raw
    if ($gitignoreContent -notmatch [regex]::Escape($KeyFileName)) {
        Add-Content -Path $gitignorePath -Value "`n# Google Cloud service account key`n$KeyFileName"
        Write-Host "✓ Added $KeyFileName to .gitignore" -ForegroundColor Green
    }
} 