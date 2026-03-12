@echo off
echo Starting Release Notes Processor Backend...
echo.

cd /d %~dp0
call venv\Scripts\activate

echo Starting FastAPI server on http://localhost:8000
echo Press Ctrl+C to stop the server
echo.

python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

pause
