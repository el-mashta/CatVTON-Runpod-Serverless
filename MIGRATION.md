# Migration and Setup Guide for Network Volume

This document contains the one-time setup instructions for preparing the RunPod Network Volume. This process ensures that the Python environment, source code, and models are all correctly placed on the persistent volume for the serverless worker to use.

## One-Time Network Volume Setup

This procedure must be performed once to prepare your network volume.

1.  **Launch a Temporary Interactive Pod:**
    *   In the RunPod console, go to **GPU Pods** and launch a new interactive pod. The "RunPod PyTorch 2" template is a good choice.
    *   During configuration, attach your Network Volume (e.g., `ebis76cipw`) to the pod.

2.  **Open a Terminal into the Pod:**
    *   Once the pod is running, connect to it and open a terminal.

3.  **Run the Setup Commands:**
    *   Execute the following commands inside the pod's terminal. These commands will create a portable Python environment and install the necessary dependencies.

    ```bash
    # Set environment variables to ensure uv installs everything onto the volume
    export UV_CACHE_DIR=/workspace/uv-cache
    export UV_PYTHON_INSTALL_DIR=/workspace/python-toolchains

    # Install the uv command line tool
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source /root/.cargo/env

    # Install a specific Python version onto the network volume
    uv python install 3.9

    # Create a self-contained, portable virtual environment on the volume
    uv venv /workspace/venv --python 3.9 --seed

    # Activate the new virtual environment
    source /workspace/venv/bin/activate

    # Install all Python dependencies from the requirements file
    uv pip install -r /workspace/CatVTON/requirements.txt
    
    # Install the correct PyTorch version for the CUDA 12.1 toolkit
    # Migration and Setup Guide for a Portable Network Volume Environment

This document contains the one-time setup instructions for preparing the RunPod Network Volume. This process creates a **fully portable and self-contained** Python environment, ensuring that it will work correctly across different serverless workers regardless of the host machine's configuration.

## One-Time Network Volume Setup

This procedure must be performed once to prepare your network volume.

1.  **Launch a Temporary Interactive Pod:**
    *   In the RunPod console, go to **GPU Pods** and launch a new interactive pod.
    *   **Crucially, select a template that matches your serverless worker's GPU type.** For example, if your serverless endpoint uses RTX 4090s, deploy a pod with an RTX 4090. This ensures driver compatibility. The "RunPod PyTorch 2" template is a good choice.
    *   During configuration, attach your Network Volume to the pod at the `/workspace` mount point.

2.  **Open a Terminal into the Pod:**
    *   Once the pod is running, connect to it and open a terminal.

3.  **Run the Setup Commands:**
    *   Execute the following commands inside the pod's terminal. These commands will create a fully portable Python environment and install the necessary dependencies directly onto the network volume.

    ```bash
    # ==============================================================================
    #   PORTABLE PYTHON ENVIRONMENT SETUP SCRIPT (v2)
    # ==============================================================================
    # This script creates a fully portable Python environment on the network volume.

    # --- STEP 1: Configure uv to store everything on the network volume ---
    # This is the key to portability.
    export UV_CACHE_DIR=/workspace/uv-cache
    export UV_PYTHON_INSTALL_DIR=/workspace/python-toolchains
    echo "[CONFIG] uv cache is now at: ${UV_CACHE_DIR}"
    echo "[CONFIG] uv Python installs will be in: ${UV_PYTHON_INSTALL_DIR}"

    # --- STEP 2: Install the uv tool itself (if not already present) ---
    # The installer is smart and will skip if uv is already installed.
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Note: You may need to source the correct profile file, e.g., source /root/.bashrc or similar
    source $HOME/.cargo/env

    # --- STEP 3: Install a self-contained Python interpreter onto the volume ---
    echo "[SETUP] Installing Python 3.9 onto the network volume..."
    uv python install 3.9

    # --- STEP 4: Create the virtual environment using the portable Python ---
    # We explicitly point to the Python interpreter we just installed.
    # The wildcard (*) handles the specific patch version directory name.
    echo "[SETUP] Creating virtual environment at /workspace/venv..."
    uv venv /workspace/venv --python /workspace/python-toolchains/cpython-3.9.*/bin/python

    # --- STEP 5: Activate and Install Dependencies ---
    echo "[SETUP] Activating venv and installing project requirements..."
    source /workspace/venv/bin/activate

    # Install all dependencies into the portable venv
    uv pip install -r /workspace/CatVTON/requirements.txt

    # --- STEP 6: Verification ---
    echo "[VERIFY] Verifying Python interpreter path..."
    which python
    # The output should be: /workspace/venv/bin/python

    echo "[SUCCESS] Portable Python environment has been created successfully."
    echo "You can now terminate this pod. The environment on the network volume is ready."
    ```

4.  **Terminate the Pod:**
    *   Once the commands complete successfully, you can stop and terminate this temporary pod.

Your network volume is now fully prepared with a robust, portable, and reproducible Python environment that will not conflict with the serverless worker's host environment.
    ```

4.  **Verify and Terminate:**
    *   You can verify the setup with `ls -l /workspace/venv/bin/python`. It should **not** be a symlink to the `/root` directory.
    *   Once the commands complete successfully, you can stop and terminate this temporary pod.

Your network volume is now fully prepared with a stable and reproducible set of dependencies compatible with modern GPUs.
