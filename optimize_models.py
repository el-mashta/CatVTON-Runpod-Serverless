"""
optimize_models.py (v3 - Idempotent)

A script to optimize the Hugging Face model cache for the CatVTON-Runpod-Serverless project.

This script is designed to be **idempotent**, meaning it is safe to run multiple times.
If the optimizations have already been applied, the script will recognize this and
skip the unnecessary steps.

It performs the following optimizations in-place to reduce cold-start times:

1.  **Prunes the `stable-diffusion-inpainting` repository:**
    -   Deletes the massive, redundant `sd-v1-5-inpainting.ckpt` file.
    -   Deletes all `.bin` model files, keeping only the faster-loading `.safetensors` variants.
    -   Removes the unused `safety_checker` model directory.
    -   Creates compatibility symlinks, skipping if they already exist.

2.  **Prunes and restructures the `CatVTON` repository:**
    -   Selects the best general-purpose attention weights (`mix-48k-1024`) and moves them
        to the expected `attention` subdirectory at the root, skipping if already moved.
    -   Deletes all other unused attention weight variants and files.
"""
import os
import shutil
import logging
from pathlib import Path

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Get the models' root directory from the environment variable, default to /workspace/models
MODELS_ROOT = Path(os.getenv("HF_HOME", "/workspace/models"))

def delete_path(path: Path):
    """Idempotently deletes a file or directory."""
    try:
        if not path.exists() and not path.is_symlink():
            logging.info(f"SKIPPED (already deleted): {path}")
            return
        
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
        logging.info(f"DELETED: {path}")
    except Exception as e:
        logging.error(f"Error deleting {path}: {e}")

def create_symlink(source: Path, link_name: Path):
    """Idempotently creates a relative symbolic link."""
    if link_name.exists() or link_name.is_symlink():
        logging.info(f"SKIPPED (link already exists): {link_name}")
        return
    if not source.exists():
        logging.error(f"Source file for symlink not found: {source}. Cannot create link.")
        return
    try:
        # Create a relative symlink from the link's directory
        os.symlink(source.name, link_name)
        logging.info(f"LINKED: {link_name} -> {source.name}")
    except Exception as e:
        logging.error(f"Error creating symlink {link_name}: {e}")


def clean_stable_diffusion(base_path: Path):
    """Idempotently cleans the stable-diffusion-inpainting directory."""
    logging.info("-" * 50)
    logging.info(f"Optimizing directory: {base_path}")

    if not base_path.is_dir():
        logging.error(f"Directory not found: {base_path}. Aborting cleanup for this model.")
        return

    # 1. Delete the monolithic .ckpt file
    delete_path(base_path / "sd-v1-5-inpainting.ckpt")

    # 2. Delete the unused safety_checker directory
    delete_path(base_path / "safety_checker")

    # 3. Delete all redundant .bin files
    for bin_file in list(base_path.glob("**/*.bin")):
        delete_path(bin_file)

    # 4. Create compatibility symlinks
    logging.info("Verifying compatibility symlinks...")
    # UNet
    unet_dir = base_path / "unet"
    create_symlink(
        source=unet_dir / "diffusion_pytorch_model.fp16.safetensors",
        link_name=unet_dir / "diffusion_pytorch_model.bin"
    )
    # VAE
    vae_dir = base_path / "vae"
    create_symlink(
        source=vae_dir / "diffusion_pytorch_model.fp16.safetensors",
        link_name=vae_dir / "diffusion_pytorch_model.bin"
    )
    # Text Encoder
    text_encoder_dir = base_path / "text_encoder"
    create_symlink(
        source=text_encoder_dir / "model.fp16.safetensors",
        link_name=text_encoder_dir / "pytorch_model.bin"
    )
    
    logging.info(f"Finished optimizing {base_path}")
    logging.info("-" * 50)


def clean_catvton(base_path: Path):
    """Idempotently cleans and restructures the CatVTON model directory."""
    logging.info("-" * 50)
    logging.info(f"Optimizing directory: {base_path}")

    if not base_path.is_dir():
        logging.error(f"Directory not found: {base_path}. Aborting cleanup for this model.")
        return

    # 1. Define paths for the canonical attention model.
    source_attention_dir = base_path / "mix-48k-1024" / "attention"
    target_attention_dir = base_path / "attention"

    # 2. Idempotently move the chosen attention model to the root.
    if target_attention_dir.exists():
        logging.info(f"SKIPPED (already moved): {target_attention_dir}")
    elif source_attention_dir.is_dir():
        try:
            shutil.move(str(source_attention_dir), str(target_attention_dir))
            logging.info(f"MOVED: {source_attention_dir} -> {target_attention_dir}")
        except Exception as e:
            logging.error(f"Could not move attention directory: {e}")
            return # Stop if this critical step fails
    else:
        logging.warning(f"Source attention dir not found: {source_attention_dir}. Cannot perform restructure.")

    # 3. Delete all other model variants and unused files.
    paths_to_delete = [
        base_path / "dresscode-16k-512",
        base_path / "vitonhd-16k-512",
        base_path / "mix-48k-1024",
        base_path / "flux-lora",
        base_path / ".gitattributes",
        base_path / "README.md",
        base_path / "config.json",
    ]

    for path in paths_to_delete:
        delete_path(path)

    logging.info(f"Finished optimizing {base_path}")
    logging.info("-" * 50)


def main():
    """Main function to run the optimization process."""
    logging.info("Starting model optimization script (v3 - Idempotent).")
    logging.info(f"Targeting models root directory: {MODELS_ROOT}")

    sd_path = MODELS_ROOT / "stable-diffusion-inpainting"
    catvton_path = MODELS_ROOT / "CatVTON"

    clean_stable_diffusion(sd_path)
    clean_catvton(catvton_path)

    logging.info("Optimization complete.")

if __name__ == "__main__":
    main()