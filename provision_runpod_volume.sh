#!/bin/bash
# ==============================================================================
#   provision_runpod_volume.sh - Master Setup Script (Unified Paths)
# ==============================================================================
# This script performs all necessary one-time setup tasks to prepare the
# RunPod Network Volume. It assumes the volume is mounted at /runpod-volume.
#
# It is designed to be idempotent: safe to run multiple times.
# ==============================================================================

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- [STEP 0/8] CONFIGURING ENVIRONMENT ---"
# All paths now use the final /runpod-volume mount point.
export VOLUME_PATH="/runpod-volume"
export UV_CACHE_DIR="${VOLUME_PATH}/uv-cache"
export UV_PYTHON_INSTALL_DIR="${VOLUME_PATH}/python-toolchains"
export MODELS_DIR="${VOLUME_PATH}/models"
export CATVTON_DIR="${VOLUME_PATH}/CatVTON"
export VENV_PATH="${VOLUME_PATH}/venv"
export CATVTON_REPO_URL="https://github.com/zhengchong/CatVTON.git"
export HF_HOME="${MODELS_DIR}"
export HUGGINGFACE_HUB_CACHE="${MODELS_DIR}"

# Ensure the working directory is the volume root.
cd "${VOLUME_PATH}"
echo "Working directory set to: $(pwd)"
echo "uv cache is now at: ${UV_CACHE_DIR}"
echo "uv Python installs will be in: ${UV_PYTHON_INSTALL_DIR}"
echo ""

echo "--- [STEP 1/8] INSTALLING UV PACKAGE MANAGER ---"
if ! command -v uv &> /dev/null; then
    echo "uv not found, installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.cargo/env"
    echo "uv installed successfully."
else
    echo "uv is already installed. Skipping."
fi
echo ""

echo "--- [STEP 2/8] CLONING CatVTON REPOSITORY ---"
if [ ! -d "${CATVTON_DIR}" ]; then
    echo "Cloning CatVTON repository..."
    git clone "${CATVTON_REPO_URL}" "${CATVTON_DIR}"
    echo "Repository cloned successfully."
else
    echo "CatVTON directory already exists. Skipping clone."
fi
echo ""

echo "--- [STEP 3/8] INSTALLING PORTABLE PYTHON 3.9 ---"
echo "Installing Python 3.9 onto the network volume..."
uv python install 3.9
echo "Python 3.9 installed successfully."
echo ""

echo "--- [STEP 4/8] CREATING VIRTUAL ENVIRONMENT ---"
PORTABLE_PYTHON_EXEC=$(find "${UV_PYTHON_INSTALL_DIR}" -type f -name "python" | head -n 1)
if [ -z "$PORTABLE_PYTHON_EXEC" ]; then
    echo "FATAL: Could not find the portable Python executable. Exiting."
    exit 1
fi
echo "Found portable Python at: ${PORTABLE_PYTHON_EXEC}"
echo "Creating virtual environment at ${VENV_PATH}..."
uv venv "${VENV_PATH}" --python "${PORTABLE_PYTHON_EXEC}"
echo "Virtual environment created successfully."
echo ""

echo "--- [STEP 5/8] INSTALLING PYTHON DEPENDENCIES ---"
echo "Activating venv and installing requirements..."
source "${VENV_PATH}/bin/activate"
# Install huggingface-hub first for the downloader.
uv pip install huggingface-hub
# Install all project dependencies.
uv pip install -r "${CATVTON_DIR}/requirements.txt"
echo "All Python dependencies installed successfully."
echo ""

echo "--- [STEP 6/8] DOWNLOADING ML MODELS ---"
echo "Downloading models to ${MODELS_DIR}..."
mkdir -p "${MODELS_DIR}"
huggingface-cli download runwayml/stable-diffusion-inpainting --local-dir "${MODELS_DIR}/stable-diffusion-inpainting" --local-dir-use-symlinks False
huggingface-cli download zhengchong/CatVTON --local-dir "${MODELS_DIR}/CatVTON" --local-dir-use-symlinks False
echo "ML models downloaded successfully."
echo ""

echo "--- [STEP 7/8] OPTIMIZING MODELS ---"
echo "Running model optimization script..."
OPTIMIZE_SCRIPT="${VOLUME_PATH}/optimize_models.py"
if [ -f "$OPTIMIZE_SCRIPT" ]; then
    python "$OPTIMIZE_SCRIPT"
    echo "Model optimization complete."
else
    echo "WARNING: optimize_models.py not found at ${OPTIMIZE_SCRIPT}. Skipping optimization."
fi
echo ""

echo "--- [STEP 8/8] VERIFICATION ---"
echo "Final check of the directory structure:"
ls -l "${VOLUME_PATH}"
echo ""
echo "Python version in venv:"
python --version
echo ""
echo "============================================================"
echo "  PROVISIONING COMPLETE!"
echo "  The network volume is now fully prepared."
echo "  You can terminate this pod and deploy the serverless worker."
echo "============================================================"
