# Worker API Contract

Endpoints: `/health`, `/capabilities`, `/gpu`, `/tools`, `/jobs`, `/jobs/{job_id}`, `/jobs/{job_id}/cancel`, `/artifacts/{artifact_id}`.

Allowed job types: blender_mcp_smoke, blender_export_3mf, slice_to_staging, comfyui_generate_3d, printer_status_scan, proof_bundle_build.

Forbidden: raw shell command jobs, arbitrary Python from VPS, printer heating/movement unless write-control gate is enabled.
