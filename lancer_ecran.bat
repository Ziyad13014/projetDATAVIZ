@echo off
cd /d "%~dp0projet"
start "" http://127.0.0.1:8052
python app_dash/ecran.py
pause
