import uvicorn
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4009))
    logger.info(f"Starting server on host 0.0.0.0 and port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
