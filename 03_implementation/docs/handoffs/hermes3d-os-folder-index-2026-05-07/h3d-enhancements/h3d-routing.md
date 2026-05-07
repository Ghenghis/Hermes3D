# h3d-routing

- **Type**: ENHANCEMENT (LLM ROUTING)
- **Status**: OPEN — branch ahead of develop, no PR opened yet
- **Branch**: `feat/cp-h3d-routing-mode`
- **Last commit**: `76e922d feat(llm): provider-registry routing-mode loader + ADR-017`
- **PR link**: none
- **Repo**: `https://github.com/Ghenghis/Hermes3D`

## Goal

Introduce a YAML-driven LLM provider registry plus a routing-mode loader, so Hermes3D can pick between local LM Studio models and the Continue-LLM class catalog under a single declarative policy. Adds ADR-017 to lock in the design decision and a 223-line pytest suite to keep the loader honest.

## Files changed (vs `origin/develop`)

| File | + / - |
| --- | --- |
| `00_overview/adr/ADR-017-provider-registry-and-routing.md` | +143 |
| `02_specs/policies/provider-registry/AUDIT.md` | +78 |
| `02_specs/policies/provider-registry/continue_llm_classes.csv` | +63 |
| `02_specs/policies/provider-registry/lmstudio_local_models.csv` | +88 |
| `02_specs/policies/provider-registry/registry.yaml` | +966 |
| `02_specs/policies/provider-registry/routing.yaml` | +12 |
| `03_implementation/src/hermes3d/core/llm/providers.py` | +20 / -1 |
| `03_implementation/src/hermes3d/core/llm/registry_loader.py` | +191 |
| `04_testing/pytest/test_registry_loader.py` | +223 |

Total: 9 files changed, +1784 / -1.

## Notes

- The registry file (`registry.yaml`, 966 lines) is the bulk of the change — a structured catalog of providers / model classes.
- ADR-017 documents the trade-offs between baking provider tables into code vs. driving them off YAML; this branch picks YAML.
- One-commit branch ahead of develop (76e922d). Ready to open as a PR once the audit is signed off.

## SVG diagram — change footprint

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 450 250" width="450" height="250" role="img" aria-label="h3d-routing change footprint">
  <style>
    .box { fill: #1f2937; stroke: #4b5563; stroke-width: 1; }
    .new { fill: #065f46; stroke: #10b981; }
    .mod { fill: #78350f; stroke: #f59e0b; }
    .label { fill: #f9fafb; font: 600 12px sans-serif; }
    .sub { fill: #d1d5db; font: 10.5px sans-serif; }
    .title { fill: #f9fafb; font: 700 14px sans-serif; }
  </style>
  <rect width="450" height="250" fill="#0b1220"/>
  <text class="title" x="225" y="22" text-anchor="middle">feat/cp-h3d-routing-mode — provider-registry layout</text>

  <rect class="box new" x="20" y="45" width="200" height="80" rx="6"/>
  <text class="label" x="30" y="65">02_specs/policies/provider-registry/</text>
  <text class="sub"   x="30" y="83">registry.yaml (+966)</text>
  <text class="sub"   x="30" y="98">routing.yaml (+12) · AUDIT.md (+78)</text>
  <text class="sub"   x="30" y="113">2 CSV catalogs (+63 / +88)</text>

  <rect class="box new" x="240" y="45" width="190" height="80" rx="6"/>
  <text class="label" x="250" y="65">core/llm/</text>
  <text class="sub"   x="250" y="83">registry_loader.py (+191) · NEW</text>
  <text class="sub"   x="250" y="98">providers.py  +20 / -1 — wires loader</text>
  <text class="sub"   x="250" y="113">tests +223 — test_registry_loader.py</text>

  <rect class="box new" x="20" y="140" width="200" height="60" rx="6"/>
  <text class="label" x="30" y="162">ADR-017</text>
  <text class="sub"   x="30" y="180">+143 — registry &amp; routing decision</text>

  <rect class="box mod" x="240" y="140" width="190" height="60" rx="6"/>
  <text class="label" x="250" y="162">runtime entry-point</text>
  <text class="sub"   x="250" y="180">providers.py reads YAML at boot</text>

  <text class="sub" x="225" y="225" text-anchor="middle" fill="#9ca3af">9 files · +1784 / -1 · branch ahead, no PR yet</text>
</svg>
```
