# backend.py
# This script creates a minimal FastAPI backend that acts as a secure, self-contained
# proxy for the S3-based RunPod worker. It demonstrates the full production
# workflow: receive Base64 -> upload to S3 -> trigger worker -> download from S3 -> return Base64.

import os
import uuid
import httpx
import base64
import io
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn
import boto3
from botocore.client import Config
from contextlib import asynccontextmanager

# --- Environment Variable Loading ---
load_dotenv()

# --- Configuration ---
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
S3_ENDPOINT_URL = os.getenv("RUNPOD_S3_ENDPOINT_URL")
S3_ACCESS_KEY_ID = os.getenv("RUNPOD_S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.getenv("RUNPOD_S3_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.getenv("RUNPOD_S3_BUCKET_NAME")

# --- Global S3 Client ---
s3_client = None

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global s3_client
    if not all([RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID, S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET_NAME]):
        raise RuntimeError("Missing one or more required Runpod or S3 environment variables.")
    
    print("Initializing S3 client...")
    s3_client = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4')
    )
    yield
    print("Shutting down.")
    s3_client = None

# --- API Data Models ---
class TryOnRequest(BaseModel):
    person_image: str
    garment_image: str

class TryOnResponse(BaseModel):
    result_image: str

# --- FastAPI Application Setup ---
app = FastAPI(
    title="CatVTON S3 Backend",
    description="A proxy backend for the S3-based CatVTON RunPod worker.",
    version="1.0.0",
    lifespan=lifespan
)

# --- API Endpoint ---
@app.post("/api/tryon", response_model=TryOnResponse)
async def perform_tryon(request: TryOnRequest):
    if not s3_client:
        raise HTTPException(status_code=503, detail="S3 client is not initialized.")

    request_id = uuid.uuid4().hex
    person_key = f"uploads/person_{request_id}.jpg"
    garment_key = f"uploads/garment_{request_id}.jpg"

    try:
        # 1. Decode Base64 and upload to S3
        person_bytes = base64.b64decode(request.person_image)
        garment_bytes = base64.b64decode(request.garment_image)

        s3_client.upload_fileobj(io.BytesIO(person_bytes), S3_BUCKET_NAME, person_key)
        s3_client.upload_fileobj(io.BytesIO(garment_bytes), S3_BUCKET_NAME, garment_key)

        # 2. Prepare payload and call RunPod worker
        runpod_payload = {
            "person_image_key": person_key,
            "garment_image_key": garment_key,
        }
        
        tryon_url = f"https://{RUNPOD_ENDPOINT_ID}.api.runpod.ai/api/v1/tryon-s3"
        headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(tryon_url, headers=headers, json=runpod_payload)
            response.raise_for_status()

        # 3. Process the response from the worker
        worker_output = response.json()
        result_key = worker_output.get("result_image_key")
        if not result_key:
            raise ValueError("Invalid response from worker.")

        # 4. Download the result from S3
        result_obj = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=result_key)
        result_bytes = result_obj['Body'].read()

        # 5. Encode result to Base64 and return
        result_base64 = base64.b64encode(result_bytes).decode('utf-8')
        return TryOnResponse(result_image=result_base64)

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")

# --- Server Execution ---
if __name__ == "__main__":
    print("Starting backend server on http://0.0.0.0:4009")
    uvicorn.run(app, host="0.0.0.0", port=4009)
