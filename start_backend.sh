#!/bin/bash
# Uses the current user's home directory for logs and PIDs
LOG_FILE="$HOME/backend.log"
PID_FILE="$HOME/backend.pid"

# Create log file and start logging
echo "--- Starting Python backend at $(date) ---" > "$LOG_FILE" 2>/dev/null || {
    echo "Warning: Cannot write to log file $LOG_FILE, continuing without logging"
    LOG_FILE="/dev/null"
}

echo "Changing to python_backend directory" >> "$LOG_FILE"
cd "$(dirname "$0")/python_backend" || {
    echo "Error: Cannot change to python_backend directory" | tee -a "$LOG_FILE"
    exit 1
}

echo "Activating virtual environment" >> "$LOG_FILE"
source .venv/bin/activate || {
    echo "Error: Cannot activate virtual environment" | tee -a "$LOG_FILE"
    exit 1
}

echo "Starting server with command: python run_server.py" >> "$LOG_FILE"
python run_server.py >> "$LOG_FILE" 2>&1 &
BACKEND_PID=$!


# Try to save PID, but don't fail if we can't
if echo "$BACKEND_PID" > "$PID_FILE" 2>/dev/null; then
    echo "Backend started with PID $BACKEND_PID" >> "$LOG_FILE" 2>/dev/null
    echo "Backend started with PID $BACKEND_PID (saved to $PID_FILE)"
else
    echo "Backend started with PID $BACKEND_PID (could not save PID file)"
fi