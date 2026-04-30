# GPU Detection Implementation Requirements

Windows checks: `nvidia-smi`, PyTorch CUDA if installed, ComfyUI device detection if configured.

Expected user hardware example: EVGA FTW3 Ultra RTX 3090 Ti, 24GB VRAM.

Output schema includes worker_id, vendor, GPU name, VRAM, CUDA availability, driver version, and capabilities.

If GPU is not detected, system stays usable but routes heavy jobs to `blocked_no_gpu` with clear operator explanation.
