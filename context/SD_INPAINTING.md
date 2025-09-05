# Architecture Plan: Stable Diffusion Inpainting with Network Volumes

This document outlines the complete architecture and workflow for deploying the standard CatVTON model (using `stable-diffusion-inpainting`) with a high-performance, network-volume-based approach on RunPod.

## 1. Core Architectural Goal

The primary goal is to achieve the fastest possible cold-start times for the serverless worker. We accomplish this by creating an extremely lightweight Docker image (a "launcher") and externalizing all large or dynamic components to a persistent network volume.

This decouples the runtime environment from the code, models, and dependencies, providing significant performance gains and operational flexibility.

## 2. Key Components

The architecture consists of three main new parts:

### a. The Lightweight "Launcher" Image (`Dockerfile.volume`)

-   **Purpose**: To be as small and fast to download as possible. Its only job is to start the container and run the entrypoint script.
-   **Contents**:
    -   A minimal CUDA base image.
    -   The `uv` Python package manager.
    -   The FastAPI application script (`app_sd_volume.py`).
    -   The smart entrypoint script (`entrypoint.sh`).
-   **Exclusions**: This image does **not** contain the CatVTON source code, any Python dependencies, or any ML models.

### b. The Smart Entrypoint Script (`entrypoint.sh`)

-   **Purpose**: To prepare the environment on the network volume and then launch the application. It acts as an intelligent bootstrapper.
-   **Execution Flow**:
    1.  The script runs automatically when the container starts.
    2.  It checks for the existence of a Python virtual environment at `/runpod-volume/venv`.
    3.  **If the environment does not exist (first-ever worker start):**
        -   It creates a new Python 3.9 virtual environment using `uv`.
        -   It installs all necessary Python packages from `/runpod-volume/CatVTON/requirements.txt` into the new venv. This is a one-time setup cost.
    4.  **If the environment already exists:**
        -   It skips the setup and immediately proceeds.
    5.  It activates the virtual environment from the network volume.
    6.  It launches the FastAPI server (`app_sd_volume.py`).

### c. The Volume-Aware Application (`app_sd_volume.py`)

-   **Purpose**: A FastAPI server specifically designed to operate in this decoupled environment.
-   **Key Features**:
    -   **Dynamic Path Injection**: At startup, it adds the CatVTON source code from `/runpod-volume/CatVTON` to the Python system path, allowing it to be imported.
    -   **Volume-Based Model Loading**: It loads the `stable-diffusion-inpainting` base model and the CatVTON adapter weights directly from `/runpod-volume/models`.
    -   **Extensive Logging**: Provides clear, step-by-step logs for environment setup, model loading, and inference.
    -   **API Contract**: Expects input image paths relative to the network volume and saves the output image back to the volume.

## 3. The Three Network Volume Components

The network volume is the persistent heart of the system and is responsible for storing:

1.  **The Python Environment (`/runpod-volume/venv/`)**: The complete virtual environment with all installed packages (`torch`, `diffusers`, etc.). This is created by the `entrypoint.sh` on the first run.
2.  **The Application Code (`/runpod-volume/CatVTON/`)**: The entire Git repository for CatVTON. This allows you to update the code on the volume without rebuilding the Docker image.
3.  **The Models (`/runpod-volume/models/`)**: The `stable-diffusion-inpainting` and `CatVTON` model files.

## 4. Complete User Workflow

This is the step-by-step process to get the system running.

### Step A: One-Time Network Volume Setup

This only needs to be done once.

1.  **Download Models Locally**: Use the `just -f Justfile.windows setup-volume-download` command. This will download the `runwayml/stable-diffusion-inpainting` and `zhengchong/CatVTON` models into a local `./models` directory.
2.  **Configure S3 Credentials**: Ensure your `.env` file contains the correct S3 credentials (`RUNPOD_S3_...`) for your network volume.
3.  **Upload to Volume**: Run `just -f Justfile.windows setup-volume-upload`. This command uses the AWS CLI to sync two local directories to the root of your network volume:
    -   `./models` -> `s3://<volume-id>/models`
    -   `./CatVTON` -> `s3://<volume-id>/CatVTON`

### Step B: Build and Deploy the Launcher

1.  **Build the Image**: Run `just -f Justfile.windows build-volume`. This creates the small launcher image.
2.  **Push the Image**: Run `just -f Justfile.windows push-volume` to push the image to your container registry.
3.  **Deploy on RunPod**:
    -   Create or update your serverless endpoint.
    -   Use the new launcher image (e.g., `elmashta/catvton-runpod-serverless:volume-launcher`).
    -   **Crucially, attach the network volume** you configured in Step A.

### Step C: First Cold Start vs. Subsequent Starts

-   **First Worker Start**: The `entrypoint.sh` will detect that no venv exists. It will spend a few minutes creating the venv and installing all Python packages. This worker will take longer to become healthy.
-   **All Subsequent Worker Starts**: The `entrypoint.sh` will find the existing venv. It will skip the setup, activate the environment, and launch the app immediately. These cold starts will be significantly faster, limited only by the time it takes to load the models into VRAM.
