@echo off
echo Starting Release Notes Processor Frontend...
echo.

cd /d %~dp0frontend

echo Installing dependencies (if needed)...
call npm install

echo.
echo Starting React dev server on http://localhost:3000
echo Press Ctrl+C to stop the server
echo.

call npm start

pause
