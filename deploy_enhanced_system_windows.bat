@echo off
REM Enhanced EIDBI System - Windows Deployment Script
echo =================================================================
echo Enhanced EIDBI System - Windows Deployment
echo =================================================================

REM Check if we're in the correct directory
if not exist "backend\main.py" (
    echo ERROR: Please run this script from the project root directory
    echo Expected to find backend\main.py
    pause
    exit /b 1
)

REM Create logs directory
if not exist "logs" mkdir logs

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo Warning: No virtual environment found at .venv
    echo Using system Python...
)

REM Install/verify enhanced dependencies
echo.
echo Installing enhanced system dependencies...
pip install pandas>=2.0.0 schedule>=1.2.0

REM Check if installation was successful
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Create data directories
echo.
echo Setting up data directories...
if not exist "backend\data" mkdir backend\data
if not exist "backend\data\structured" mkdir backend\data\structured

REM Run the enhanced system
echo.
echo =================================================================
echo Starting Enhanced EIDBI System...
echo =================================================================
echo.
echo Enhanced capabilities include:
echo   📊 Structured data ingestion and management
echo   🕷️ Automated provider directory scraping  
echo   🔍 Enhanced vector search with improved coverage
echo   📝 Intelligent prompt engineering with fallback handling
echo   ⏰ Automated data refresh scheduling
echo.
echo System will be available at: http://localhost:8080
echo Web interface will be available at: http://localhost:8080/docs
echo.
echo Press Ctrl+C to stop the system
echo =================================================================

python run_enhanced_production.py

REM If we get here, the system has stopped
echo.
echo Enhanced EIDBI System has stopped.
pause 