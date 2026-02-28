@echo off
REM Pull latest updates from GitHub (requires Git)
cd /d "%~dp0"
echo Downloading latest updates...
git pull
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q
echo.
echo Update complete! Run run.bat to start the app.
pause
