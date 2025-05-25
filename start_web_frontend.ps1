#!/usr/bin/env pwsh
# Start EIDBI Web Frontend

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting EIDBI Chat UI (Web Frontend)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to web-frontend directory
Set-Location -Path "web-frontend"

# Start the server
Write-Host "Starting server on http://localhost:8080" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

python server.py 