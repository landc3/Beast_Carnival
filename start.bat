@echo off
echo Starting Beast Carnival...

echo Starting Redis (if not running)...
start /B redis-server

echo Starting Backend...
cd backend
start cmd /k "python run.py"

timeout /t 3

echo Starting Frontend...
cd ../frontend
start cmd /k "npm run dev"

echo.
echo Backend: http://localhost:1998
echo Frontend: http://localhost:4399
echo.
pause

