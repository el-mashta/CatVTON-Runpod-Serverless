import os
import subprocess
import websockets
import uuid
import httpx
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import json

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Pydantic Models for API Contracts ---
class TryonRequest(BaseModel):
    person_image: str  # base64 encoded string
    garment_image: str # base64 encoded string

# --- FastAPI App ---
app = FastAPI()
comfyui_process = None

# --- ComfyUI Workflow Management ---
def load_workflow():
    """Loads the ComfyUI workflow template from a JSON file."""
    try:
        with open("catvton_workflow.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("catvton_workflow.json not found!")
        return None

@app.on_event("startup")
def startup_event():
    """On startup, launch the ComfyUI server as a background process."""
    global comfyui_process
    # The official worker places ComfyUI at /comfyui
    comfyui_path = "/comfyui/main.py"
    if not os.path.exists(comfyui_path):
        logger.error(f"ComfyUI main.py not found at {comfyui_path}")
        return

    command = ["python3", comfyui_path, "--listen", "127.0.0.1", "--port", "8188"]
    logger.info(f"Starting ComfyUI with command: {" ".join(command)}")
    comfyui_process = subprocess.Popen(command)
    logger.info(f"ComfyUI process started with PID: {comfyui_process.pid}")

@app.on_event("shutdown")
def shutdown_event():
    """On shutdown, terminate the ComfyUI process."""
    if comfyui_process:
        logger.info("Terminating ComfyUI process.")
        comfyui_process.terminate()

# --- API Endpoints ---
@app.get("/ping")
async def health_check():
    """Health check endpoint required by Runpod for load balancing."""
    return {"status": "healthy"}

import base64
import uuid

# ... (keep existing imports)

async def get_image_data(prompt_id, client_id):
    """Connects to ComfyUI websocket and waits for the output image."""
    uri = "ws://127.0.0.1:8188/ws?clientId={}".format(client_id)
    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"WebSocket connected for prompt_id: {prompt_id}")
            while True:
                try:
                    out = await asyncio.wait_for(websocket.recv(), timeout=120) # 2 minute timeout
                    if isinstance(out, str):
                        message = json.loads(out)
                        if message.get('type') == 'executed' and message.get('data', {}).get('prompt_id') == prompt_id:
                            logger.info(f"Execution complete for prompt_id: {prompt_id}")
                            data = message['data']['output']['images'][0]
                            return data
                except asyncio.TimeoutError:
                    logger.error(f"Timeout waiting for message from ComfyUI for prompt {prompt_id}")
                    return None
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        return None

@app.post("/api/v1/tryon")
async def virtual_tryon(request: TryonRequest):
    """The main endpoint to perform the virtual try-on."""
    workflow = load_workflow()
    if not workflow:
        raise HTTPException(status_code=500, detail="Workflow file not found on server.")

    # --- Image Handling ---
    request_uuid = uuid.uuid4()
    person_filename = f"{request_uuid}_person.png"
    garment_filename = f"{request_uuid}_garment.png"
    comfy_input_path = "/comfyui/input"
    os.makedirs(comfy_input_path, exist_ok=True)

    try:
        with open(os.path.join(comfy_input_path, person_filename), "wb") as f:
            f.write(base64.b64decode(request.person_image))
        with open(os.path.join(comfy_input_path, garment_filename), "wb") as f:
            f.write(base64.b64decode(request.garment_image))
        logger.info(f"Saved input images to {comfy_input_path}")
    except (base64.binascii.Error, IOError) as e:
        logger.error(f"Error decoding or saving image: {e}")
        raise HTTPException(status_code=400, detail="Invalid base64 image data.")

    # --- Workflow Modification ---
    for node in workflow.get("nodes", []):
        if node.get("id") == 10:
            node["widgets_values"] = [person_filename, "image"]
        elif node.get("id") == 11:
            node["widgets_values"] = [garment_filename, "image"]

    # --- ComfyUI Interaction ---
    try:
        client_id = str(uuid.uuid4())
        payload = {"prompt": workflow, "client_id": client_id}
        
        async with httpx.AsyncClient() as client:
            logger.info("Sending prompt to local ComfyUI server.")
            response = await client.post("http://127.0.0.1:8188/prompt", json=payload, timeout=30)
            response.raise_for_status()
            prompt_id = response.json().get('prompt_id')
            logger.info(f"Prompt submitted with ID: {prompt_id}")

        if not prompt_id:
            raise HTTPException(status_code=500, detail="Failed to get prompt ID from ComfyUI.")

        image_data = await get_image_data(prompt_id, client_id)

        if not image_data:
            raise HTTPException(status_code=500, detail="Failed to retrieve image from ComfyUI.")

        # Read the output image and encode it to base64
        output_image_path = f"/comfyui/output/{image_data['filename']}"
        if not os.path.exists(output_image_path):
             raise HTTPException(status_code=500, detail="Output image file not found.")

        with open(output_image_path, "rb") as f:
            b64_image = base64.b64encode(f.read()).decode('utf-8')

        logger.info("Successfully processed try-on request.")
        return {"output": {"images": [{"image": b64_image}]}}

    except httpx.RequestError as e:
        logger.error(f"Error communicating with ComfyUI: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable: cannot connect to ComfyUI.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
