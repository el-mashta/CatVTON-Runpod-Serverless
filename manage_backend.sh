#!/bin/bash
# A robust, unified script to manage the FastAPI backend using Gunicorn.
#
# USAGE: ./manage_backend.sh {start|stop|restart|status|logs}

# --- Configuration ---
# Get the absolute path of the directory where this script resides.
# This makes the script runnable from any location.
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

# Define paths relative to the script's location.
APP_DIR="$BASE_DIR/python_backend"
# Use the python executable from the venv to run gunicorn as a module.
PYTHON_EXEC="$APP_DIR/.venv/bin/python"
GUNICORN_MODULE="gunicorn"
LOG_DIR="/home/stephanie"
LOG_FILE="$LOG_DIR/backend.log"
PID_FILE="$LOG_DIR/backend.pid"

# The main FastAPI app object (e.g., for `main.py`, it's `main:app`).
APP_MODULE="main:app"

# --- Gunicorn Settings ---
GUNICORN_WORKERS=3
GUNICORN_WORKER_CLASS="uvicorn.workers.UvicornWorker"
GUNICORN_BIND="0.0.0.0:4009"
GUNICORN_LOG_LEVEL="info"

# --- Helper Functions ---
# Create the log directory if it doesn't exist.
mkdir -p "$LOG_DIR"

# --- Script Actions ---
case "$1" in
    start)
        echo "Starting backend server..."
        
        if [ -f "$PID_FILE" ] && ps -p $(cat "$PID_FILE") > /dev/null; then
            echo "Server is already running (PID: $(cat "$PID_FILE"))."
            exit 1
        fi

        # Verify that the python executable exists and is runnable.
        if [ ! -x "$PYTHON_EXEC" ]; then
            echo "Error: Python executable not found at $PYTHON_EXEC"
            echo "Please ensure your virtual environment is set up correctly in '$APP_DIR/.venv'"
            exit 1
        fi
        
        # Change to the app directory before starting. This is crucial.
        cd "$APP_DIR" || { echo "Error: Could not change to directory $APP_DIR"; exit 1; }
        
        echo "--- Starting Gunicorn at $(date) ---" >> "$LOG_FILE"
        # Execute gunicorn as a module using nohup to ensure all stdout/stderr are captured.
        # The final '&' sends it to the background.
        nohup "$PYTHON_EXEC" -m "$GUNICORN_MODULE" \
            --workers "$GUNICORN_WORKERS" \
            --worker-class "$GUNICORN_WORKER_CLASS" \
            --bind "$GUNICORN_BIND" \
            --log-level "$GUNICORN_LOG_LEVEL" \
            --access-logfile "$LOG_FILE" \
            --error-logfile "$LOG_FILE" \
            "$APP_MODULE" >> "$LOG_FILE" 2>&1 &
        
        # Capture the PID of the last backgrounded process.
        echo $! > "$PID_FILE"
        
        echo "Server started. Logs are being written to $LOG_FILE"
        ;;
        
    stop)
        echo "Stopping backend server..."
        
        if [ ! -f "$PID_FILE" ]; then
            echo "Server is not running (no PID file found)."
            exit 0
        fi
        
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null; then
            echo "Sending SIGTERM to process $PID..."
            kill "$PID"
            for i in {1..10}; do
                if ! ps -p "$PID" > /dev/null; then
                    echo "Server stopped gracefully."
                    rm -f "$PID_FILE"
                    exit 0
                fi
                sleep 1
            done
            echo "Server did not stop gracefully. Forcing shutdown (SIGKILL)..."
            kill -9 "$PID"
            rm -f "$PID_FILE"
        else
            echo "Server is not running (stale PID file found). Cleaning up."
            rm -f "$PID_FILE"
        fi
        ;;
        
    restart)
        echo "Restarting backend server..."
        "$0" stop
        sleep 2
        "$0" start
        ;;
        
    status)
        if [ -f "$PID_FILE" ] && ps -p $(cat "$PID_FILE") > /dev/null; then
            echo "Server is running (PID: $(cat "$PID_FILE"))."
        else
            echo "Server is not running."
        fi
        ;;
    
    logs)
        echo "Tailing logs from $LOG_FILE..."
        tail -f "$LOG_FILE"
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac

exit 0
