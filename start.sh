#!/bin/bash

echo "Starting Beast Carnival..."

# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis..."
    redis-server &
    sleep 2
fi

# Start Backend
echo "Starting Backend..."
cd backend
python -u run.py &
BACKEND_PID=$!
cd ..

echo ""
echo "Backend: http://localhost:1998"
echo "Frontend: http://localhost:4399"
echo ""
echo "Note: Frontend will be started automatically by run.py"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user interrupt
trap "kill $BACKEND_PID; exit" INT
wait


















