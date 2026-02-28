@echo off
REM One-time setup for Windows
cd /d "%~dp0"
echo Setting up Budget Tracker...
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r requirements.txt
echo.
echo Done! Double-click run.bat to start the app.
pause
