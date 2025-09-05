# ====================================================================================
# Stage 1: Model Downloader
# Use a more robust base image to ensure network stability during downloads.
# ====================================================================================
FROM ubuntu:22.04 AS downloader

# Install Python 3.9, pip, and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.9 \
    python3-pip \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv, the Rust-based Python package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install the full huggingface_hub[cli] package to get the modern `hf` command
RUN uv pip install --system "huggingface_hub[cli]"

# Set the cache directory where all models will be stored
ENV HF_HOME=/models
ENV HUGGINGFACE_HUB_CACHE=/models

# Download the base Stable Diffusion model from the official repository.
RUN hf download runwayml/stable-diffusion-inpainting --local-dir ${HF_HOME}/stable-diffusion-inpainting

# Download the CatVTON fine-tuned weights and supporting models (DensePose, SCHP).
RUN hf download zhengchong/CatVTON --local-dir ${HF_HOME}/CatVTON

# ====================================================================================
# Stage 2: Final Production Image
# This stage remains unchanged, starting from the lean CUDA base image.
# ====================================================================================
FROM nvidia/cuda:12.1.1-base-ubuntu22.04

# Set the working directory
WORKDIR /app

# Install system dependencies required for uv and building some Python packages.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv, the Rust-based Python package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set explicit uv environment variables for a robust, reproducible environment
ENV UV_CACHE_DIR=/opt/uv/cache
ENV UV_PYTHON_INSTALL_DIR=/opt/python
ENV UV_NO_CACHE=1

# Install Python 3.9 using uv. It will be installed into UV_PYTHON_INSTALL_DIR.
RUN uv python install 3.9

# Define the path for our application's virtual environment
ENV VENV_PATH=/opt/venv
ENV UV_PROJECT_ENVIRONMENT=$VENV_PATH

# Create a virtual environment at the predefined path using the Python we just installed.
RUN uv venv $VENV_PATH --python 3.9

# Activate the virtual environment by adding its bin directory to the PATH.
ENV PATH="$VENV_PATH/bin:$PATH"

# Install PyTorch and its variants using uv, pointing to the correct CUDA 12.1 index.
RUN uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Copy the CatVTON library code into the image
COPY ./CatVTON /app/CatVTON

# Install the remaining Python dependencies into the virtual environment
RUN uv pip install -r /app/CatVTON/requirements.txt

# Copy the pre-downloaded models from our downloader stage
COPY --from=downloader /models /app/models

# Set environment variables to point to the local models
ENV HF_HOME=/app/models
ENV HUGGINGFACE_HUB_CACHE=/app/models

# Copy the application logic for the runpod handler
COPY app.py .

# Expose the port the handler will run on
EXPOSE 8000

# Command to run the serverless handler using the Python from our venv
CMD ["python", "-u", "app.py"]
