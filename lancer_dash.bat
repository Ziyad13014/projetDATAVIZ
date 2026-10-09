@echo off
cd /d "%~dp0projet"
start "" http://127.0.0.1:8050
python app_dash/app.py
pause
