# Adapter Boundary Architecture

External projects are used through adapters. Hermes3D must not become a monorepo containing Blender, slicers, printer UIs, and service code inside core logic.

```text
/source-lab/<tool-name>/      optional cloned source repos
/tools/<tool-name>/           installed binaries or portable apps
/hermes3d/adapters/<tool>/    stable integration code
/hermes3d/ui/panels/<tool>/   dock/undock panels
```

Each adapter exposes detect, version, capabilities, healthcheck, open_docked, open_undocked, open_external, and gated tool-specific read/write methods.
