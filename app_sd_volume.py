# app_sd_volume.py
# PRODUCTION WORKER for Standard CatVTON with Full Network Volume Architecture.
# This server loads EVERYTHING from the network volume:
# - Python source code for CatVTON
# - Python virtual environment (dependencies)
# - All model files (Stable Diffusion Inpainting + CatVTON adapters)

import os
import sys
import logging
import uuid
from contextlib import asynccontextmanager

# --- Dynamic Path Setup ---
# The CatVTON source code is on the network volume, so we must add it to the Python path at runtime.
NETWORK_VOLUME_PATH = "/runpod-volume"
CATVTON_CODE_PATH = os.path.join(NETWORK_VOLUME_PATH, "CatVTON")
if CATVTON_CODE_PATH not in sys.path:
    sys.path.insert(0, CATVTON_CODE_PATH)

# Now that the path is set, we can import the necessary modules.
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image

# CatVTON specific imports
from model.pipeline import CatVTONPipeline
from model.cloth_masker import AutoMasker
from utils import resize_and_crop, resize_and_padding, init_weight_dtype

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- Global Variables ---
pipeline = None
automasker = None

# --- Pydantic Models for API Contracts ---
class TryOnRequest(BaseModel):
    person_image_path: str  # Relative path on the network volume
    garment_image_path: str # Relative path on the network volume
    cloth_type: str = "upper"
    seed: int = -1

class TryOnResponse(BaseModel):
    result_image_path: str # Relative path on the network volume where the result is saved

# --- Model Loading (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline, automasker
    logger.info("Server starting up, preparing to load models from network volume...")

    # Define model paths on the network volume
    base_model_path = os.path.join(NETWORK_VOLUME_PATH, "models", "stable-diffusion-inpainting")
    catvton_model_path = os.path.join(NETWORK_VOLUME_PATH, "models", "CatVTON")
    
    if not os.path.isdir(base_model_path) or not os.path.isdir(catvton_model_path):
        logger.error(f"FATAL: Model directory not found. Searched for '{base_model_path}' and '{catvton_model_path}'.")
        raise RuntimeError("Model directory not found.")

    logger.info(f"Base model path: {base_model_path}")
    logger.info(f"CatVTON adapter path: {catvton_model_path}")

    try:
        logger.info("Initializing CatVTONPipeline...")
        # CORRECTED INITIALIZATION: Pass device and dtype to the constructor.
        pipeline = CatVTONPipeline(
            base_ckpt=base_model_path,
            attn_ckpt=catvton_model_path,
            device="cuda",
            weight_dtype=torch.float16
        )
        logger.info("CatVTONPipeline loaded successfully.")

        logger.info("Initializing AutoMasker...")
        automasker = AutoMasker(
            densepose_ckpt=os.path.join(catvton_model_path, "DensePose"),
            schp_ckpt=os.path.join(catvton_model_path, "SCHP"),
            device='cuda',
        )
        logger.info("AutoMasker loaded successfully.")
        logger.info("All models loaded and ready.")
    except Exception as e:
        logger.exception(f"A critical error occurred during model loading: {e}")
        raise
    yield
    logger.info("Server shutting down.")

# --- FastAPI App Initialization ---
app = FastAPI(lifespan=lifespan)

# --- API Endpoints ---
@app.get("/ping")
async def health_check():
    """Health check endpoint for RunPod load balancer."""
    return {"status": "healthy"}

@app.post("/api/v1/tryon", response_model=TryOnResponse)
async def virtual_tryon(request: TryOnRequest):
    if not pipeline or not automasker:
        logger.warning("Try-on request received before models were fully loaded.")
        raise HTTPException(status_code=503, detail="Worker is not ready or is initializing.")

    try:
        person_image_full_path = os.path.join(NETWORK_VOLUME_PATH, request.person_image_path)
        garment_image_full_path = os.path.join(NETWORK_VOLUME_PATH, request.garment_image_path)

        logger.info(f"Processing request: Person='{person_image_full_path}', Garment='{garment_image_full_path}'")

        if not os.path.exists(person_image_full_path) or not os.path.exists(garment_image_full_path):
            raise HTTPException(status_code=404, detail="Input image not found on network volume.")

        person_image = Image.open(person_image_full_path).convert("RGB")
        garment_image = Image.open(garment_image_full_path).convert("RGB")

        width, height = 768, 1024
        person_image = resize_and_crop(person_image, (width, height))
        garment_image = resize_and_padding(garment_image, (width, height))
        logger.info("Images preprocessed.")

        mask = automasker(person_image, mask_type=request.cloth_type)['mask']
        logger.info("Mask generated.")

        generator = torch.Generator(device='cuda').manual_seed(request.seed) if request.seed != -1 else None

        logger.info("Starting inference pipeline...")
        with torch.inference_mode():
            # The pipeline call in the original code was incorrect for an inpainting model.
            # It requires 'image', 'condition_image', and 'mask'.
            result_image = pipeline(
                image=person_image,
                condition_image=garment_image,
                mask=mask,
                height=height,
                width=width,
                num_inference_steps=50,
                guidance_scale=2.5, # Adjusted to a more standard value for inpainting
                generator=generator
            )[0] # The pipeline returns a list of images
        logger.info("Inference complete.")

        result_filename = f"result_{uuid.uuid4().hex}.png"
        result_relative_path = os.path.join("results", result_filename)
        result_full_path = os.path.join(NETWORK_VOLUME_PATH, result_relative_path)
        
        os.makedirs(os.path.dirname(result_full_path), exist_ok=True)
        
        result_image.save(result_full_path)
        logger.info(f"Result saved to '{result_full_path}'")

        return TryOnResponse(result_image_path=result_relative_path)

    except Exception as e:
        logger.exception(f"An unexpected error occurred during try-on process: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")