# Install / Clone Plan

Claude may create scripts, but must follow this plan:

```text
mkdir -p source-lab installed-tools var/proof-bundles
```

For each registry item:
1. If user supplied zip exists, register it as local source.
2. If official repo exists, clone to `source-lab/<key>` only when needed.
3. Prefer installed binary for Blender/slicers.
4. Do not build large apps from source unless explicitly requested.
5. After detection, write `var/tool-detection/<key>.json`.

## Clone commands examples
```bash
git clone https://github.com/blender/blender source-lab/blender
git clone https://github.com/Flsun3d/FlsunSlicer source-lab/flsun_slicer
git clone https://github.com/prusa3d/PrusaSlicer source-lab/prusa_slicer
git clone https://github.com/SoftFever/OrcaSlicer source-lab/orca_slicer
git clone https://github.com/kliment/Printrun source-lab/printrun
git clone https://github.com/Arksine/moonraker source-lab/moonraker
git clone https://github.com/fluidd-core/fluidd source-lab/fluidd
git clone https://github.com/mainsail-crew/mainsail source-lab/mainsail
git clone https://github.com/OctoPrint/OctoPrint source-lab/octoprint
git clone https://github.com/ahujasid/blender-mcp source-lab/blender_mcp_ahujasid
git clone https://github.com/VxASI/blender-mcp-vxai source-lab/blender_mcp_vxai
```
