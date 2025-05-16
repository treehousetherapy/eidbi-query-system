# EIDBI Query System Startup Script (PowerShell)
# This script starts both the backend and frontend services

Write-Host "Starting EIDBI Query System..." -ForegroundColor Green

# Get current directory
$currentDir = Get-Location

# Function to check if a port is in use
function Test-PortInUse {
    param (
        [int]$Port
    )
    
    $connections = netstat -ano | Select-String -Pattern "LISTENING" | Select-String -Pattern ":$Port "
    return ($connections.Count -gt 0)
}

# Check if backend port is already in use
if (Test-PortInUse -Port 8000) {
    Write-Host "Warning: Port 8000 is already in use. Backend may already be running." -ForegroundColor Yellow
}

# Check if frontend port is already in use
if (Test-PortInUse -Port 8501) {
    Write-Host "Warning: Port 8501 is already in use. Frontend may already be running." -ForegroundColor Yellow
}

# Start the backend in a new PowerShell window
Write-Host "Starting backend service on http://localhost:8000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$currentDir'; python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

# Wait a bit for the backend to start
Write-Host "Waiting for backend to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Start the frontend in a new PowerShell window
Write-Host "Starting frontend service on http://localhost:8501..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$currentDir'; cd frontend; python -m streamlit run streamlit_app.py"

Write-Host "EIDBI Query System started successfully!" -ForegroundColor Green
Write-Host "Backend URL: http://localhost:8000" -ForegroundColor White
Write-Host "Frontend URL: http://localhost:8501" -ForegroundColor White
Write-Host "Press Ctrl+C to exit this window (services will continue running in their own windows)" -ForegroundColor DarkGray 