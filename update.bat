@echo off
REM Updates the app by downloading the latest ZIP from GitHub.
REM Does NOT require Git to be installed.
cd /d "%~dp0"

echo ================================================
echo  Budget Tracker - Update
echo ================================================
echo.
echo Downloading latest version from GitHub...

powershell -Command "Invoke-WebRequest -Uri 'https://github.com/lifeshortcuts/budgetapp/archive/refs/heads/main.zip' -OutFile '%TEMP%\budgetapp-update.zip'"

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Download failed. Please check your internet connection and try again.
    pause
    exit /b 1
)

echo Extracting...
powershell -Command "if (Test-Path '%TEMP%\budgetapp-update') { Remove-Item '%TEMP%\budgetapp-update' -Recurse -Force }; Expand-Archive -Path '%TEMP%\budgetapp-update.zip' -DestinationPath '%TEMP%\budgetapp-update'"

echo Applying update (your data is untouched)...
robocopy "%TEMP%\budgetapp-update\budgetapp-main" "%~dp0" /E /XD "data" ".venv" "__pycache__" /XF "*.db" "*.csv" /NFL /NDL /NJH /NJS >nul

echo Installing any new requirements...
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q

echo Cleaning up...
rmdir /s /q "%TEMP%\budgetapp-update" 2>nul
del /f /q "%TEMP%\budgetapp-update.zip" 2>nul

echo.
echo ================================================
echo  Update complete! Run run.bat to start the app.
echo ================================================
pause
