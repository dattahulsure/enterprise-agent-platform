@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)
if not exist .venv %PY% -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements-minimal.txt
if errorlevel 1 (pause & exit /b 1)
echo WARNING: LangGraph not installed. Agent execution uses an explicitly labeled sequential fallback.
start "" http://127.0.0.1:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
