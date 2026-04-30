# Secure Remote GPU Worker Architecture

The VPS never directly uses the user's GPU. The VPS routes jobs to the Windows Desktop GPU Worker through a secure tunnel.

```text
Browser / Phone
  -> Ubuntu VPS Control Server
  -> Auth + Job Queue + Proof Viewer
  -> Secure Tunnel
  -> Windows Desktop GPU Worker
  -> RTX 3090 Ti / Blender / ComfyUI / Slicers / LAN printers
```

Required channels: control, event, artifact, health.

Security boundaries: typed job types only, allowlisted local command templates, no raw shell passthrough, signed/logged worker actions, printer-control write actions require explicit adapter permission.
