@echo off
echo ========================================
echo Starting Beast Carnival...
echo ========================================
echo.

echo [1/2] Starting Redis (if not running)...
start /B redis-server
timeout /t 2 /nobreak >nul

echo [2/2] Starting Backend (will auto-start Frontend)...
cd backend
start cmd /k "python -u run.py"

echo.
echo ========================================
echo Backend: http://localhost:1998
echo Frontend: http://localhost:4399
echo ========================================
echo.
echo Note: Frontend will be started automatically by run.py
echo.
pause

