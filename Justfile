# Set PowerShell as the default shell for all recipes
set shell := ["pwsh", "-c"]

# Justfile for managing the CatVTON Runpod Serverless Worker

# ==============================================================================
# Variables
# ==============================================================================

# The name of the Docker image to build.
# Usage: just build --set IMAGE_NAME "your-repo/your-image"
IMAGE_NAME := "elmashta/catvton-runpod-serverless:latest"

# The port to expose on the host when running the container locally.
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

# Install all Python dependencies from requirements.txt into the virtual environment
install:
    uv pip install -r CatVTON/requirements.txt
    uv pip install fastapi uvicorn python-multipart pydantic httpx
    @echo "Dependencies installed."

# ==============================================================================
# Docker Workflow
# ==============================================================================

# Build the Docker container image using Docker Buildx
build:
    docker buildx build --platform linux/amd64 --load -t {{IMAGE_NAME}} .
    @echo "Docker image built: {{IMAGE_NAME}}"

# Build the Docker container image and push it to a registry
push: build
    docker push {{IMAGE_NAME}}
    @echo "Docker image pushed: {{IMAGE_NAME}}"

# Run the Docker container locally for testing
run:
    @echo "Starting container. Access the API at http://localhost:{{HOST_PORT}}"
    docker run --rm -it -p {{HOST_PORT}}:8000 --gpus all {{IMAGE_NAME}}

# Stop any running local container (useful for development)
stop:
    @docker ps -q --filter ancestor={{IMAGE_NAME}} | xargs -r docker stop

# ==============================================================================
# Testing & Verification
# ==============================================================================

# Run a test request against a locally running container using PowerShell
test:
    @pwsh -ExecutionPolicy Bypass -File ./test.ps1 -HostPort {{HOST_PORT}}

# ==============================================================================
# Utility
# ==============================================================================

# Tail the logs of the running Docker container
logs:
    @docker ps -q --filter ancestor={{IMAGE_NAME}} | xargs -r docker logs -f