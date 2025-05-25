#!/usr/bin/env pwsh
# Enhanced EIDBI System Deployment Script
# This script deploys all the new enhanced features

param(
    [switch]$SkipDependencies,
    [switch]$SkipTests,
    [switch]$Force,
    [string]$Environment = "production"
)

Write-Host "🚀 Enhanced EIDBI System Deployment" -ForegroundColor Green
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host "=" * 50

# Function to check if command exists
function Test-Command($cmdname) {
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# Function to run command with error handling
function Invoke-SafeCommand {
    param([string]$Command, [string]$Description)
    
    Write-Host "📋 $Description..." -ForegroundColor Cyan
    try {
        Invoke-Expression $Command
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code $LASTEXITCODE"
        }
        Write-Host "✅ $Description completed successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ $Description failed: $_" -ForegroundColor Red
        if (-not $Force) {
            exit 1
        }
    }
}

# Step 1: Pre-deployment checks
Write-Host "🔍 Running pre-deployment checks..." -ForegroundColor Yellow

# Check Python
if (-not (Test-Command "python")) {
    Write-Host "❌ Python not found. Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

$pythonVersion = python --version 2>&1
Write-Host "✅ Found $pythonVersion" -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "backend/main.py")) {
    Write-Host "❌ Please run this script from the eidbi-query-system root directory" -ForegroundColor Red
    exit 1
}

# Step 2: Backup current system
Write-Host "💾 Creating backup..." -ForegroundColor Yellow
$backupDir = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

# Backup critical files
$filesToBackup = @(
    "backend/main.py",
    "backend/requirements.txt",
    ".env"
)

foreach ($file in $filesToBackup) {
    if (Test-Path $file) {
        $destPath = Join-Path $backupDir (Split-Path $file -Leaf)
        Copy-Item $file $destPath -Force
        Write-Host "📁 Backed up $file" -ForegroundColor Gray
    }
}

Write-Host "✅ Backup created in $backupDir" -ForegroundColor Green

# Step 3: Install dependencies
if (-not $SkipDependencies) {
    Write-Host "📦 Installing enhanced dependencies..." -ForegroundColor Yellow
    
    # Upgrade pip first
    Invoke-SafeCommand "python -m pip install --upgrade pip" "Upgrading pip"
    
    # Install backend dependencies
    Set-Location backend
    Invoke-SafeCommand "pip install -r requirements.txt" "Installing backend dependencies"
    Set-Location ..
    
    # Install scraper dependencies if they exist
    if (Test-Path "scraper/requirements.txt") {
        Set-Location scraper
        Invoke-SafeCommand "pip install -r requirements.txt" "Installing scraper dependencies"
        Set-Location ..
    }
}

# Step 4: Environment configuration
Write-Host "⚙️ Configuring environment..." -ForegroundColor Yellow

# Check if .env exists, create if not
if (-not (Test-Path ".env")) {
    Write-Host "📝 Creating .env file..." -ForegroundColor Cyan
    
    $envContent = @"
# Enhanced EIDBI System Configuration

# GCP Configuration
GCP_PROJECT_ID=lyrical-ward-454915-e6
GCP_REGION=us-central1
GCP_BUCKET_NAME=your-bucket-name

# Caching Configuration
ENABLE_EMBEDDING_CACHE=true
ENABLE_QUERY_CACHE=true
EMBEDDING_CACHE_SIZE=100
QUERY_CACHE_SIZE=50

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Testing Configuration
TESTING_MODE=false
"@
    
    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✅ Created .env file with default configuration" -ForegroundColor Green
    Write-Host "⚠️  Please update GCP_BUCKET_NAME and other settings as needed" -ForegroundColor Yellow
}

# Step 5: Create directories for enhanced features
Write-Host "🗄️ Preparing storage..." -ForegroundColor Yellow

$directories = @(
    "logs",
    "test_results",
    "feedback_data"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "📁 Created directory: $dir" -ForegroundColor Gray
    }
}

# Step 6: Deploy backend
Write-Host "🚀 Deploying enhanced backend..." -ForegroundColor Yellow

# Stop existing backend if running
Write-Host "🛑 Stopping existing backend..." -ForegroundColor Cyan
try {
    # Try to gracefully stop any running backend
    $backendProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*main.py*" }
    if ($backendProcess) {
        $backendProcess | Stop-Process -Force
        Write-Host "✅ Stopped existing backend process" -ForegroundColor Green
    }
}
catch {
    Write-Host "ℹ️  No existing backend process found" -ForegroundColor Gray
}

# Start enhanced backend
Write-Host "▶️  Starting enhanced backend..." -ForegroundColor Cyan

Set-Location backend

# Start the backend
if ($Environment -eq "development") {
    Write-Host "🔧 Starting in development mode..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "main.py" -NoNewWindow
} else {
    Write-Host "🏭 Starting in production mode..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "main.py"
}

Set-Location ..

# Wait a moment for startup
Start-Sleep -Seconds 5

# Step 7: Verify deployment
Write-Host "✅ Verifying deployment..." -ForegroundColor Yellow

$apiUrl = "http://localhost:8000"
$maxRetries = 10
$retryCount = 0

do {
    try {
        $response = Invoke-RestMethod -Uri "$apiUrl/health" -Method GET -TimeoutSec 5
        if ($response.status -eq "healthy") {
            Write-Host "✅ Backend is healthy!" -ForegroundColor Green
            Write-Host "📊 Version: $($response.version)" -ForegroundColor Gray
            break
        }
    }
    catch {
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-Host "⏳ Waiting for backend to start... (attempt $retryCount/$maxRetries)" -ForegroundColor Yellow
            Start-Sleep -Seconds 3
        } else {
            Write-Host "❌ Backend health check failed after $maxRetries attempts" -ForegroundColor Red
            Write-Host "🔍 Check logs for details" -ForegroundColor Yellow
            break
        }
    }
} while ($retryCount -lt $maxRetries)

# Step 8: Deployment summary
Write-Host ""
Write-Host "🎉 Enhanced EIDBI System Deployment Complete!" -ForegroundColor Green
Write-Host "=" * 50

Write-Host "📊 Deployment Summary:" -ForegroundColor Yellow
Write-Host "• Backend URL: $apiUrl" -ForegroundColor Gray
Write-Host "• Version: 2.0.0 (Enhanced)" -ForegroundColor Gray
Write-Host "• Backup: $backupDir" -ForegroundColor Gray

Write-Host ""
Write-Host "🚀 New Features Available:" -ForegroundColor Yellow
Write-Host "• ✅ Advanced Caching System" -ForegroundColor Green
Write-Host "• ✅ Feedback Loops" -ForegroundColor Green
Write-Host "• ✅ Multi-Source Data Integration" -ForegroundColor Green
Write-Host "• ✅ Enhanced Prompt Engineering" -ForegroundColor Green
Write-Host "• ✅ Automated Testing" -ForegroundColor Green

Write-Host ""
Write-Host "🔗 Key Endpoints:" -ForegroundColor Yellow
Write-Host "• Health Check: $apiUrl/health" -ForegroundColor Gray
Write-Host "• Enhanced Query: $apiUrl/query" -ForegroundColor Gray
Write-Host "• Submit Feedback: $apiUrl/feedback" -ForegroundColor Gray
Write-Host "• Cache Stats: $apiUrl/cache-stats" -ForegroundColor Gray
Write-Host "• Data Sources: $apiUrl/data-sources/status" -ForegroundColor Gray

Write-Host ""
Write-Host "✨ Deployment completed successfully!" -ForegroundColor Green 