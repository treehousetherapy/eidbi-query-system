@echo off
echo Enhanced EIDBI System Deployment
echo ==================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

echo Found Python version:
python --version

REM Check if we're in the right directory
if not exist "backend\main.py" (
    echo ERROR: Please run this script from the eidbi-query-system root directory
    pause
    exit /b 1
)

echo Creating backup...
set BACKUP_DIR=backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set BACKUP_DIR=%BACKUP_DIR: =0%
mkdir "%BACKUP_DIR%" 2>nul

if exist "backend\main.py" copy "backend\main.py" "%BACKUP_DIR%\" >nul
if exist "backend\requirements.txt" copy "backend\requirements.txt" "%BACKUP_DIR%\" >nul
if exist ".env" copy ".env" "%BACKUP_DIR%\" >nul

echo Backup created in %BACKUP_DIR%

echo Installing dependencies...
python -m pip install --upgrade pip
cd backend
pip install -r requirements.txt
cd ..

echo Creating environment configuration...
if not exist ".env" (
    echo Creating .env file...
    (
        echo # Enhanced EIDBI System Configuration
        echo.
        echo # GCP Configuration
        echo GCP_PROJECT_ID=lyrical-ward-454915-e6
        echo GCP_REGION=us-central1
        echo GCP_BUCKET_NAME=your-bucket-name
        echo.
        echo # Caching Configuration
        echo ENABLE_EMBEDDING_CACHE=true
        echo ENABLE_QUERY_CACHE=true
        echo EMBEDDING_CACHE_SIZE=100
        echo QUERY_CACHE_SIZE=50
        echo.
        echo # API Configuration
        echo API_HOST=0.0.0.0
        echo API_PORT=8000
        echo API_DEBUG=false
        echo.
        echo # Testing Configuration
        echo TESTING_MODE=false
    ) > .env
    echo Created .env file with default configuration
    echo WARNING: Please update GCP_BUCKET_NAME and other settings as needed
)

echo Creating required directories...
if not exist "logs" mkdir logs
if not exist "test_results" mkdir test_results
if not exist "feedback_data" mkdir feedback_data

echo Stopping existing backend...
taskkill /f /im python.exe >nul 2>&1

echo Starting enhanced backend...
cd backend
start "Enhanced EIDBI Backend" python main.py
cd ..

echo Waiting for backend to start...
timeout /t 10 /nobreak >nul

echo Verifying deployment...
python verify_deployment.py --report deployment_report.txt

echo.
echo ========================================
echo Enhanced EIDBI System Deployment Complete!
echo ========================================
echo.
echo Deployment Summary:
echo - Backend URL: http://localhost:8000
echo - Version: 2.0.0 (Enhanced)
echo - Backup: %BACKUP_DIR%
echo.
echo New Features Available:
echo - Advanced Caching System
echo - Feedback Loops
echo - Multi-Source Data Integration
echo - Enhanced Prompt Engineering
echo - Automated Testing
echo.
echo Key Endpoints:
echo - Health Check: http://localhost:8000/health
echo - Enhanced Query: http://localhost:8000/query
echo - Submit Feedback: http://localhost:8000/feedback
echo - Cache Stats: http://localhost:8000/cache-stats
echo - Data Sources: http://localhost:8000/data-sources/status
echo.
echo Deployment completed successfully!
pause 