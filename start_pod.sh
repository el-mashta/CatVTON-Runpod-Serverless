#!/bin/bash
# start_pod.sh
# Entrypoint for the development pod.
# Starts the SSH server in the background and then launches the FastAPI server
# in the foreground, using the environment on the attached network volume.

echo "============================================================"
echo "      STARTING DEVELOPMENT POD ENTRYPOINT SCRIPT"
echo "============================================================"

# --- 1. Start SSH Server ---
echo "--- STEP 1: STARTING SSH DAEMON ---"
/usr/sbin/sshd
echo "[SUCCESS] SSH Daemon started in the background."
echo ""

# --- 2. Activate Virtual Environment ---
VENV_PATH="/workspace/venv"
echo "--- STEP 2: ACTIVATING PYTHON VIRTUAL ENVIRONMENT ---"
if [ -f "${VENV_PATH}/bin/activate" ]; then
    echo "Activating venv from ${VENV_PATH}..."
    source "${VENV_PATH}/bin/activate"
    echo "[SUCCESS] Virtual environment activated."
    echo "Python executable: $(which python)"
else
    echo "[WARNING] Virtual environment not found at ${VENV_PATH}."
    echo "The server will likely fail. Please ensure the venv is set up correctly on the volume."
fi
echo ""

# --- 3. Launch the Server ---
echo "--- STEP 3: LAUNCHING UVICORN SERVER ---"
echo "Changing directory to /app where app_sd_volume.py is located."
cd /app
echo "Executing command: uvicorn app_sd_volume:app --host 0.0.0.0 --port 8000"
echo "Server logs will follow:"
echo "============================================================"

# Use the PORT environment variable if set, otherwise default to 8000.
# The `exec` command replaces the shell process with the uvicorn process,
# ensuring it's the main process and receives signals correctly.
exec uvicorn app_sd_volume:app --host 0.0.0.0 --port "${PORT:-8000}"

echo "[FATAL ERROR] 'exec' command failed. The server did not start."
exit 126
