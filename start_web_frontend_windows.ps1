# Start EIDBI Web Frontend - Windows Compatible

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting EIDBI Chat UI (Web Frontend)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to web-frontend directory
Push-Location
Set-Location -Path "$PSScriptRoot\web-frontend"

# Start the server
Write-Host "Starting server on http://localhost:8080" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

try {
    python server.py
} finally {
    Pop-Location
} 