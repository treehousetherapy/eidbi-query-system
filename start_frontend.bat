@echo off
echo Starting EIDBI Query System Frontend...
cd %~dp0
cd frontend
python -m streamlit run streamlit_app.py 