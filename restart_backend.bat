@echo off
echo Stopping backend processes...

REM Kill any Python processes on port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo Killing process %%a
    taskkill /PID %%a /F 2>nul
)

REM Wait a moment for processes to fully stop
timeout /t 2 /nobreak >nul

echo Backend stopped.
echo.
echo Starting backend again...
call start_enhanced_backend.bat 