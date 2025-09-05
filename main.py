import logging
import sys
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image, ImageOps
import base64
import json
import shutil
import uuid
import os
import boto3
import httpx
import asyncio
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
S3_ENDPOINT_URL = os.getenv("RUNPOD_S3_ENDPOINT_URL")
S3_ACCESS_KEY_ID = os.getenv("RUNPOD_S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.getenv("RUNPOD_S3_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.getenv("RUNPOD_S3_BUCKET_NAME") # Bucket name is the same as the endpoint ID

# --- Validation and S3 Client Initialization ---
if not all([RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID, S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY]):
    logger.error("CRITICAL: Missing one or more Runpod API or S3 environment variables.")
    s3_client = None
else:
    s3_client = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        region_name="eu-ro-1",
        config=Config(signature_version='s3v4')
    )

app = FastAPI()

# (CORS Middleware remains the same)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Simplified for brevity, use your specific origins
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
    # This function remains the same
    logger.debug(f"[{request_id}] Preparing image: {path}")
    img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    jpg_path = os.path.splitext(path)[0] + ".jpg"
    img.save(jpg_path, format="JPEG")
    logger.debug(f"[{request_id}] Image saved to {jpg_path}")
    return jpg_path

def image_to_base64(filepath):
    with open(filepath, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

@app.post("/api/tryon")
async def tryon(person: UploadFile = File(...), cloth: UploadFile = File(...), garment_des: str = Form("shirt"), category: str = Form("upper_body")):
    request_id = uuid.uuid4().hex
    logger.info(f"[{request_id}] Received new try-on request.")

    person_filename = f"person_{request_id}.jpg"
    cloth_filename = f"cloth_{request_id}.jpg"
    local_person_path = os.path.join(UPLOAD_DIR, person_filename)
    local_cloth_path = os.path.join(UPLOAD_DIR, cloth_filename)
    result_image_path = None

    try:
        loop = asyncio.get_event_loop()
        
        with open(local_person_path, "wb") as f:
            await loop.run_in_executor(None, shutil.copyfileobj, person.file, f)
        with open(local_cloth_path, "wb") as f:
            await loop.run_in_executor(None, shutil.copyfileobj, cloth.file, f)
        
        final_local_person_path = await loop.run_in_executor(None, prepare_image, local_person_path, request_id)
        final_local_cloth_path = await loop.run_in_executor(None, prepare_image, local_cloth_path, request_id)

        person_b64 = image_to_base64(final_local_person_path)
        cloth_b64 = image_to_base64(final_local_cloth_path)

        tryon_url = f"https://{RUNPOD_ENDPOINT_ID}.api.runpod.ai/api/v1/tryon"
        headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "person_image": person_b64,
            "garment_image": cloth_b64
        }

        logger.info(f"[{request_id}] Sending POST request to custom load balancer endpoint.")

        async with httpx.AsyncClient() as client:
            response = await client.post(tryon_url, headers=headers, json=payload, timeout=300)
        
        response.raise_for_status()
        result = response.json()

        output_data = result.get('output', {})
        
        # Assuming the output contains a base64 image string
        image_b64_data = output_data.get('images', [{}])[0].get('image')

        if not image_b64_data:
            raise ValueError("Output from worker is not a valid base64 image string.")

        image_data = base64.b64decode(image_b64_data)
        result_image_path = os.path.join(RESULT_DIR, f"result_{request_id}.png")
        with open(result_image_path, "wb") as f:
            f.write(image_data)
        logger.info(f"[{request_id}] AI Try-on completed. Result saved to: {result_image_path}")

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
    uvicorn.run("main_prod_s3_upload:app", host="0.0.0.0", port=8000, reload=True)