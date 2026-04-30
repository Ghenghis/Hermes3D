# GPU Worker Requirements

The Windows worker must detect GPU vendor, model, total VRAM, available VRAM when possible, CUDA status, NVIDIA driver version, and tool availability. Primary target: EVGA FTW3 Ultra RTX 3090 Ti, 24GB VRAM.

Jobs route by capability: image-to-3D -> GPU worker; Blender cleanup -> Blender MCP worker; slicing -> worker with slicer installed; USB printer control -> physically attached worker only.
