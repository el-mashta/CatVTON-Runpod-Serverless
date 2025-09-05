# Automatically load environment variables from a .env file
set dotenv-load

# Set Bash as the default shell for all recipes
set shell := ["bash", "-c"]

# ==============================================================================
# Variables
# ==============================================================================

# Image name for the standard CatVTON build
IMAGE_NAME := "elmashta/catvton-runpod-serverless:latest"

# Image name for the FLUX-based CatVTON build (Base64)
IMAGE_NAME_FLUX := "elmashta/catvton-runpod-serverless:flux"

# Image name for the production-ready FLUX S3 build
IMAGE_NAME_FLUX_S3 := "elmashta/catvton-runpod-serverless:flux-s3"

# The port to expose on the host when running containers locally.
HOST_PORT := "8000"

# ==============================================================================
# Default Task - Documentation
# ==============================================================================

# List all available commands
default:
    @echo "Usage: just <command>"
    @echo ""
    @echo "Available commands:"
    @just --list

# ==============================================================================
# Python Environment Management (using uv)
# ==============================================================================

# Create a Python virtual environment
setup:
    uv venv
    @echo "Virtual environment created in .venv"
    @echo "Activate it with: source .venv/bin/activate"

# Install all Python dependencies into the virtual environment
install:
    uv pip install -r CatVTON/requirements.txt
    uv pip install fastapi uvicorn python-multipart pydantic httpx boto3 botocore python-dotenv
    @echo "Dependencies installed."

# ==============================================================================
# Standard CatVTON Docker Workflow
# ============================================================================== 

# Build the standard Docker container image
build:
    docker buildx build --platform linux/amd64 --load -f Dockerfile -t {{IMAGE_NAME}} .
    @echo "Docker image built: {{IMAGE_NAME}}"

# Build and push the standard Docker container image
push: build
    docker push {{IMAGE_NAME}}
    @echo "Docker image pushed: {{IMAGE_NAME}}"

# ==============================================================================
# FLUX Version Docker Workflow (Base64)
# ==============================================================================

# Build the FLUX version Docker container image, passing the HF_TOKEN secret
flux-build:
    @echo "Building FLUX image. This requires the HF_TOKEN environment variable to be set."
    @docker buildx build --platform linux/amd64 --load \
      --secret id=hf_token,env=HF_TOKEN \
      -f Dockerfile.flux -t {{IMAGE_NAME_FLUX}} .
    @echo "FLUX Docker image built: {{IMAGE_NAME_FLUX}}"

# Build and push the FLUX version Docker container image
flux-push: flux-build
    docker push {{IMAGE_NAME_FLUX}}
    @echo "FLUX Docker image pushed: {{IMAGE_NAME_FLUX}}"

# ==============================================================================
# FLUX Version Docker Workflow (S3 - Production)
# ==============================================================================

# Build the FLUX S3 version Docker container image, passing the HF_TOKEN secret
flux-s3-build:
    @echo "Building FLUX S3 image. This requires the HF_TOKEN environment variable to be set."
    @docker buildx build --platform linux/amd64 --load \
      --secret id=hf_token,env=HF_TOKEN \
      -f Dockerfile.flux_s3 -t {{IMAGE_NAME_FLUX_S3}} .
    @echo "FLUX S3 Docker image built: {{IMAGE_NAME_FLUX_S3}}"

# Build and push the FLUX S3 version Docker container image
flux-s3-push: flux-s3-build
    docker push {{IMAGE_NAME_FLUX_S3}}
    @echo "FLUX S3 Docker image pushed: {{IMAGE_NAME_FLUX_S3}}"

# Run the FLUX S3 version Docker container locally (requires local .env file with S3 creds)
flux-s3-run:
    @echo "Starting FLUX S3 container. Ensure .env file is present."
    docker run --rm -it --env-file .env -p {{HOST_PORT}}:8000 --gpus all {{IMAGE_NAME_FLUX_S3}}
