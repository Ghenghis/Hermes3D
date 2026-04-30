# Dual Edition Architecture

```text
Remote browser / phone / laptop
        ↓
Ubuntu VPS Hermes3D Control Server
        ↓ secure tunnel
Windows Hermes3D GPU Worker
        ↓
NVIDIA 3090 Ti + Blender MCP + ComfyUI + Slicers + Printrun + Printer LAN
```

The UI must not fork. Desktop mode talks mostly to local backend. VPS mode talks to the VPS backend, which routes work to registered workers. Shared packages include API schemas, job model, proof model, adapter model, agent event model, and UI state model.
