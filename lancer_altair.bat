@echo off
cd /d "%~dp0projet"
python -m streamlit run app_altair/app.py
pause
