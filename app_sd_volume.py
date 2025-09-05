# app_sd_volume.py
# PRODUCTION WORKER for Standard CatVTON with Full Network Volume Architecture.
# This server loads EVERYTHING from the network volume:
# - Python source code for CatVTON
# - Python virtual environment (dependencies)
# - All model files (Stable Diffusion Inpainting + CatVTON adapters)

import os
import sys
import logging
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
from utils import resize_and_crop, resize_and_padding

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
    
    # Check if model paths exist before loading
    if not os.path.isdir(base_model_path):
        logger.error(f"FATAL: Base model directory not found at '{base_model_path}'. The worker cannot start.")
        raise RuntimeError(f"Base model directory not found: {base_model_path}")
    if not os.path.isdir(catvton_model_path):
        logger.error(f"FATAL: CatVTON model directory not found at '{catvton_model_path}'. The worker cannot start.")
        raise RuntimeError(f"CatVTON model directory not found: {catvton_model_path}")

    logger.info(f"Base model path: {base_model_path}")
    logger.info(f"CatVTON adapter path: {catvton_model_path}")

    try:
        logger.info("Initializing CatVTONPipeline...")
        pipeline = CatVTONPipeline(
            base_ckpt=base_model_path,
            attn_ckpt=catvton_model_path,
        ).to("cuda", torch.float16)
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
    # If this endpoint is reachable, it means the lifespan startup was successful.
    return {"status": "healthy"}

@app.post("/api/v1/tryon", response_model=TryOnResponse)
async def virtual_tryon(request: TryOnRequest):
    if not pipeline or not automasker:
        logger.warning("Try-on request received before models were fully loaded.")
        raise HTTPException(status_code=503, detail="Worker is not ready or is initializing.")

    try:
        # Construct full paths from the relative paths provided in the request
        person_image_full_path = os.path.join(NETWORK_VOLUME_PATH, request.person_image_path)
        garment_image_full_path = os.path.join(NETWORK_VOLUME_PATH, request.garment_image_path)

        logger.info(f"Processing request: Person='{person_image_full_path}', Garment='{garment_image_full_path}'")

        if not os.path.exists(person_image_full_path):
            raise HTTPException(status_code=404, detail=f"Person image not found at: {person_image_full_path}")
        if not os.path.exists(garment_image_full_path):
            raise HTTPException(status_code=404, detail=f"Garment image not found at: {garment_image_full_path}")

        person_image = Image.open(person_image_full_path).convert("RGB")
        garment_image = Image.open(garment_image_full_path).convert("RGB")

        # Preprocess images
        width, height = 768, 1024
        person_image = resize_and_crop(person_image, (width, height))
        garment_image = resize_and_padding(garment_image, (width, height))
        logger.info("Images preprocessed.")

        # Generate mask
        mask = automasker(person_image, cloth_type=request.cloth_type)['mask']
        logger.info("Mask generated.")

        # Set up generator for reproducibility
        generator = torch.Generator(device='cuda').manual_seed(request.seed) if request.seed != -1 else None

        # Run inference
        logger.info("Starting inference pipeline...")
        with torch.inference_mode():
            result_image = pipeline(
                image=person_image,
                condition_image=garment_image,
                mask_image=mask,
                height=height,
                width=width,
                num_inference_steps=50,
                guidance_scale=7.5,
                generator=generator
            ).images[0]
        logger.info("Inference complete.")

        # Save result back to the network volume
        result_filename = f"result_{os.path.basename(request.person_image_path)}_{os.path.basename(request.garment_image_path)}"
        result_relative_path = os.path.join("results", result_filename)
        result_full_path = os.path.join(NETWORK_VOLUME_PATH, result_relative_path)
        
        # Ensure the results directory exists
        os.makedirs(os.path.dirname(result_full_path), exist_ok=True)
        
        result_image.save(result_full_path)
        logger.info(f"Result saved to '{result_full_path}'")

        return TryOnResponse(result_image_path=result_relative_path)

    except Exception as e:
        logger.exception(f"An unexpected error occurred during try-on process: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")
