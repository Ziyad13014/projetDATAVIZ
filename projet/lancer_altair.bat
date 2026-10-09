@echo off
cd /d "%~dp0"
python -m streamlit run app_altair/app.py
pause
