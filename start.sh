#!/bin/bash
# ====================================================================================
#   POD STARTUP SCRIPT
# ====================================================================================
# This script is executed when the pod's container starts.
# It handles the initialization of services needed for development.

set -e

echo "--- Initializing Pod Services ---"

# --- 1. Start the SSH Server ---
# The -D flag runs sshd in the foreground without detaching
echo "[INFO] Starting SSH server..."
/usr/sbin/sshd -D &
echo "[SUCCESS] SSH server started."

# --- 2. Launch Jupyter Lab ---
# We will launch Jupyter Lab from the /workspace directory, which is where
# the network volume will be mounted.
echo "[INFO] Starting Jupyter Lab server..."
jupyter lab --port=8888 --ip=0.0.0.0 --allow-root --no-browser --ServerApp.token='' --ServerApp.password=''
echo "[INFO] Jupyter Lab server has stopped."

# Keep the container running if Jupyter stops for any reason
tail -f /dev/null
