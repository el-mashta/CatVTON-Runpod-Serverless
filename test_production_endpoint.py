"""
A script to test the live Runpod serverless endpoint from your local machine.

This script simulates the exact workflow of your production gateway backend:
1. Loads credentials from a .env file.
2. Takes local person and garment images as input.
3. Uploads these images to your RunPod S3-compatible network volume.
4. Sends a request to your live serverless endpoint with the S3 paths.
5. Waits for the worker to process the request.
6. Downloads the final try-on image from S3 and saves it locally.
"""
import os
import uuid
import logging
from dotenv import load_dotenv
import boto3
import httpx
from botocore.client import Config

# --- Inline Script Metadata (PEP 723) ---
# [run]
# requires = [
#     "boto3>=1.34.0",
#     "httpx>=0.27.0",
#     "python-dotenv>=1.0.0",
# ]
# ---

# --- Basic Configuration ---
# Update these paths to point to your local test images
LOCAL_PERSON_IMAGE_PATH = "person.jpg"
LOCAL_GARMENT_IMAGE_PATH = "garment.jpg"
RESULT_DIR = "results"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the end-to-end test."""
    # 1. Load Environment Variables
    logger.info("Loading environment variables from .env file...")
    load_dotenv()

    runpod_api_key = os.getenv("RUNPOD_API_KEY")
    runpod_endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID")
    s3_endpoint_url = os.getenv("RUNPOD_S3_ENDPOINT_URL")
    s3_access_key_id = os.getenv("RUNPOD_S3_ACCESS_KEY_ID")
    s3_secret_access_key = os.getenv("RUNPOD_S3_SECRET_ACCESS_KEY")
    s3_bucket_name = os.getenv("RUNPOD_S3_BUCKET_NAME")
    s3_region = os.getenv("RUNPOD_S3_REGION", "eu-ro-1")

    if not all([runpod_api_key, runpod_endpoint_id, s3_endpoint_url, s3_access_key_id, s3_secret_access_key, s3_bucket_name]):
        logger.error("CRITICAL: Missing one or more required environment variables. Please check your .env file.")
        return

    # Create results directory if it doesn't exist
    os.makedirs(RESULT_DIR, exist_ok=True)

    # 2. Initialize S3 Client
    logger.info(f"Connecting to S3-compatible storage at {s3_endpoint_url}...")
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=s3_endpoint_url,
            aws_access_key_id=s3_access_key_id,
            aws_secret_access_key=s3_secret_access_key,
            region_name=s3_region,
            config=Config(signature_version='s3v4')
        )
    except Exception as e:
        logger.exception("Failed to create S3 client.")
        return

    request_id = uuid.uuid4().hex
    person_filename = f"person_{request_id}.jpg"
    cloth_filename = f"cloth_{request_id}.jpg"
    s3_person_key = f"uploads/{person_filename}"
    s3_cloth_key = f"uploads/{cloth_filename}"

    try:
        # 3. Upload Images to S3
        logger.info(f"[{request_id}] Uploading '{LOCAL_PERSON_IMAGE_PATH}' to S3 bucket '{s3_bucket_name}' as '{s3_person_key}'...")
        s3_client.upload_file(LOCAL_PERSON_IMAGE_PATH, s3_bucket_name, s3_person_key)

        logger.info(f"[{request_id}] Uploading '{LOCAL_GARMENT_IMAGE_PATH}' to S3 as '{s3_cloth_key}'...")
        s3_client.upload_file(LOCAL_GARMENT_IMAGE_PATH, s3_bucket_name, s3_cloth_key)
        logger.info(f"[{request_id}] S3 uploads complete.")

        # 4. Call RunPod Serverless Endpoint
        # For load balancing endpoints, the payload is the raw JSON body, not wrapped in {"input": ...}
        runpod_payload = {
            "person_image_path": s3_person_key,
            "garment_image_path": s3_cloth_key,
            "mask_type": "upper", # Assuming 'upper' as a default
            "seed": -1
        }
        
        # NOTE: The worker's endpoint path might be different.
        # Based on `main.py` it seems to be `/api/v1/tryon`, but adjust if needed.
        tryon_url = f"https://{runpod_endpoint_id}.api.runpod.ai/api/v1/tryon"
        headers = {"Authorization": f"Bearer {runpod_api_key}"}

        logger.info(f"[{request_id}] Sending request to Runpod endpoint: {tryon_url}")
        logger.debug(f"[{request_id}] Payload: {runpod_payload}")

        with httpx.Client(timeout=300.0) as client: # 5 minute timeout
            response = client.post(tryon_url, headers=headers, json=runpod_payload)
        
        logger.info(f"[{request_id}] Received response with status code: {response.status_code}")
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"[{request_id}] Full worker response: {result}")

        # 5. Download Result from S3
        result_image_key = result.get('result_image_path')
        if not result_image_key:
             raise ValueError(f"Unexpected output format from worker: {result}")

        local_result_path = os.path.join(RESULT_DIR, f"result_{request_id}.png")
        logger.info(f"[{request_id}] Downloading result '{result_image_key}' from S3 to '{local_result_path}'...")
        s3_client.download_file(s3_bucket_name, result_image_key, local_result_path)
        
        logger.info(f"SUCCESS! AI Try-on completed. Result saved to: {local_result_path}")

    except httpx.TimeoutException:
        logger.error(f"[{request_id}] Request to Runpod timed out. The worker may be cold starting or the task is taking too long.")
    except httpx.HTTPStatusError as e:
        logger.error(f"[{request_id}] HTTP error from Runpod: {e.response.status_code}")
        # Log the full response body for debugging
        logger.error(f"[{request_id}] Full response content: {e.response.text}")
    except Exception as e:
        logger.exception(f"[{request_id}] An unexpected error occurred during the process.")

if __name__ == "__main__":
    # --- How to Run ---
    # 1. Create a `.env` file by copying `.env.example` and fill in your actual credentials.
    # 2. Make sure you have `person.jpg` and `garment.jpg` in the same directory as this script.
    # 3. Ensure you have a PEP 723-compliant runner like pipx (`pip install pipx`).
    # 4. Run the script from your terminal:
    #    pipx run ./test_production_endpoint.py
    main()
