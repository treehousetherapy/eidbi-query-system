@echo off
echo === Simple Google Cloud Authentication Setup ===
echo.

REM Check if gcloud is installed
where gcloud >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: gcloud CLI is not installed!
    echo Please install Google Cloud SDK from: https://cloud.google.com/sdk/docs/install
    echo.
    pause
    exit /b 1
)

echo This will set up Google Cloud authentication using your personal Google account.
echo This is the simplest method for local development.
echo.
pause

REM Login with Google account
echo Logging in to Google Cloud...
gcloud auth login

REM Set application default credentials
echo.
echo Setting up application default credentials...
gcloud auth application-default login

REM Set the project
echo.
echo Setting active project...
gcloud config set project lyrical-ward-454915-e6

REM Update the batch file to use real responses
echo.
echo Updating start_enhanced_backend.bat to use real AI responses...

REM Create a temporary PowerShell script to update the batch file
echo $content = Get-Content "start_enhanced_backend.bat" -Raw > temp_update.ps1
echo $content = $content -replace 'set USE_MOCK_EMBEDDINGS=true', 'set USE_MOCK_EMBEDDINGS=false' >> temp_update.ps1
echo $content = $content -replace 'set MOCK_LLM_RESPONSES=true', 'set MOCK_LLM_RESPONSES=false' >> temp_update.ps1
echo Set-Content "start_enhanced_backend.bat" $content -Encoding ASCII >> temp_update.ps1

powershell -ExecutionPolicy Bypass -File temp_update.ps1
del temp_update.ps1

echo.
echo === Setup Complete! ===
echo.
echo Your Google Cloud authentication is now configured.
echo The system will use your personal Google account credentials.
echo.
echo Next steps:
echo 1. Run start_enhanced_backend.bat to start the backend with real AI responses
echo 2. The system will now use Google Cloud's Vertex AI instead of mock responses
echo.
echo Note: These credentials are stored in your user profile and will expire after a few hours.
echo You may need to run 'gcloud auth application-default login' again if they expire.
echo.
pause 