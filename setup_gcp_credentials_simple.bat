@echo off
echo === Google Cloud Credentials Setup (Service Account) ===
echo.

REM Configuration
set PROJECT_ID=lyrical-ward-454915-e6
set SERVICE_ACCOUNT=id-eidbi-service-account@lyrical-ward-454915-e6.iam.gserviceaccount.com
set KEY_FILE=eidbi-service-account-key.json

REM Check if gcloud is installed
where gcloud >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: gcloud CLI is not installed!
    echo Please install Google Cloud SDK from: https://cloud.google.com/sdk/docs/install
    pause
    exit /b 1
)

echo Found gcloud CLI installation.
echo.

REM Check current authentication
echo Checking current authentication...
for /f "tokens=*" %%i in ('gcloud auth list --filter=status:ACTIVE --format="value(account)" 2^>nul') do set CURRENT_ACCOUNT=%%i

if defined CURRENT_ACCOUNT (
    echo Currently authenticated as: %CURRENT_ACCOUNT%
    echo.
    choice /C YN /M "Do you want to use this account"
    if errorlevel 2 (
        echo Please run 'gcloud auth login' to authenticate with a different account
        pause
        exit /b 1
    )
) else (
    echo No active authentication found.
    echo Please authenticate with Google Cloud...
    gcloud auth login
)

REM Set the project
echo.
echo Setting active project to: %PROJECT_ID%
gcloud config set project %PROJECT_ID%

REM Check if service account key already exists
if exist "%KEY_FILE%" (
    echo.
    echo Service account key already exists at: %KEY_FILE%
    choice /C YN /M "Do you want to create a new key"
    if errorlevel 2 goto :UseExistingKey
    del /f "%KEY_FILE%"
)

REM Create service account key
echo.
echo Creating service account key...
gcloud iam service-accounts keys create "%KEY_FILE%" --iam-account=%SERVICE_ACCOUNT% --project=%PROJECT_ID%

if not exist "%KEY_FILE%" (
    echo.
    echo ERROR: Failed to create service account key!
    echo.
    echo This might be because:
    echo 1. You don't have permission to create keys for this service account
    echo 2. The service account doesn't exist
    echo 3. You've reached the key limit for this service account
    echo.
    echo Alternative: Run setup_gcp_auth_simple.bat to use your personal Google account
    pause
    exit /b 1
)

echo Service account key created successfully!

:UseExistingKey
REM Update start_enhanced_backend.bat
echo.
echo Updating start_enhanced_backend.bat...

REM First, add GOOGLE_APPLICATION_CREDENTIALS if not present
findstr /C:"GOOGLE_APPLICATION_CREDENTIALS" start_enhanced_backend.bat >nul
if %errorlevel% neq 0 (
    REM Create a temporary file with the updated content
    powershell -Command "(Get-Content 'start_enhanced_backend.bat') -replace '(set ENABLE_QUERY_CACHE=true)', '$1`r`nset GOOGLE_APPLICATION_CREDENTIALS=%%~dp0%KEY_FILE%' | Set-Content 'start_enhanced_backend.bat' -Encoding ASCII"
)

REM Disable mock mode
powershell -Command "(Get-Content 'start_enhanced_backend.bat') -replace 'set USE_MOCK_EMBEDDINGS=true', 'set USE_MOCK_EMBEDDINGS=false' | Set-Content 'start_enhanced_backend.bat' -Encoding ASCII"
powershell -Command "(Get-Content 'start_enhanced_backend.bat') -replace 'set MOCK_LLM_RESPONSES=true', 'set MOCK_LLM_RESPONSES=false' | Set-Content 'start_enhanced_backend.bat' -Encoding ASCII"

echo Updated start_enhanced_backend.bat

REM Test authentication
echo.
echo Testing authentication...
set GOOGLE_APPLICATION_CREDENTIALS=%~dp0%KEY_FILE%
python -c "import google.auth; c,p = google.auth.default(); print('Authentication successful! Project:', p)" 2>nul
if %errorlevel% neq 0 (
    echo Authentication test failed. Check if google-auth Python package is installed.
    echo Run: pip install google-auth
)

REM Add to .gitignore
findstr /C:"%KEY_FILE%" .gitignore >nul 2>&1
if %errorlevel% neq 0 (
    echo.>> .gitignore
    echo # Google Cloud service account key>> .gitignore
    echo %KEY_FILE%>> .gitignore
    echo Added %KEY_FILE% to .gitignore
)

echo.
echo === Setup Complete! ===
echo.
echo Google Cloud credentials have been configured!
echo.
echo Next steps:
echo 1. Run start_enhanced_backend.bat to start the backend with real AI responses
echo 2. The system will now use Google Cloud's Vertex AI instead of mock responses
echo.
echo IMPORTANT: Keep %KEY_FILE% secure and never commit it to git!
echo.
pause 