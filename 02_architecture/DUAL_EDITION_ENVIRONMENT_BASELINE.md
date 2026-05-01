# Dual-Edition Environment Baseline — Phase 0

> **Status:** Phase 0 baseline document. Derived from `hermes3d_gui_contract_kit_v4.1/` specs + a one-time probe of the canonical reference host. This document publishes findings — Phase 1 implements the detection script + schema.

## 1. Editions

Per [`DUAL_EDITION_REQUIREMENTS.md`](../hermes3d_gui_contract_kit_v4.1/01_requirements/DUAL_EDITION_REQUIREMENTS.md) and [`DUAL_EDITION_ARCHITECTURE.md`](../hermes3d_gui_contract_kit_v4.1/02_architecture/DUAL_EDITION_ARCHITECTURE.md):

| Edition | Owns | Runs on |
|---|---|---|
| **Windows Desktop GPU Worker** | GPU jobs, Blender, ComfyUI, slicers, USB-attached printers, LAN-attached printers, local proof signing | User's Windows machine |
| **Ubuntu VPS Control Server** | Auth, job queue, registry, secure tunnel termination, proof archive, WebSocket dispatch | Internet-reachable Linux VPS |
| **Shared (one product)** | Routes, visual language, job states, proof schema, adapter status surface, agent activity stream | Both — single React/Tailwind UI surface |

**Topology** (per [`SECURE_REMOTE_GPU_WORKER_ARCHITECTURE.md`](../hermes3d_gui_contract_kit_v4.1/02_architecture/SECURE_REMOTE_GPU_WORKER_ARCHITECTURE.md)):

```
Browser / Phone
  ─→ Ubuntu VPS Control Server (auth + queue + proof viewer)
       ─→ Secure Tunnel (Tailscale preferred / Cloudflare Tunnel optional / WireGuard advanced)
            ─→ Windows Desktop GPU Worker
                 ─→ RTX-class GPU / Blender / ComfyUI / Slicers / LAN printers
```

**Hard rule** (kit-canonical): the VPS never directly uses GPU. All GPU work routes to a Windows worker through the tunnel. The VPS cannot send raw shell to the worker — only typed, allowlisted job classes.

## 2. Canonical reference host

This Phase 0 baseline was probed on the user's Windows host on 2026-04-30. The host satisfies the canonical "Desktop GPU Worker" hardware profile from [`GPU_WORKER_REQUIREMENTS.md`](../hermes3d_gui_contract_kit_v4.1/01_requirements/GPU_WORKER_REQUIREMENTS.md) (reference: EVGA FTW3 RTX 3090 Ti, 24 GB VRAM).

| Resource | Detected | Detail |
|---|---|---|
| OS | Windows 11 Pro | 10.0.26100 |
| CPU | AMD Ryzen 7 5800X3D | 8 cores / 16 logical processors |
| RAM | 127.9 GB | `Win32_ComputerSystem.TotalPhysicalMemory` |
| GPU (`nvidia-smi`) | NVIDIA GeForce RTX 3090 Ti | 24,564 MiB total VRAM, driver 591.86 |
| GPU (WMI) | NVIDIA GeForce RTX 3090 Ti | `AdapterRAM` = 4,293,918,720 — saturated 32-bit DWORD (see §4) |
| CUDA | available via driver | `nvidia-smi` succeeds |
| PyTorch | 2.11.0 + cpu | `torch.cuda.is_available() == False` (CPU-only wheel installed locally — does not affect adapter detection) |
| Python | 3.14.3 | |
| Node.js | v25.8.2 | required for Playwright (Layer D) |
| Git | 2.54.0.windows.1 | |
| Bash | GNU bash 5.3.9 (msys2) at `/usr/bin/bash` | |
| PowerShell | 7.6.1 at `C:\Program Files\PowerShell\7\pwsh.exe` | |
| cmd | `C:\Windows\system32\cmd.exe` | |

**Verdict:** This host IS a viable Desktop GPU Worker reference. RTX 3090 Ti + 128 GB RAM + Ryzen 7 5800X3D meets the kit's reference profile. The tooling chain (Python 3.14, Node 25, Git, three shells) is sufficient for both Phase 0 audit work and Phase 1 detection-script development.

## 3. Detection cascade (per kit)

[`GPU_DETECTION_SKELETON.md`](../hermes3d_gui_contract_kit_v4.1/03_implementation/dual_edition/GPU_DETECTION_SKELETON.md) prescribes the order:

1. **`nvidia-smi`** — authoritative for VRAM, driver version, and live free-VRAM. Always tried first.
2. **`torch.cuda`** — only as a CUDA-runtime check; do NOT use `torch` for VRAM (CPU-only wheels lie).
3. **WMI `Win32_VideoController`** — name + presence fallback only. **Do NOT trust `AdapterRAM`** — it's a 32-bit DWORD and saturates at ~4 GB even on a 24 GB card (confirmed on this host).
4. **`safe-unavailable`** — final state. System stays usable; status is `blocked_no_gpu` with operator-readable reason.

[`GPU_DETECTION_IMPLEMENTATION.md`](../hermes3d_gui_contract_kit_v4.1/03_implementation/dual_edition/GPU_DETECTION_IMPLEMENTATION.md) defines the output schema fields: `worker_id`, vendor, GPU name, total VRAM, free VRAM (when available), CUDA availability, driver version, tool capabilities.

## 4. Edition resolution rule

The kit's specs assume but never explicitly state how an installation knows which edition it is. The canonical resolution (to be codified by the Phase 1 detection script):

```
if platform == "Windows" and detect_gpu().vendor == "NVIDIA":
    edition = "desktop_gpu_worker"
elif platform == "Linux" and not detect_gpu().has_cuda:
    edition = "ubuntu_vps_control_server"
elif platform == "Linux" and detect_gpu().has_cuda:
    edition = "desktop_gpu_worker"   # Linux GPU box — supported, secondary
else:
    edition = "blocked_no_gpu"       # Mac / Windows without NVIDIA / etc.
```

This rule is a Phase 1 ADR, not a Phase 0 deliverable. The text above is a recommendation for the ADR author — Phase 1 may refine it.

## 5. Worker auth + transport (per [`TUNNEL_AND_REMOTE_ACCESS.md`](../hermes3d_gui_contract_kit_v4.1/01_requirements/TUNNEL_AND_REMOTE_ACCESS.md))

| Property | Spec |
|---|---|
| Tunnel modes | Tailscale preferred · Cloudflare Tunnel optional · WireGuard advanced |
| Auth direction | VPS reaches worker `/health`; worker authenticates VPS |
| Failure mode | Tunnels fail closed |
| Public exposure | Worker NEVER public; printer LAN endpoints NEVER public |
| Job channels | `control`, `event`, `artifact`, `health` |

**Gap (HIGH severity, deferred to Phase 1):** the specific worker-auth scheme (mutual TLS / API key / signed JWT / WireGuard pre-shared key + ACL) is named only as a property ("worker authenticates VPS") and not as a chosen mechanism. Phase 1's first security ADR closes this. See `05_truth_proof/PHASE0_PROOF_BASELINE.md` "Phase 1 prerequisites" for the full Phase 1 ADR list.

## 6. Worker registry protocol (per [`WORKER_REGISTRY_PROTOCOL.md`](../hermes3d_gui_contract_kit_v4.1/02_architecture/WORKER_REGISTRY_PROTOCOL.md))

Workers register with: `worker_id`, signed token, capability manifest, tool versions, GPU report, tunnel URL.

State machine:
```
offline → connecting → online → busy → degraded → blocked → updating → error
```

Heartbeat: 10 s. `> 30 s` no heartbeat → `degraded`. `> 60 s` → `offline`.

This state model is consistent with the adapter lifecycle states defined in `03_implementation/adapter_registry/README.md` §3 (worker-level vs adapter-level — distinct planes, both use compatible vocabulary).

## 7. Worker API contract (per [`WORKER_API_CONTRACT.md`](../hermes3d_gui_contract_kit_v4.1/03_implementation/dual_edition/WORKER_API_CONTRACT.md))

Endpoints:
- `/health`, `/capabilities`, `/gpu`, `/tools`
- `/jobs` (POST submit), `/jobs/{job_id}` (GET status), `/jobs/{job_id}/cancel`
- `/artifacts/{artifact_id}`

Allowed job classes (per [`JOB_ROUTER_CONTRACT.md`](../hermes3d_gui_contract_kit_v4.1/03_implementation/dual_edition/JOB_ROUTER_CONTRACT.md)):
- `vision_analysis`, `image_to_3d`, `blender_cleanup`, `mesh_validation`, `slicing`, `printer_control_readonly`, `printer_control_write`, `proof_bundle_build`

Forbidden: raw shell command jobs · arbitrary Python from VPS · printer heating/movement when write-control gate is disabled.

## 8. Findings

| # | Severity | Finding |
|---|---|---|
| 1 | **HIGH** | No `scripts/env-detect.py` (or equivalent) exists in the repo today. Adapters and the router cannot trust an "edition = Desktop vs VPS" claim until Phase 1 produces this script. |
| 2 | **HIGH** | Worker auth scheme is unspecified beyond "worker authenticates VPS". Required as Phase 1 ADR. |
| 3 | MED | No `schemas/env_report.schema.json` defining the env-detect output. UI / router / registry will all consume this — needs a single source. |
| 4 | MED | `tests/fixtures/gpu_detection/` does not exist. The 4 scenarios named in `GPU_DETECTION_SKELETON.md` (nvidia-smi+3090Ti, nvidia-smi+no-GPU, no-nvidia-smi, no-GPU-at-all) need fixture JSONs for offline tests. |
| 5 | MED | Edition resolution rule is implicit. Phase 1 ADR should make it explicit (recommendation in §4). |
| 6 | LOW | Local PyTorch is CPU-only; this is a per-host install issue, not a contract issue. Detection cascade explicitly does not depend on `torch.cuda`. |
| 7 | LOW | WMI `AdapterRAM` 32-bit ceiling is documented in this baseline so future implementers don't repeat the mistake. |
| 8 | INFO | Reference host (this Windows machine) confirmed as a viable Desktop GPU Worker per kit profile. |

## 9. Phase 1 deliverables (environment axis)

Listed here for the Phase 1 implementer; cross-referenced in `00_overview/PHASE0_BASELINE_REPORT.md`.

1. **`scripts/env-detect.py`** — emits `env_report.json` matching the schema; runs the kit's prescribed cascade; falls back gracefully through every level.
2. **`schemas/env_report.schema.json`** — JSON Schema for the env report; consumed by the registry validator, the worker registration call, and the UI.
3. **Test fixtures** under `tests/fixtures/gpu_detection/` for the four scenarios; offline detector tests use these.
4. **ADR-006 "Edition Resolution Rule"** — explicit rule for `desktop_gpu_worker` vs `ubuntu_vps_control_server` vs `blocked_no_gpu`.
5. **ADR-007 "Worker Authentication Scheme"** — the chosen mechanism (likely Tailscale ACL + per-worker API key) with rotation policy.
6. **`02_architecture/AUDIT_LOG_SCHEMA.md`** — log schema for "signed/logged worker actions" (kit calls them out but doesn't define).

## 10. rc1 non-disturbance

This document is informational and reference-only. It does not modify:
- `release/v5.3.0-rc1` branch or the `v5.3.0-rc1` tag (frozen)
- any source code under `03_implementation/src/hermes3d/`
- any kit doc

It changes only this file and a sibling reference under `00_overview/`, `01_requirements/`, `03_implementation/adapter_registry/`, and `05_truth_proof/`.

---

**Phase 1 readiness for the environment axis: GO** — kit intent is implementable on the canonical reference host; first Phase 1 deliverables are an env-detect script + schema + fixtures + the two ADRs above.
