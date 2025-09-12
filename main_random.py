import logging
import sys
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image, ImageOps
import shutil
import uuid
import os
import boto3
import httpx
import asyncio
import random
from botocore.client import Config
from pillow_heif import register_heif_opener

register_heif_opener()

from dotenv import load_dotenv
load_dotenv()

# --- Detailed Logging Configuration ---
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    stream=sys.stdout,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# --- Runpod API and S3 Configuration ---
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
RUNPOD_ENDPOINT_ID_ALT = os.getenv("RUNPOD_ENDPOINT_ID_ALT")
S3_ENDPOINT_URL = os.getenv("RUNPOD_S3_ENDPOINT_URL")
S3_ACCESS_KEY_ID = os.getenv("RUNPOD_S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.getenv("RUNPOD_S3_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.getenv("RUNPOD_S3_BUCKET_NAME")
S3_REGION = os.getenv("RUNPOD_S3_REGION", "eu-ro-1") # Make region configurable

# --- Validation and S3 Client Initialization ---
if not all([RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID, S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET_NAME]):
    logger.error("CRITICAL: Missing one or more Runpod API or S3 environment variables.")
    s3_client = None
else:
    s3_client = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        region_name=S3_REGION,
        config=Config(signature_version='s3v4')
    )

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
RESULT_DIR = os.path.join(BASE_DIR, "results")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

def prepare_image(path, request_id=""):
    logger.debug(f"[{request_id}] Preparing image: {path}")
    img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    jpg_path = os.path.splitext(path)[0] + ".jpg"
    img.save(jpg_path, format="JPEG")
    logger.debug(f"[{request_id}] Image saved to {jpg_path}")
    return jpg_path

@app.post("/api/tryon")
async def tryon(
    person: UploadFile = File(...), 
    cloth: UploadFile = File(...), 
    garment_des: Optional[str] = Form(None), 
    category: Optional[str] = Form(None)
):
    if not s3_client:
        return JSONResponse(content={"error": "S3 client is not configured."}, status_code=500)

    request_id = uuid.uuid4().hex
    logger.info(f"[{request_id}] Received new try-on request.")

    person_filename = f"person_{request_id}.jpg"
    cloth_filename = f"cloth_{request_id}.jpg"
    local_person_path = os.path.join(UPLOAD_DIR, person_filename)
    local_cloth_path = os.path.join(UPLOAD_DIR, cloth_filename)
    
    s3_person_key = f"uploads/{person_filename}"
    s3_cloth_key = f"uploads/{cloth_filename}"

    final_local_person_path = None
    final_local_cloth_path = None
    result_image_path = None

    try:
        loop = asyncio.get_event_loop()
        
        with open(local_person_path, "wb") as f:
            await loop.run_in_executor(None, shutil.copyfileobj, person.file, f)
        with open(local_cloth_path, "wb") as f:
            await loop.run_in_executor(None, shutil.copyfileobj, cloth.file, f)
        
        final_local_person_path = await loop.run_in_executor(None, prepare_image, local_person_path, request_id)
        final_local_cloth_path = await loop.run_in_executor(None, prepare_image, local_cloth_path, request_id)

        logger.info(f"[{request_id}] Uploading to S3 bucket '{S3_BUCKET_NAME}'")
        await loop.run_in_executor(None, s3_client.upload_file, final_local_person_path, S3_BUCKET_NAME, s3_person_key)
        await loop.run_in_executor(None, s3_client.upload_file, final_local_cloth_path, S3_BUCKET_NAME, s3_cloth_key)
        logger.info(f"[{request_id}] S3 uploads complete.")

        runpod_payload = {
            "person_image_path": s3_person_key,
            "garment_image_path": s3_cloth_key,
            "cloth_type": "upper",
            "seed": -1
        }
        
        # Randomly select between the two endpoints if the ALT is available
        endpoints = [RUNPOD_ENDPOINT_ID]
        if RUNPOD_ENDPOINT_ID_ALT:
            endpoints.append(RUNPOD_ENDPOINT_ID_ALT)
        selected_endpoint_id = random.choice(endpoints)
        
        tryon_url = f"https://{selected_endpoint_id}.api.runpod.ai/api/v1/tryon"
        headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}", "Content-Type": "application/json"}

        logger.info(f"[{request_id}] Sending request to Runpod Load Balancer ({selected_endpoint_id}).")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(tryon_url, headers=headers, json=runpod_payload, timeout=120.0)
        
        response.raise_for_status()
        result = response.json()
        
        result_image_key = result.get('result_image_path')
        if not result_image_key:
             raise ValueError(f"Unexpected output format from worker: {result}")

        result_image_path = os.path.join(RESULT_DIR, f"result_{request_id}.png")
        logger.info(f"[{request_id}] Downloading result '{result_image_key}' from S3 to '{result_image_path}'")
        await loop.run_in_executor(None, s3_client.download_file, S3_BUCKET_NAME, result_image_key, result_image_path)
        logger.info(f"[{request_id}] AI Try-on completed. Result saved to: {result_image_path}")

    except httpx.TimeoutException:
        logger.error(f"[{request_id}] Request to Runpod timed out. The worker may be cold starting or failing.")
        return JSONResponse(content={"error": "The AI worker took too long to respond. Please try again in a few minutes."}, status_code=504) # Gateway Timeout
    except httpx.HTTPStatusError as e:
        logger.error(f"[{request_id}] HTTP error from Runpod: {e.response.status_code} - {e.response.text}")
        return JSONResponse(content={"error": "The AI worker returned an error."}, status_code=502) # Bad Gateway
    except Exception as e:
        logger.exception(f"[{request_id}] An unexpected error occurred.")
        return JSONResponse(content={"error": "An error occurred while processing the request."}, status_code=500)
    finally:
        for f_path in [local_person_path, local_cloth_path, final_local_person_path, final_local_cloth_path]:
            if f_path and os.path.exists(f_path):
                try:
                    os.remove(f_path)
                except OSError:
                    pass

    return {"output": f"/results/{os.path.basename(result_image_path)}"}

from fastapi.staticfiles import StaticFiles
app.mount("/results", StaticFiles(directory=RESULT_DIR), name="results")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server for local development.")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)