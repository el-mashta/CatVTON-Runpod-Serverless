#!/bin/bash
set -e

# This script is the entrypoint for a RunPod worker that uses a network volume
# to store its Python environment, source code, and models.

# --- Configuration ---
NETWORK_VOLUME_PATH="/runpod-volume"
VENV_PATH="$NETWORK_VOLUME_PATH/venv"
CODE_PATH="$NETWORK_VOLUME_PATH/CatVTON"
REQUIREMENTS_FILE="$CODE_PATH/requirements.txt"
APP_FILE="/app/app_sd_volume.py" # The app server is in the image itself

echo "--- RunPod Worker Entrypoint ---"
echo "Network Volume Path: $NETWORK_VOLUME_PATH"
echo "Virtual Env Path: $VENV_PATH"
echo "Application Code Path: $CODE_PATH"

# --- Step 1: Check if the virtual environment is already set up ---
if [ -d "$VENV_PATH" ]; then
    echo "Virtual environment found at $VENV_PATH. Skipping installation."
else
    echo "Virtual environment not found. Starting first-time setup..."
    
    # Check if the CatVTON source code and requirements file exist
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        echo "FATAL: requirements.txt not found at $REQUIREMENTS_FILE."
        echo "Please ensure the CatVTON source code is synced to the network volume."
        exit 1
    fi
    
    echo "Creating Python 3.9 virtual environment with uv..."
    uv venv "$VENV_PATH" --python 3.9
    
    echo "Activating virtual environment to install dependencies..."
    # We need to source the activator to make `pip` available in the current shell
    source "$VENV_PATH/bin/activate"
    
    echo "Installing dependencies from $REQUIREMENTS_FILE..."
    # Use the venv's pip to install packages into the correct location
    uv pip install -r "$REQUIREMENTS_FILE"
    
    echo "First-time setup complete. Environment is ready."
fi

# --- Step 2: Activate the environment and launch the application ---
echo "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

echo "All checks passed. Launching FastAPI server..."
# Use uvicorn to run the FastAPI application
# The application file is inside the container at /app/app_sd_volume.py
exec uvicorn app_sd_volume:app --host 0.0.0.0 --port 8000
