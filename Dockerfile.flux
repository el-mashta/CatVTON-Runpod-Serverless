# ====================================================================================
# Stage 1: Model Downloader (FLUX Version)
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

# Use Docker Build Secret to securely access the Hugging Face token
RUN --mount=type=secret,id=hf_token \
    HF_TOKEN=$(cat /run/secrets/hf_token) hf download black-forest-labs/FLUX.1-Fill-dev --local-dir ${HF_HOME}/FLUX.1-Fill-dev

# Download the CatVTON fine-tuned weights (contains FLUX LoRA) and supporting models (DensePose, SCHP).
RUN hf download zhengchong/CatVTON --local-dir ${HF_HOME}/CatVTON

# ====================================================================================
# Stage 2: Final Production Image (FLUX Version)
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

# Install Python 3.9 using uv.
RUN uv python install 3.9

# Define and configure the project's virtual environment
ENV VENV_PATH=/opt/venv
ENV UV_PROJECT_ENVIRONMENT=$VENV_PATH
RUN uv venv $VENV_PATH --python 3.9
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

# Copy the FLUX application logic and rename it to app.py for a consistent entrypoint
COPY app_flux.py ./app.py

# Expose the port the handler will run on
EXPOSE 8000

# Command to run the serverless handler using the Python from our venv
CMD ["python", "-u", "app.py"]