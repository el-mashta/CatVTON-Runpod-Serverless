# Automatically load environment variables from a .env file
set dotenv-load

# Set Bash as the default shell for all recipes
set shell := ["bash", "-c"]

# ==============================================================================
# Variables
# ==============================================================================

# Default tag for the launcher image. Can be overridden from the command line.
# Example: just --set tag "v1.0.1" push-volume
tag := "latest"

# Image name for the lightweight launcher for the Full Network Volume architecture
IMAGE_NAME_VOLUME := "elmashta/catvton-runpod-serverless:volume-launcher-" + tag

# Image name for the development pod environment
IMAGE_NAME_POD := "elmashta/catvton-dev-pod:" + tag

# ==============================================================================
# Default Task - Documentation
# ==============================================================================

# List all available commands
default:
    @echo "Usage: just <command>"
    @echo ""
    @echo "--- Main Workflow ---"
    @echo "  build-volume         : Build the lightweight launcher Docker image."
    @echo "  push-volume          : Push the launcher image. Use --set tag <tag> to specify a version."
    @echo ""
    @echo "--- Development Pod Workflow ---"
    @echo "  build-pod            : Build the development pod Docker image."
    @echo "  push-pod             : Push the dev pod image. Use --set tag <tag> to specify a version."
    @echo ""
    @echo "--- Local Development ---"
    @echo "  install              : Install Python dependencies into the local .venv."
    @echo "  setup                : Create a local Python virtual environment."

# ==============================================================================
# Full Network Volume Architecture Workflow
# ==============================================================================

# Build the lightweight launcher Docker image
build-volume:
    @docker buildx build --platform linux/amd64 --load -f Dockerfile.volume -t {{IMAGE_NAME_VOLUME}} .
    @echo "Launcher image built: {{IMAGE_NAME_VOLUME}}"

# Build and push the launcher Docker image
push-volume: build-volume
    @docker push {{IMAGE_NAME_VOLUME}}
    @echo "Launcher image pushed: {{IMAGE_NAME_VOLUME}}"

# ==============================================================================
# Development Pod Workflow
# ==============================================================================

# Build the development pod Docker image
build-pod:
    @docker buildx build --platform linux/amd64 --load -f Dockerfile.pod.final -t {{IMAGE_NAME_POD}} .
    @echo "Development pod image built: {{IMAGE_NAME_POD}}"

# Build and push the development pod Docker image
push-pod: build-pod
    @docker push {{IMAGE_NAME_POD}}
    @echo "Development pod image pushed: {{IMAGE_NAME_POD}}"

# ==============================================================================
# Python Environment Management (Local)
# ==============================================================================

# Create a local Python virtual environment
setup:
    uv venv
    @echo "Virtual environment created in .venv"
    @echo "Activate it with: source .venv/bin/activate"

# Install all Python dependencies into the local virtual environment
install:
    uv pip install -r CatVTON/requirements.txt
    uv pip install fastapi uvicorn python-multipart pydantic httpx boto3 botocore python-dotenv
    @echo "Dependencies installed."
