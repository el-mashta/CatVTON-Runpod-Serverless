#!/bin/bash
# entrypoint.sh (Final, Path-Correcting Version)
# This script robustly finds the Python interpreter by reading the symlink
# from the venv and dynamically correcting its absolute path to match the
# serverless worker's mount point.

# --- Configuration ---
VOLUME_PATH="/runpod-volume"
VENV_PATH="${VOLUME_PATH}/venv"
PYTHON_SYMLINK="${VENV_PATH}/bin/python"
TIMEOUT_SECONDS=30
CORRECT_PYTHON_EXEC=""

echo "============================================================"
echo "  STARTING PATH-CORRECTING WORKER ENTRYPOINT SCRIPT"
echo "============================================================"

# --- 1. Wait for the Python Symlink to Appear ---
echo "--- STEP 1: WAITING FOR PYTHON SYMLINK AT ${PYTHON_SYMLINK} ---"
elapsed=0
while [ ! -L "${PYTHON_SYMLINK}" ]; do
  if [ "$elapsed" -ge "$TIMEOUT_SECONDS" ]; then
    echo "[FATAL ERROR] Timed out waiting for the symlink at ${PYTHON_SYMLINK}."
    exit 1
  fi
  echo "Symlink not found. Waiting... (${elapsed}s / ${TIMEOUT_SECONDS}s)"
  sleep 2
  elapsed=$((elapsed + 2))
done
echo "[SUCCESS] Python symlink found."

# --- 2. Read the (potentially broken) symlink target ---
echo ""
echo "--- STEP 2: READING SYMLINK TARGET ---"
# Use `readlink` (no -f) to get the path stored in the symlink, even if it's broken.
BROKEN_PATH=$(readlink "${PYTHON_SYMLINK}")
if [ -z "$BROKEN_PATH" ]; then
    echo "[FATAL ERROR] Symlink at ${PYTHON_SYMLINK} is empty or could not be read."
    exit 1
fi
echo "Symlink target path is: ${BROKEN_PATH}"

# --- 3. Correct the Path for the Serverless Environment ---
echo ""
echo "--- STEP 3: CORRECTING THE PATH ---"
# This is the crucial step. We replace the incorrect '/workspace/' prefix
# with the correct '/runpod-volume/' prefix for the serverless environment.
CORRECT_PYTHON_EXEC=${BROKEN_PATH/#\/workspace\//\/runpod-volume\/}
echo "Corrected path for serverless worker is: ${CORRECT_PYTHON_EXEC}"

# --- 4. Verify the Corrected Path ---
echo ""
echo "--- STEP 4: VERIFYING CORRECTED PATH ---"
if [ ! -f "$CORRECT_PYTHON_EXEC" ]; then
    echo "[FATAL ERROR] The corrected path '${CORRECT_PYTHON_EXEC}' does not exist or is not a file."
    echo "This means the Python toolchain is missing from the expected location on the volume."
    echo "Please ensure the 'python-toolchains' directory exists in the root of your network volume."
    exit 1
fi
echo "[SUCCESS] Corrected path points to a valid executable."

# --- 5. Start the Server ---
echo ""
echo "--- STEP 5: LAUNCHING UVICORN SERVER ---"
echo "Executing command: ${CORRECT_PYTHON_EXEC} -m uvicorn app_sd_volume:app --host 0.0.0.0 --port 8000"
echo "============================================================"

# Use the PORT environment variable provided by RunPod, defaulting to 8000 for local testing.
exec "$CORRECT_PYTHON_EXEC" -m uvicorn app_sd_volume:app --host 0.0.0.0 --port "${PORT:-8000}"

echo "[FATAL ERROR] 'exec' command failed."
exit 126