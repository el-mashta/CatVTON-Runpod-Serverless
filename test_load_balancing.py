"""
A script to test the load balancing capabilities of a live Runpod serverless endpoint.

This script sends multiple concurrent requests to the endpoint to simulate a real-world
load scenario. It uses asyncio and a semaphore to control concurrency and avoid
client-side bottlenecks.

Workflow for each concurrent task:
1. Loads credentials from a .env file.
2. Takes local person and garment images as input.
3. Uploads these images to S3 with a unique name for each request.
4. Sends a request to the live serverless endpoint.
5. Waits for the worker to process and downloads the result.
"""
import os
import uuid
import logging
import asyncio
import random
from dotenv import load_dotenv
import boto3
import httpx
from botocore.config import Config as BotoConfig

# --- Inline Script Metadata (PEP 723) ---
# [run]
# requires = [
#     "boto3>=1.34.0",
#     "httpx>=0.27.0",
#     "python-dotenv>=1.0.0",
# ]
# ---

# --- Configuration ---
LOCAL_PERSON_IMAGE_PATH = "person.jpg"
LOCAL_GARMENT_IMAGE_PATH = "garment.jpg"
RESULT_DIR = "results_load_test"
TOTAL_REQUESTS = 30
MAX_CONCURRENT_TASKS = 30 # Controls how many requests are active at once

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
)
logger = logging.getLogger(__name__)

# --- Load Environment Variables ---
load_dotenv()
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
RUNPOD_ENDPOINT_ID_ALT = os.getenv("RUNPOD_ENDPOINT_ID_ALT")
S3_ENDPOINT_URL = os.getenv("RUNPOD_S3_ENDPOINT_URL")
S3_ACCESS_KEY_ID = os.getenv("RUNPOD_S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.getenv("RUNPOD_S3_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.getenv("RUNPOD_S3_BUCKET_NAME")
S3_REGION = os.getenv("RUNPOD_S3_REGION", "eu-ro-1")

# --- S3 Client Initialization ---
# Increased connection pool and added retries to handle higher concurrency.
s3_client = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=S3_ACCESS_KEY_ID,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY,
    region_name=S3_REGION,
    config=BotoConfig(
        signature_version='s3v4',
        max_pool_connections=50, # Default is 10, increasing to handle more concurrent uploads
        retries={'max_attempts': 5, 'mode': 'standard'}
    )
)

async def run_single_tryon_request(client: httpx.AsyncClient, request_num: int, semaphore: asyncio.Semaphore):
    """
    Handles one full try-on request, from S3 upload to result download.
    Uses a semaphore to limit overall concurrency.
    """
    async with semaphore:
        request_id = f"req-{request_num}-{uuid.uuid4().hex[:8]}"
        logger.info(f"[{request_id}] Starting...")

        person_filename = f"person_{request_id}.jpg"
        cloth_filename = f"cloth_{request_id}.jpg"
        s3_person_key = f"uploads/{person_filename}"
        s3_cloth_key = f"uploads/{cloth_filename}"

        try:
            # 1. Upload Images to S3
            logger.info(f"[{request_id}] Uploading images to S3...")
            await asyncio.to_thread(s3_client.upload_file, LOCAL_PERSON_IMAGE_PATH, S3_BUCKET_NAME, s3_person_key)
            await asyncio.to_thread(s3_client.upload_file, LOCAL_GARMENT_IMAGE_PATH, S3_BUCKET_NAME, s3_cloth_key)
            logger.info(f"[{request_id}] S3 uploads complete.")

            # 2. Call RunPod Serverless Endpoint
            runpod_payload = {
                "person_image_path": s3_person_key,
                "garment_image_path": s3_cloth_key,
                "mask_type": "upper",
                "seed": -1
            }
            
            # Randomly select between the two endpoints if the ALT is available
            endpoints = [RUNPOD_ENDPOINT_ID]
            if RUNPOD_ENDPOINT_ID_ALT:
                endpoints.append(RUNPOD_ENDPOINT_ID_ALT)
            selected_endpoint_id = random.choice(endpoints)

            tryon_url = f"https://{selected_endpoint_id}.api.runpod.ai/api/v1/tryon"
            headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}

            logger.info(f"[{request_id}] Sending request to Runpod endpoint ({selected_endpoint_id})...")
            response = await client.post(tryon_url, headers=headers, json=runpod_payload)
            
            logger.info(f"[{request_id}] Received response with status code: {response.status_code}")
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"[{request_id}] Worker response: {result}")

            # 3. Download Result from S3
            result_image_key = result.get('result_image_path')
            if not result_image_key:
                 raise ValueError("Worker response did not contain 'result_image_path'")

            local_result_path = os.path.join(RESULT_DIR, f"result_{request_id}.png")
            logger.info(f"[{request_id}] Downloading result to '{local_result_path}'...")
            await asyncio.to_thread(s3_client.download_file, S3_BUCKET_NAME, result_image_key, local_result_path)
            
            logger.info(f"[{request_id}] SUCCESS! Result saved to: {local_result_path}")

        except httpx.HTTPStatusError as e:
            logger.error(f"[{request_id}] HTTP error from Runpod: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.exception(f"[{request_id}] An unexpected error occurred.")


async def main():
    """Main function to orchestrate the concurrent load test."""
    if not all([RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID, S3_BUCKET_NAME]):
        logger.error("CRITICAL: Missing required environment variables. Please check your .env file.")
        return

    os.makedirs(RESULT_DIR, exist_ok=True)
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    
    # Use a single client for all requests for connection pooling
    async with httpx.AsyncClient(timeout=300.0) as client:
        tasks = []
        for i in range(TOTAL_REQUESTS):
            task = run_single_tryon_request(client, i + 1, semaphore)
            tasks.append(task)
        
        logger.info(f"Dispatching {TOTAL_REQUESTS} requests with a max concurrency of {MAX_CONCURRENT_TASKS}...")
        await asyncio.gather(*tasks)
        logger.info("Load test complete.")


if __name__ == "__main__":
    # --- How to Run ---
    # 1. Ensure your .env file is correctly filled out.
    # 2. Make sure `person.jpg` and `garment.jpg` are in the same directory.
    # 3. Run using a PEP 723-compliant runner like pipx or uv:
    #    pipx run ./test_load_balancing.py
    #    uv run ./test_load_balancing.py
    asyncio.run(main())
