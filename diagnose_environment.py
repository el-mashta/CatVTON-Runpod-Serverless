"""
diagnose_environment.py (v2)

An observability script to diagnose the Python, PyTorch, and CUDA environment
within a RunPod worker.

This script runs a series of checks to pinpoint mismatches between the installed
PyTorch library and the underlying NVIDIA driver, which is the most common cause
of the "CUDA driver initialization failed" error.

v2: Made nvidia-smi parsing more robust to handle cases where the driver
does not report a CUDA version.
"""
import sys
import os
import subprocess
import logging

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def print_header(title):
    logging.info("=" * 60)
    logging.info(f"  {title.upper()}")
    logging.info("=" * 60)

def print_check(title, value, status="INFO", indent=2):
    prefix = " " * indent
    status_map = {
        "INFO": "[INFO]",
        "SUCCESS": "[SUCCESS]",
        "WARNING": "[WARNING]",
        "ERROR": "[ERROR]"
    }
    logging.info(f"{prefix}{status_map.get(status, '[INFO]')} {title:<30}: {value}")

def run_command(command):
    """Runs a shell command and returns its output or an error."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip(), None
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip()

def check_environment_variables():
    """Checks for potentially problematic environment variables."""
    print_header("Checking Environment Variables")
    ld_path = os.getenv("LD_LIBRARY_PATH")
    if ld_path:
        print_check("LD_LIBRARY_PATH", ld_path, "WARNING")
        print_check("Analysis", "This variable is set. It can sometimes force PyTorch to use the wrong CUDA libraries.", "WARNING")
    else:
        print_check("LD_LIBRARY_PATH", "Not set", "SUCCESS")

def check_python():
    """Checks the Python interpreter."""
    print_header("Checking Python Environment")
    print_check("Python Executable", sys.executable)
    print_check("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    if "/runpod-volume/" in sys.executable or "/workspace/" in sys.executable:
        print_check("Interpreter Location", "Located on Network Volume", "WARNING")
        print_check("Analysis", "Running a Python binary from a network volume can cause library mismatches.", "WARNING")
    else:
        print_check("Interpreter Location", "Located in Container Filesystem", "SUCCESS")

def check_pytorch_and_cuda():
    """Performs the core PyTorch and CUDA diagnostics."""
    print_header("Checking PyTorch and CUDA")
    try:
        import torch
        print_check("PyTorch Version", torch.__version__, "SUCCESS")
        
        is_cuda_available = torch.cuda.is_available()
        if is_cuda_available:
            print_check("PyTorch CUDA Support", "Available", "SUCCESS")
        else:
            print_check("PyTorch CUDA Support", "NOT AVAILABLE", "ERROR")
            print_check("Analysis", "PyTorch was installed without CUDA support. This is a critical issue.", "ERROR")
            return

        try:
            device_count = torch.cuda.device_count()
            print_check("CUDA Initialization", "Successful", "SUCCESS")
            print_check("Available GPUs", str(device_count), "SUCCESS")
            
            if device_count > 0:
                for i in range(device_count):
                    print_check(f"GPU {i} Name", torch.cuda.get_device_name(i), "INFO", indent=4)
                
                pt_cuda_version = torch.version.cuda
                print_check("PyTorch CUDA Version", pt_cuda_version, "INFO")
                
                smi_output, smi_error = run_command("nvidia-smi --query-gpu=driver_version,cuda_version --format=csv,noheader")
                if smi_error:
                    print_check("NVIDIA Driver Info", "Failed to query nvidia-smi", "ERROR")
                    print_check("nvidia-smi error", smi_error, "ERROR")
                else:
                    smi_values = [v.strip() for v in smi_output.split(',')]
                    if len(smi_values) >= 2:
                        driver_ver, driver_cuda_ver = smi_values[0], smi_values[1]
                        print_check("NVIDIA Driver Version", driver_ver, "INFO")
                        print_check("Driver CUDA Version", driver_cuda_ver, "INFO")
                        
                        if pt_cuda_version.split('.')[0] != driver_cuda_ver.split('.')[0]:
                            print_check("Version Match", "MISMATCH", "ERROR")
                            print_check("Analysis", f"PyTorch expects CUDA {pt_cuda_version} but the driver provides {driver_cuda_ver}. This is a critical incompatibility.", "ERROR")
                        else:
                            print_check("Version Match", "OK", "SUCCESS")
                    else:
                        print_check("NVIDIA Driver Info", "Incomplete output from nvidia-smi", "WARNING")
                        print_check("nvidia-smi output", f"'{smi_output}'", "INFO")
                        print_check("Analysis", "Could not parse both driver and CUDA version. The driver might be old or the environment is unusual.", "WARNING")

        except RuntimeError as e:
            print_check("CUDA Initialization", "FAILED", "ERROR")
            print_check("RuntimeError", str(e), "ERROR")
            print_check("Analysis", "This is the exact error your app is facing. It means PyTorch cannot communicate with the NVIDIA driver.", "ERROR")

    except ImportError:
        print_check("PyTorch", "Not found in this environment.", "ERROR")

def main():
    """Run all diagnostic checks."""
    print_header("Starting Environment Diagnostics")
    check_python()
    check_environment_variables()
    check_pytorch_and_cuda()
    print_header("Diagnostics Complete")

if __name__ == "__main__":
    main()