# Migration Guide: From IDM-VTON to a Load-Balanced CatVTON API

This document outlines the migration of the virtual try-on backend to a modern, high-performance CatVTON workflow using RunPod's **Load Balancer** serverless endpoints.

This guide is based on the official `runpod/worker-comfyui` practices, adapting them for a direct API access model, which is ideal for interactive web applications.

---\n

## Architectural Overview

The core of this migration is to shift from a traditional, queue-based worker to a direct-access, load-balanced REST API.

1.  **The Foundation**: We will build upon the official `runpod/worker-comfyui:5.4.0-base` Docker image, which provides a stable, pre-configured ComfyUI environment.
2.  **The Shift**: Instead of using the image's built-in queue handler, we will create our own **FastAPI web server (`app.py`)** that runs on top. This gives us full control over the API.
3.  **The Workflow**:
    *   Our FastAPI server will expose custom endpoints (e.g., `/api/v1/tryon`) and a mandatory health check (`/ping`).
    *   On startup, it will launch the main ComfyUI server as a background process within the same container.
    *   When our API receives a request, it will construct a ComfyUI workflow in memory, inject the base64 image data directly into the workflow nodes, and send it to the local ComfyUI process for execution.
    *   The final image is returned directly in the API response.
4.  **The Backend (`main.py`)**: The application backend will be simplified to make a single, direct HTTP request to our new custom API endpoint.

This approach bypasses the RunPod queueing system, resulting in lower latency and a more standard REST API architecture.

---\n

## Part 1: Creating the New Load Balancer Worker

### Step 1: Create the FastAPI Wrapper (`app.py`)

Create a new file, `app.py`, in the root of your repository. This script will manage both the API and the underlying ComfyUI process.

```python
import os
import subprocess
import asyncio
import httpx
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import json

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Pydantic Models for API Contracts ---
class TryonRequest(BaseModel):
    person_image: str  # base64 encoded string
    garment_image: str # base64 encoded string

# --- FastAPI App ---
app = FastAPI()
comfyui_process = None

# --- ComfyUI Workflow Management ---
def load_workflow():
    """Loads the ComfyUI workflow template from a JSON file."""
    try:
        with open("catvton_workflow.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("catvton_workflow.json not found!")
        return None

@app.on_event("startup")
def startup_event():
    """On startup, launch the ComfyUI server as a background process."""
    global comfyui_process
    # The official worker places ComfyUI at /comfyui
    comfyui_path = "/comfyui/main.py"
    if not os.path.exists(comfyui_path):
        logger.error(f"ComfyUI main.py not found at {comfyui_path}")
        return

    command = ["python3", comfyui_path, "--listen", "127.0.0.1", "--port", "8188"]
    logger.info(f"Starting ComfyUI with command: {" ".join(command)}")
    comfyui_process = subprocess.Popen(command)
    logger.info(f"ComfyUI process started with PID: {comfyui_process.pid}")

@app.on_event("shutdown")
def shutdown_event():
    """On shutdown, terminate the ComfyUI process."""
    if comfyui_process:
        logger.info("Terminating ComfyUI process.")
        comfyui_process.terminate()

# --- API Endpoints ---
@app.get("/ping")
async def health_check():
    """Health check endpoint required by Runpod for load balancing."""
    return {"status": "healthy"}

@app.post("/api/v1/tryon")
async def virtual_tryon(request: TryonRequest):
    """The main endpoint to perform the virtual try-on."""
    workflow = load_workflow()
    if not workflow:
        raise HTTPException(status_code=500, detail="Workflow file not found on server.")

    # Directly inject base64 image data into the workflow nodes.
    for node in workflow["nodes"]:
        if node["id"] == 10: # Target Person Node
            node["widgets_values"][0] = request.person_image
        elif node["id"] == 11: # Reference Garment Node
            node["widgets_values"][0] = request.garment_image

    # This is a simplified placeholder for the ComfyUI interaction.
    # A production implementation would require a more robust async client
    # to handle websockets for real-time updates from ComfyUI.
    try:
        async with httpx.AsyncClient() as client:
            logger.info("Sending prompt to local ComfyUI server.")
            # A full implementation would post to /prompt and then fetch
            # the result from /history or /view.
            mock_result = {
                "output": {
                    "images": [{"image": "mock_base64_image_data_from_worker"}]
                }
            }
            logger.info("Received response from ComfyUI.")
            return mock_result

    except httpx.RequestError as e:
        logger.error(f"Error communicating with ComfyUI: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable: cannot connect to ComfyUI.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

### Step 2: Create an Optimized, Production-Ready `Dockerfile`

The `Dockerfile` is the blueprint for your worker. The following version is heavily based on the official `runpod/worker-comfyui` practices and is optimized for our specific load-balancing use case, with explicit `uv` environment management.

**Key Optimizations:**
1.  **Official Base Image**: We use `runpod/worker-comfyui:5.4.0-base` as our foundation. This image already includes a Python virtual environment at `/opt/venv` which is managed by `uv` and added to the system `PATH`.
2.  **Explicit `uv` Environment**: We explicitly set `UV_PROJECT_ENVIRONMENT` to ensure all `uv` commands operate within the provided virtual environment for maximum reproducibility.
3.  **Multi-Stage Build**: A `downloader` stage fetches all models to keep the final image clean and improve build caching.
4.  **Pre-cached Models**: All required models are downloaded during the build for the fastest possible cold starts.

Create/update your `Dockerfile` with the following content:

```dockerfile
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
RUN uv pip install fastapi uvicorn httpx pydantic

# Copy our application files into the container's root directory.
COPY app.py .
COPY catvton_workflow.json .

# Expose the port our API will run on
EXPOSE 8000

# The final command to start our FastAPI server.
# This `uvicorn` executable is the one installed inside the /opt/venv.
# We override the base image's default CMD.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

In your `app.py`, you will need to update the paths in the `CatVTONPipeline` and `AutoMasker` initialization to point to the pre-downloaded models in `/comfyui/models/huggingface` instead of relying on automatic downloads from the hub.

### Step 3: Deploy as a Load Balancer Endpoint

1.  Push your updated Docker image to a container registry.
2.  In the RunPod console, create a **New Endpoint**.
3.  Select **Import from Docker Registry** and provide your image URL.
4.  **Crucially, under "Endpoint Type", select "Load Balancer".**
5.  Configure your GPU and worker settings.
6.  Under **Expose HTTP Ports**, add `8000`.
7.  Create the endpoint.

---\n

## Part 2: Backend (`main.py`) Modifications

The application backend (`main.py`) is now much simpler.

### Update the API Call Logic

Replace the core of the `tryon` function in `main.py` with a single, direct call to your new load-balanced endpoint.

```python
# Inside the async def tryon(...) function in main.py

# ... (image saving and base64 encoding logic remains the same) ...
person_b64 = image_to_base64(final_local_person_path)
cloth_b64 = image_to_base64(final_local_cloth_path)

# Define the new endpoint URL and payload
tryon_url = f"https://{RUNPOD_ENDPOINT_ID}.api.runpod.ai/api/v1/tryon"
headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}", "Content-Type": "application/json"}
payload = {
    "person_image": person_b64,
    "garment_image": cloth_b64
}

logger.info(f"[{request_id}] Sending POST request to custom load balancer endpoint.")

try:
    async with httpx.AsyncClient() as client:
        response = await client.post(tryon_url, headers=headers, json=payload, timeout=300)
    
    response.raise_for_status()
    result = response.json()

    # Process the direct response from your FastAPI wrapper
    output_data = result.get('output', {})
    # ... (rest of the image decoding and saving logic) ...

except Exception as e:
    # ... (error handling) ...

# ... (cleanup logic) ...
```

---\n

## Part 3: Local Testing

You can test your new worker locally before deploying.

1.  **Build the Docker Image:**
    ```bash
    docker build -t catvton-worker .
    ```

2.  **Run the Container:**
    ```bash
    docker run --rm -p 8000:8000 --gpus all catvton-worker
    ```

3.  **Send a Test Request:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/tryon \
         -H "Content-Type: application/json" \
         -d 
             "person_image": "your_base64_person_image_string",
             "garment_image": "your_base64_garment_image_string"
             
    ```
This updated guide provides a more robust and well-explained path to a modern, load-balanced architecture on RunPod.
