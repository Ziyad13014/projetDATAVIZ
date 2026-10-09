@echo off
cd /d "%~dp0"
start "" http://127.0.0.1:8050
python app_dash/app.py
pause
