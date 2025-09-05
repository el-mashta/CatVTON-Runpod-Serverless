# app_flux_s3.py
# PRODUCTION WORKER: This FastAPI server uses the superior Network Volume architecture.
# It reads input files directly from the local /runpod-volume mount point for maximum speed
# and uploads the final result back to the volume via the S3 API.

import os
import uuid
import logging
from contextlib import asynccontextmanager

import torch
import boto3
from botocore.client import Config
from diffusers.image_processor import VaeImageProcessor
from fastapi import FastAPI, HTTPException
from PIL import Image
from pydantic import BaseModel

# Import FLUX pipeline and other CatVTON modules
from CatVTON.model.flux.pipeline_flux_tryon import FluxTryOnPipeline
from CatVTON.model.cloth_masker import AutoMasker
from CatVTON.utils import resize_and_crop, resize_and_padding

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Global Variables ---
pipeline = None
automasker = None
mask_processor = None
s3_client = None
S3_BUCKET_NAME = None
NETWORK_VOLUME_PATH = "/runpod-volume"

# --- Pydantic Models for API Contracts ---
class TryOnRequestS3(BaseModel):
    person_image_key: str
    garment_image_key: str
    cloth_type: str = "upper"
    seed: int = -1

class TryOnResponseS3(BaseModel):
    result_image_key: str

# --- Model & S3 Client Loading (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline, automasker, mask_processor, s3_client, S3_BUCKET_NAME
    logger.info("Server starting up, loading models and initializing S3 client...")

    # --- S3 Configuration (for UPLOADING results) ---
    S3_ENDPOINT_URL = os.getenv("RUNPOD_S3_ENDPOINT_URL")
    S3_ACCESS_KEY_ID = os.getenv("RUNPOD_S3_ACCESS_KEY_ID")
    S3_SECRET_ACCESS_KEY = os.getenv("RUNPOD_S3_SECRET_ACCESS_KEY")
    S3_BUCKET_NAME = os.getenv("RUNPOD_S3_BUCKET_NAME")

    if not all([S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET_NAME]):
        raise RuntimeError("Missing one or more required S3 environment variables for uploading.")

    s3_client = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4')
    )
    logger.info(f"S3 client initialized for bucket '{S3_BUCKET_NAME}'.")

    # --- Model Loading ---
    # Models are now loaded from the network volume for faster cold starts.
    base_model_path = "/runpod-volume/models/FLUX.1-Fill-dev"
    resume_path = "/runpod-volume/models/CatVTON"
    try:
        pipeline = FluxTryOnPipeline.from_pretrained(base_model_path)
        pipeline.load_lora_weights(os.path.join(resume_path, "flux-lora"), weight_name='pytorch_lora_weights.safetensors')
        pipeline.to("cuda", torch.bfloat16)
        automasker = AutoMasker(
            densepose_ckpt=os.path.join(resume_path, "DensePose"),
            schp_ckpt=os.path.join(resume_path, "SCHP"),
            device='cuda',
        )
        mask_processor = VaeImageProcessor(
            vae_scale_factor=8, do_normalize=False, do_binarize=True, do_convert_grayscale=True
        )
        logger.info("All models loaded successfully.")
    except Exception as e:
        logger.exception(f"An error occurred during model loading: {e}")
        raise
    yield
    logger.info("Server shutting down.")

# --- FastAPI App Initialization ---
app = FastAPI(lifespan=lifespan)

# --- API Endpoints ---
@app.get("/ping")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/v1/tryon-s3", response_model=TryOnResponseS3)
async def virtual_tryon_s3(request: TryOnRequestS3):
    if not all([pipeline, automasker, s3_client]):
        raise HTTPException(status_code=503, detail="Worker is not ready.")

    request_id = uuid.uuid4().hex
    
    # --- OPTIMIZATION: Read directly from the mounted Network Volume ---
    local_person_path = os.path.join(NETWORK_VOLUME_PATH, request.person_image_key)
    local_garment_path = os.path.join(NETWORK_VOLUME_PATH, request.garment_image_key)
    local_result_path = f"/tmp/result_{request_id}.png" # Use /tmp for ephemeral result file

    try:
        # 1. Read images directly from the filesystem
        logger.info(f"Reading '{local_person_path}' and '{local_garment_path}' from network volume.")
        if not os.path.exists(local_person_path) or not os.path.exists(local_garment_path):
            raise HTTPException(status_code=404, detail="Input file not found on network volume.")
            
        person_image = Image.open(local_person_path).convert("RGB")
        garment_image = Image.open(local_garment_path).convert("RGB")

        # 2. Preprocess images
        width, height = 768, 1024
        person_image = resize_and_crop(person_image, (width, height))
        garment_image = resize_and_padding(garment_image, (width, height))

        # 3. Generate mask
        mask = automasker(person_image, request.cloth_type)['mask']
        mask = mask_processor.blur(mask, blur_factor=9)

        # 4. Set up generator
        generator = torch.Generator(device='cuda').manual_seed(request.seed) if request.seed != -1 else None

        # 5. Run inference
        logger.info(f"Running FLUX inference for request {request_id}")
        result_image = pipeline(
            image=person_image,
            condition_image=garment_image,
            mask_image=mask,
            height=height,
            width=width,
            num_inference_steps=50,
            guidance_scale=30.0,
            generator=generator
        ).images[0]
        logger.info("Inference complete.")

        # 6. Save result locally and upload to S3
        result_image.save(local_result_path, format="PNG")
        result_image_key = f"results/result_{request_id}.png"
        
        logger.info(f"Uploading '{local_result_path}' to S3 as '{result_image_key}'")
        s3_client.upload_file(local_result_path, S3_BUCKET_NAME, result_image_key)

        return TryOnResponseS3(result_image_key=result_image_key)

    except Exception as e:
        logger.exception(f"An unexpected error occurred during try-on: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")
    finally:
        # 7. Clean up local temporary file
        if os.path.exists(local_result_path):
            os.remove(local_result_path)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)