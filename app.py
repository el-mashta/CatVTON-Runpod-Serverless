# app.py
# This is the main application file for the FastAPI server.

import os
import base64
import io
import logging
from contextlib import asynccontextmanager

import torch
from diffusers.image_processor import VaeImageProcessor
from fastapi import FastAPI, HTTPException
from PIL import Image
from pydantic import BaseModel
import numpy as np

# Import CatVTON specific modules from the subdirectory
from CatVTON.model.pipeline import CatVTONPipeline
from CatVTON.model.cloth_masker import AutoMasker
from CatVTON.utils import init_weight_dtype, resize_and_crop, resize_and_padding

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Global Variables for Models ---
# These will be loaded once at startup and reused across requests.
pipeline = None
automasker = None
mask_processor = None

# --- Pydantic Models for API Contracts ---
class TryonRequest(BaseModel):
    person_image: str  # Base64 encoded string of the person's image
    garment_image: str # Base64 encoded string of the garment image
    cloth_type: str = "upper" # Default to upper body, can be "lower" or "overall"
    seed: int = -1 # Optional random seed, -1 for random

class TryonResponse(BaseModel):
    result_image: str # Base64 encoded string of the final image

# --- Model Loading and Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the AI models on startup and clear them on shutdown."""
    global pipeline, automasker, mask_processor
    logger.info("Server starting up, loading models...")

    # Get model paths from environment variables set in the Dockerfile
    base_model_path = os.getenv("BASE_MODEL_PATH", "/app/models/stable-diffusion-inpainting")
    resume_path = os.getenv("RESUME_PATH", "/app/models/CatVTON")

    if not os.path.exists(base_model_path) or not os.path.exists(resume_path):
        logger.error("Model paths not found! Check Dockerfile and model download stage.")
        raise RuntimeError("Could not find models. Aborting startup.")

    try:
        # Initialize the CatVTON Pipeline
        pipeline = CatVTONPipeline(
            base_ckpt=base_model_path,
            attn_ckpt=resume_path,
            attn_ckpt_version="mix",
            weight_dtype=init_weight_dtype("bf16"), # Using bf16 as a default
            use_tf32=True,
            device='cuda'
        )
        logger.info("CatVTONPipeline loaded successfully.")

        # Initialize the AutoMasker for generating clothing masks
        automasker = AutoMasker(
            densepose_ckpt=os.path.join(resume_path, "DensePose"),
            schp_ckpt=os.path.join(resume_path, "SCHP"),
            device='cuda',
        )
        logger.info("AutoMasker loaded successfully.")

        # Initialize the mask processor
        mask_processor = VaeImageProcessor(
            vae_scale_factor=8, do_normalize=False, do_binarize=True, do_convert_grayscale=True
        )
        logger.info("Mask processor initialized.")

    except Exception as e:
        logger.exception(f"An error occurred during model loading: {e}")
        raise

    yield # The application is now running

    # --- Shutdown Logic ---
    logger.info("Server shutting down, clearing models...")
    pipeline = None
    automasker = None
    mask_processor = None
    torch.cuda.empty_cache()

# --- FastAPI App Initialization ---
app = FastAPI(lifespan=lifespan)

# --- API Endpoints ---
@app.get("/ping")
async def health_check():
    """Health check endpoint required by Runpod for load balancing."""
    return {"status": "healthy"}

@app.post("/api/v1/tryon", response_model=TryonResponse)
async def virtual_tryon(request: TryonRequest):
    """The main endpoint to perform the virtual try-on."""
    if not pipeline or not automasker:
        raise HTTPException(status_code=503, detail="Models are not loaded or ready.")

    try:
        # 1. Decode base64 images
        person_image_bytes = base64.b64decode(request.person_image)
        garment_image_bytes = base64.b64decode(request.garment_image)

        person_image = Image.open(io.BytesIO(person_image_bytes)).convert("RGB")
        garment_image = Image.open(io.BytesIO(garment_image_bytes)).convert("RGB")

        # 2. Preprocess images
        width, height = 768, 1024
        person_image = resize_and_crop(person_image, (width, height))
        garment_image = resize_and_padding(garment_image, (width, height))

        # 3. Generate mask automatically
        mask = automasker(
            person_image,
            request.cloth_type
        )['mask']
        mask = mask_processor.blur(mask, blur_factor=9)

        # 4. Set up generator for reproducibility if seed is provided
        generator = None
        if request.seed != -1:
            generator = torch.Generator(device='cuda').manual_seed(request.seed)

        # 5. Run the pipeline
        logger.info(f"Running inference with cloth_type: {request.cloth_type} and seed: {request.seed}")
        result_image = pipeline(
            image=person_image,
            condition_image=garment_image,
            mask=mask,
            num_inference_steps=50, # Using a reasonable default
            guidance_scale=2.5,     # Using a reasonable default
            generator=generator
        )[0]
        logger.info("Inference complete.")

        # 6. Encode result image to base64
        buffered = io.BytesIO()
        result_image.save(buffered, format="PNG")
        result_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        return TryonResponse(result_image=result_base64)

    except base64.binascii.Error:
        raise HTTPException(status_code=400, detail="Invalid base64 string for an image.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during try-on: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)