#!/bin/bash
# entrypoint.sh (v3 - Simplified)
# This script is for the serverless worker. It assumes the network volume
# is mounted at /runpod-volume and contains a fully provisioned environment.

# --- Configuration ---
VENV_PATH="/runpod-volume/venv"

echo "============================================================"
echo "      STARTING SIMPLIED WORKER ENTRYPOINT SCRIPT"
echo "============================================================"

# --- 1. Activate Virtual Environment ---
echo "--- STEP 1: ACTIVATING PYTHON VIRTUAL ENVIRONMENT ---"
if [ -f "${VENV_PATH}/bin/activate" ]; then
    source "${VENV_PATH}/bin/activate"
    echo "[SUCCESS] Virtual environment activated."
    echo "Using Python: $(which python)"
else
    echo "[FATAL] Virtual environment not found at ${VENV_PATH}."
    echo "The server cannot start. Ensure the volume is provisioned correctly."
    exit 1
fi
echo ""

# --- 2. Start the Server ---
echo "--- STEP 2: LAUNCHING UVICORN SERVER ---"
echo "Executing command: uvicorn app_sd_volume:app --host 0.0.0.0 --port 8000"
echo "============================================================"

# Use the PORT environment variable provided by RunPod, defaulting to 8000.
exec uvicorn app_sd_volume:app --host 0.0.0.0 --port "${PORT:-8000}"

echo "[FATAL ERROR] 'exec' command failed."
exit 126
