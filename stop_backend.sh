#!/bin/bash
PID_FILE="$HOME/backend.pid"
PATTERN="uvicorn main:app"

echo "Stopping backend process..."

# First try to use the PID file if it exists and is readable
if [ -f "$PID_FILE" ] && [ -r "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        echo "Found backend process with PID $PID from PID file. Terminating..."
        kill "$PID" 2>/dev/null
        # Give it a moment to terminate gracefully
        sleep 2
        # If it's still running, force kill it
        if kill -0 "$PID" 2>/dev/null; then
            echo "Process still running, force killing..."
            kill -9 "$PID" 2>/dev/null
        fi
        rm -f "$PID_FILE" 2>/dev/null
        echo "Backend stopped and PID file cleaned up."
        exit 0
    else
        echo "PID file exists but process not found, cleaning up..."
        rm -f "$PID_FILE" 2>/dev/null
    fi
else
    echo "No PID file found or not readable, searching by process pattern..."
fi

# Fallback: try pattern matching
echo "Looking for backend processes matching '$PATTERN'..."
PIDS=$(pgrep -f "$PATTERN")
if [ -n "$PIDS" ]; then
    echo "Found running backend processes: $PIDS"
    for pid in $PIDS; do
        # Check if we own the process
        if ps -o uid= -p "$pid" 2>/dev/null | grep -q "^$(id -u)$"; then
            if kill "$pid" 2>/dev/null; then
                echo "Successfully terminated process $pid"
                sleep 1
                # Check if it's still running and force kill if needed
                if kill -0 "$pid" 2>/dev/null; then
                    kill -9 "$pid" 2>/dev/null && echo "Force killed process $pid"
                fi
            else
                echo "Failed to terminate process $pid"
            fi
        else
            echo "Process $pid is owned by another user, skipping..."
            echo "You may need to manually run: sudo kill $pid"
        fi
    done
    echo "Backend termination attempted."
else
    echo "No running backend process found."
fi