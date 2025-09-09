"""
upload_file.py

A general-purpose helper script to upload a local file to the RunPod network volume
using its S3-compatible API.

This script reads S3 credentials from the local .env file and uses command-line
arguments to specify which file to upload and where to place it on the volume.
"""
import os
import logging
import argparse
import boto3
from botocore.client import Config
from dotenv import load_dotenv

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def main():
    """Main function to handle argument parsing and the S3 upload."""
    parser = argparse.ArgumentParser(
        description="Upload a local file to a RunPod network volume via S3 API.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--local-path",
        required=True,
        help="The path to the local file you want to upload."
    )
    parser.add_argument(
        "--s3-key",
        required=True,
        help="The destination path (key) on the network volume (e.g., 'optimize_models.py' or 'my_folder/data.zip')."
    )
    args = parser.parse_args()

    # --- Validate Local File ---
    if not os.path.exists(args.local_path):
        logging.error(f"Local file not found: {args.local_path}")
        return

    # --- Load Environment Variables ---
    load_dotenv()
    S3_ENDPOINT_URL = os.getenv("RUNPOD_S3_ENDPOINT_URL")
    S3_ACCESS_KEY_ID = os.getenv("RUNPOD_S3_ACCESS_KEY_ID")
    S3_SECRET_ACCESS_KEY = os.getenv("RUNPOD_S3_SECRET_ACCESS_KEY")
    S3_BUCKET_NAME = os.getenv("RUNPOD_S3_BUCKET_NAME")
    S3_REGION = os.getenv("RUNPOD_S3_REGION", "eu-ro-1")

    # --- Validation ---
    if not all([S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET_NAME]):
        logging.error("CRITICAL: Missing one or more S3 environment variables in your .env file.")
        return

    # --- S3 Client Initialization ---
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=S3_ACCESS_KEY_ID,
            aws_secret_access_key=S3_SECRET_ACCESS_KEY,
            region_name=S3_REGION,
            config=Config(signature_version='s3v4')
        )
        logging.info("S3 client initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize S3 client: {e}")
        return

    # --- Upload the script ---
    try:
        logging.info(f"Uploading '{args.local_path}' to '{S3_BUCKET_NAME}/{args.s3_key}'...")
        
        s3_client.upload_file(
            args.local_path,
            S3_BUCKET_NAME,
            args.s3_key
        )
        
        logging.info("Upload complete.")
        logging.info(f"Successfully uploaded '{args.local_path}' to the network volume as '{args.s3_key}'.")

    except Exception as e:
        logging.error(f"An error occurred during S3 upload: {e}")


if __name__ == "__main__":
    main()
