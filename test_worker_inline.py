"""
[run]
requires = [
    "httpx>=0.27.0",
]
"""
import httpx
import logging
import uuid
import os

# --- Configuration ---
# This should be the address of the worker you are testing locally.
# The port (8000) should match the port your worker's FastAPI/Uvicorn server is listening on.
WORKER_URL = os.environ.get("WORKER_URL", "http://localhost:8000/api/v1/tryon")

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
)
logger = logging.getLogger(__name__)


def test_serverless_endpoint():
    """
    Sends a mocked request to the serverless worker endpoint to test its response.
    """
    request_id = uuid.uuid4().hex
    logger.info(f"[{request_id}] Preparing to test worker at {WORKER_URL}")

    # This payload simulates the data your main.py backend would send.
    # It provides mock paths for the images, as the worker expects to read them
    # from a volume, not receive the raw files.
    mock_payload = {
        "input": {
            "person_image_path": f"uploads/person_{request_id}.jpg",
            "garment_image_path": f"uploads/cloth_{request_id}.jpg",
            "cloth_type": "upper",
            "seed": -1
        }
    }

    logger.info(f"[{request_id}] Sending mock payload: {mock_payload}")

    try:
        # Use httpx.Client for proper resource management
        with httpx.Client(timeout=120.0) as client:
            response = client.post(WORKER_URL, json=mock_payload)

        logger.info(f"[{request_id}] Received response with status code: {response.status_code}")

        # Check if the response was successful
        response.raise_for_status()

        try:
            result = response.json()
            logger.info(f"[{request_id}] Worker response (JSON): {result}")
        except Exception:
            logger.error(f"[{request_id}] Failed to decode JSON from response. Raw text: {response.text}")

    except httpx.ConnectError as e:
        logger.error(f"[{request_id}] Connection failed. Is the worker running at {WORKER_URL}?")
        logger.error(f"Error details: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"[{request_id}] Request failed. Status: {e.response.status_code}, Response: {e.response.text}")
    except Exception as e:
        logger.exception(f"[{request_id}] An unexpected error occurred.")


if __name__ == "__main__":
    # To run this test:
    # 1. Ensure you have a PEP 723-compliant runner like pipx installed (`pip install pipx`).
    # 2. Start your worker locally (e.g., by running app_sd_volume.py).
    # 3. Run this script directly from your terminal:
    #    pipx run ./test_worker_inline.py
    #
    # You can also override the URL via an environment variable:
    #    WORKER_URL="http://some-other-address:port" pipx run ./test_worker_inline.py
    test_serverless_endpoint()
