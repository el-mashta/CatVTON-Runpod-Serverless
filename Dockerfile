# ====================================================================================
# Stage 1: Model Downloader
# This stage's only job is to download all the necessary models from Hugging Face.
# ====================================================================================
FROM python:3.9-slim as downloader

# Install huggingface-cli for robust model downloading
RUN pip install huggingface_hub

# Set the cache directory where all models will be stored
ENV HF_HOME=/models
ENV HUGGINGFACE_HUB_CACHE=/models

# Download the models. --local-dir-use-symlinks False is crucial for Docker.
RUN huggingface-cli download booksforcharlie/stable-diffusion-inpainting \
    --local-dir ${HF_HOME}/stable-diffusion-inpainting --local-dir-use-symlinks False

RUN huggingface-cli download zhengchong/CatVTON \
    --local-dir ${HF_HOME}/CatVTON --local-dir-use-symlinks False

# ====================================================================================
# Stage 2: Final Production Image
# This is the final, lean image that will be deployed.
# ====================================================================================
# Use the official, up-to-date RunPod worker image for ComfyUI.
# This base image already contains a Python virtual environment at /opt/venv
# which is managed by uv and is already added to the system PATH.
FROM runpod/worker-comfyui:5.4.0-base

# Install unzip, as it's not in the base image
RUN apt-get update && apt-get install -y unzip && rm -rf /var/lib/apt/lists/*

# Explicitly set UV_PROJECT_ENVIRONMENT to use the venv created by the base image.
# This ensures all `uv` commands operate within this isolated environment.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# Set environment variables for our API server and model locations
ENV PORT=8000
ENV HF_HOME=/comfyui/models/huggingface
ENV HUGGINGFACE_HUB_CACHE=/comfyui/models/huggingface
ENV TRANSFORMERS_CACHE=/comfyui/models/huggingface

# Copy the pre-downloaded models from our downloader stage into the correct location.
COPY --from=downloader /models /comfyui/models/huggingface

# Install the ComfyUI-CatVTON custom node
WORKDIR /comfyui/custom_nodes
RUN wget https://github.com/Zheng-Chong/CatVTON/releases/download/ComfyUI/ComfyUI-CatVTON.zip && \
    unzip ComfyUI-CatVTON.zip && \
    rm ComfyUI-CatVTON.zip

# Install Python requirements for the CatVTON custom node using `uv`.
# This will automatically use the /opt/venv virtual environment.
WORKDIR /comfyui/custom_nodes/ComfyUI-CatVTON
RUN if [ -f requirements.txt ]; then uv pip install -r requirements.txt; fi

# Install our FastAPI server dependencies using `uv`.
WORKDIR /
RUN uv pip install fastapi uvicorn httpx pydantic websockets

# Copy our application files into the container's root directory.
COPY app.py .
COPY catvton_workflow.json .

# Expose the port our API will run on
EXPOSE 8000

# The final command to start our FastAPI server.
# This `uvicorn` executable is the one installed inside the /opt/venv.
# We override the base image's default CMD.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
