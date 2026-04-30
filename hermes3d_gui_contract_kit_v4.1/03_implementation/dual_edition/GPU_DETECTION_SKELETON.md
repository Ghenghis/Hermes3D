# GPU Detection Skeleton

Windows detection order: nvidia-smi, Python torch.cuda if installed, Windows WMI fallback, safe unavailable state. Tests must mock nvidia-smi present, absent, RTX 3090 Ti detected, and no GPU detected.
