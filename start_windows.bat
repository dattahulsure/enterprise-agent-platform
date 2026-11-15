@echo off
cd /d "%~dp0"
echo Starting Enterprise Agent Platform...
where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)
%PY% --version
if errorlevel 1 (
 echo Python is not installed. Install Python 3.11 or 3.12 from https://www.python.org/downloads/
 pause
 exit /b 1
)
if not exist .venv (
 echo Creating Python environment...
 %PY% -m venv .venv
 if errorlevel 1 (pause & exit /b 1)
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if errorlevel 1 (
 echo Full installation failed. Check internet connection or Python version.
 echo You can optionally run start_minimal_windows.bat for fallback mode.
 pause
 exit /b 1
)
echo.
echo OPEN IN YOUR BROWSER: http://127.0.0.1:8000
echo Leave this window open while presenting.
start "" http://127.0.0.1:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
