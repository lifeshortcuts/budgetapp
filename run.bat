@echo off
REM Launch the Budget Tracker
cd /d "%~dp0"
call .venv\Scripts\activate.bat
streamlit run app.py
