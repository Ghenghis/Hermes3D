# Tool Install Verification Commands

```bash
blender --version
uvx blender-mcp --help || true
claude mcp list
prusa-slicer --version
orca-slicer --version || OrcaSlicer --version
pronsole --help || python -m printrun.pronsole --help
cura --version || Ultimaker-Cura --version
curl http://<printer-ip>:7125/server/info
curl http://<octoprint-host>/api/version
curl -I http://<fluidd-host>/
curl -I http://<mainsail-host>/
```

FLSUN Slicer requires Windows path detection; record executable path and file version.
