@echo off
echo Starting Enhanced EIDBI Backend (Version 2.0.0)...
echo.

REM Kill any existing Python processes on port 8000
echo Checking for existing processes on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo Killing process %%a
    taskkill /PID %%a /F 2>nul
)

REM Set environment variables
echo Setting environment variables...
set USE_MOCK_EMBEDDINGS=false
set MOCK_LLM_RESPONSES=false
set ENABLE_EMBEDDING_CACHE=true
set ENABLE_QUERY_CACHE=true

REM Change to backend directory
cd /d "%~dp0backend"

REM Start the server
echo.
echo Starting server on http://localhost:8000
echo Press Ctrl+C to stop the server
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload 