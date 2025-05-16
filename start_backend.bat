@echo off
echo Starting EIDBI Query System Backend...
cd %~dp0
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 