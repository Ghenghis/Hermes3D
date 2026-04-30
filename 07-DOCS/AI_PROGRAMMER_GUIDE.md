# AI PROGRAMMER GUIDE — Hermes3D-OS Lite

> Read this when you're going to add code to the kit. It is written
> for both humans and AI assistants. The contract
> (`00-CONTRACT/MASTER_CONTRACT.md`) is the law; this file is the
> field manual.

---

## 1. The contract in 60 seconds

Every change you make must, at minimum:

1. Build cleanly from a fresh clone (`scripts/doctor` then
   `scripts/test`).
2. Pass the forbidden-pattern scan (no TODO/FIXME/STUB/PLACEHOLDER, no
   bare `except: pass`, no naked `raise NotImplementedError` outside
   spec-tier code).
3. Be backed by at least one real test (no mock-only proof).
4. Update the relevant doc (this file, the architecture, the
   honesty ledger).
5. Pass the honesty-diff: any new file's tier classification must
   match its actual state.

If you can't satisfy any of these, don't merge. Open an issue
documenting exactly what's missing and why.

---

## 2. Setup for development

```bash
git clone <kit>
cd hermes3d-os-v5-contract-kit/02-SCAFFOLDING
python3.11 -m venv .venv
source .venv/bin/activate          # or .venv\Scripts\Activate.ps1
pip install -e .
pip install -r requirements-dev.txt
bash scripts/doctor.sh
pytest tests/ -v
```

If `pytest` is green at this point, you're set up correctly. If it
isn't, that's bug zero — fix it first.

---

## 3. The shape of a change

A typical contributor commit touches all five of these areas:

```
src/hermes3d/<layer>/<module>.py        # the code
tests/unit/test_<module>.py             # at least one real test
00-CONTRACT/HONESTY_LEDGER.md           # claim what you built
00-CONTRACT/FEATURES.md                 # if user-visible
07-DOCS/<relevant>.md                   # if architecture-relevant
```

If the change adds a tool, also update:

```
src/hermes3d/core/agents/tool_registrations.py  # register the tool
tests/unit/test_tool_registrations.py            # cover it
```

---

## 4. Implementing a new printer profile

1. Edit `config/printers.toml` — add a `[printers.<id>]` block.
2. The TOML loader will pick it up automatically — no code change.
3. Add a Klipper config skeleton at
   `config/klipper/<id>.printer.cfg`. Copy from a similar printer.
4. Run `pytest tests/unit/test_printer_profiles.py -v`. The fleet
   count assertion will tell you if you forgot anything.
5. Update `07-DOCS/PRINTER_FLEET_GUIDE.md` to add the new printer to
   the table.
6. (Optional) Build a printer-specific skill pack under
   `config/skill_packs/`.

---

## 5. Implementing a new dispatcher strategy

The dispatcher lives in `core.agents.dispatcher`. Strategies are
declared in the `DispatchStrategy` enum and implemented in a single
match-case block in `_score_printer`.

To add `BALANCED_LOAD`:

```python
# 1. Add to the enum
class DispatchStrategy(str, Enum):
    ...
    BALANCED_LOAD = "balanced_load"

# 2. Implement the scoring contribution
def _score_balanced_load(printer, live_state, ...):
    # Lower score for printers that printed in the last hour;
    # higher score for cold ones. Returns a float in [0, 1].
    ...

# 3. Add a match arm in _score_printer
case DispatchStrategy.BALANCED_LOAD:
    score += _score_balanced_load(printer, live_state)
```

Then add a test:

```python
def test_balanced_load_prefers_idle_printers(tmp_path):
    decision = dispatch(
        DispatchRequest(
            mesh_extents_mm=(50, 50, 50),
            material="PLA",
            strategy=DispatchStrategy.BALANCED_LOAD,
            live_state=...,
        )
    )
    assert decision.selected_printer_id == "expected_idle_printer_id"
```

---

## 6. Implementing a new tool

Tools live in `core.agents.tool_registry` (the registry mechanics) and
`core.agents.tool_registrations` (the actual tools wired to backends).

To add a tool that exposes mesh analysis to LLM agents:

```python
# In tool_registrations.py — at the bottom of register_default_tools()

def _mesh_analyse_handler(*, mesh_path: str, **_) -> dict:
    from hermes3d.core.agents.mesh_analyzer import analyze_mesh_file
    analysis = analyze_mesh_file(mesh_path)
    return {
        "ok": True,
        "bbox_mm": list(analysis.bbox_mm),
        "is_watertight": analysis.is_watertight,
        "risk_flags": analysis.risk_flags,
    }

reg.register(ToolSpec(
    name="mesh_analyse",
    description="Analyse a mesh file for printability risks.",
    category="domain",
    tags=("mesh", "preflight"),
    schema={
        "type": "object",
        "required": ["mesh_path"],
        "properties": {
            "mesh_path": {"type": "string", "description": "Absolute path to STL/3MF/OBJ"},
        },
    },
    handler=_mesh_analyse_handler,
))
```

Then add a test in `tests/unit/test_tool_registrations.py`:

```python
def test_mesh_analyse_tool(tmp_path: Path) -> None:
    stl = tmp_path / "cube.stl"
    _write_minimal_stl(stl)
    reg = ToolRegistry()
    register_default_tools(reg)
    out = reg.call("mesh_analyse", mesh_path=str(stl))
    assert out["ok"]
    assert out["bbox_mm"] == [10.0, 10.0, 10.0]
```

---

## 7. Implementing the orchestrator (LangGraph)

`core.agents.orchestrator.LangGraphOrchestrator` is **spec-only** in
v5. To replace the placeholder with a real implementation:

1. `pip install langgraph langchain-core`.
2. In `orchestrator.py`, remove the `# noqa: forbidden_pattern_scan`
   raise. Replace `LangGraphOrchestrator.run` with a real
   StateGraph that wires every node in `print_workflow.NODE_ORDER`.
3. Wire each node to call the corresponding executor in
   `core.orchestration.print_workflow`.
4. Persist checkpoints via the existing `var/workflow/<job_id>/`
   structure.
5. Add an integration test under `tests/integration/test_langgraph_orchestrator.py`
   that runs the full 12-node graph against a fixture STL.
6. Update `00-CONTRACT/HONESTY_LEDGER.md` — promote
   `core.agents.orchestrator` from spec to runnable.
7. Update `07-DOCS/CHANGELOG.md` under v5.x → "LangGraph runtime
   adapter promoted from spec to runnable."

The drop-in linear executor (`DryRunOrchestrator`) is what every
existing test relies on. Don't remove it; LangGraph and the linear
executor coexist.

---

## 8. Writing a skill pack

A skill pack is a JSON bundle with a manifest, a list of skills, and
an HMAC-SHA256 signature. The format:

```json
{
  "pack_id": "your_pack_v1",
  "name": "Your Pack Name",
  "version": "1.0.0",
  "author": "you",
  "created_at": "2026-04-29T00:00:00Z",
  "scope_summary": "PLA on FLSUN T1",
  "skills": [
    {
      "skill_kind": "parameter_override",
      "name": "PA value for PLA on T1",
      "scope": {"printer_id": "flsun_t1_a", "material": "PLA"},
      "body": {"pressure_advance": 0.045},
      "confidence": 0.85,
      "source": "calibrated 2026-04-15",
      "notes": "..."
    }
  ],
  "signature": {"algorithm": "HMAC-SHA256", "value": "..."}
}
```

Generate the signature with `hermes3d skill pack-sign <file>`. Import
with `hermes3d skill import <file>`.

Skill packs that ship with the kit live in
`config/skill_packs/`. Each must be HMAC-signed and reproducibly
generatable from a small Python script in the same directory.

---

## 9. Adding a REST endpoint

REST lives in `api.server`. To add `GET /v1/quality/score`:

```python
# In api/server.py
@app.get("/v1/quality/score")
def quality_score(printer_id: str, material: str) -> dict:
    from hermes3d.core.agents.quality_scorer import score_printer_for
    return score_printer_for(printer_id=printer_id, material=material).to_dict()
```

Add the endpoint to:

- `tests/conformance/test_rest_contract.py` — schema check
- `07-DOCS/ARCHITECTURE.md` §7 — endpoint count

---

## 10. Naming conventions

| Thing | Pattern |
|-------|---------|
| Module | `snake_case` |
| Class | `PascalCase` |
| Function / method | `snake_case` |
| Constant | `UPPER_SNAKE_CASE` |
| Test file | `test_<module>.py` |
| Test function | `test_<behaviour>` |
| Type alias | `PascalCase` |
| Enum value | `UPPER_SNAKE_CASE` |
| Env var | `HERMES3D_<UPPER_SNAKE_CASE>` |
| Path component | `kebab-case` for top-level dirs (`02-SCAFFOLDING/`), `snake_case` for code |

---

## 11. The forbidden-pattern scan, in detail

`scripts/forbidden_pattern_scan.py` rejects:

- The literal strings `TODO`, `FIXME`, `STUB`, `PLACEHOLDER`,
  `NOT_IMPLEMENTED` (case-insensitive) anywhere in `src/hermes3d/`.
- `raise NotImplementedError(...)` outside `@abstractmethod` blocks
  unless the line carries `# noqa: forbidden_pattern_scan`.
- `except: pass` empty handlers.

To opt out a line legitimately, append `# noqa: forbidden_pattern_scan`
on the same line *and* document why in `00-CONTRACT/HONESTY_LEDGER.md`
under the relevant tier section.

The current opt-outs (as of v5.0):

- `core.modeling.blender_mcp_server.py` — Blender bpy not installed.
- `core.agents.orchestrator.py` — LangGraph runtime not installed.

These are the only acceptable forms of opt-out. Do not introduce more
without contract-level review.

---

## 12. The honesty ledger, in detail

`00-CONTRACT/HONESTY_LEDGER.md` is the canonical tier classifier for
every module. It has three sections:

- **Runnable** — has tests, fully implemented, no surprises.
- **Scaffold** — implementation exists but isn't covered by tests, or
  some edge case isn't handled. Promotion to runnable in v5.1.
- **Spec** — interface only; raises `NotImplementedError` with a
  remediation message. Activation requires external setup.

`scripts/honesty_diff.py` checks the ledger against
`00-CONTRACT/KIT_MANIFEST.json`. Any disagreement is drift and must be
resolved before merging.

When you change a module's behaviour:

1. Decide its honest tier.
2. Update the ledger.
3. Run `python 00-CONTRACT/_generate_manifest.py`.
4. Run `python scripts/honesty_diff.py` — it must report zero drift.

---

## 13. Releases

`scripts/release.{sh,ps1}` produces:

- `dist/release/<version>/hermes3d_os_lite_v<version>.zip`
- A SHA-256 sidecar
- A signed proof envelope (HMAC-SHA256, key from `HERMES3D_PROOF_KEY`)

The CI release-dry-run job verifies that the zip builds. Tagging a
commit `v5.x.y` triggers a real release (when configured by the
maintainer in CI secrets).

---

## 14. When in doubt

- **Stuck on tier:** if you can show a passing test, it's runnable. If
  the implementation works but has no test, it's scaffold. If it
  raises `NotImplementedError`, it's spec.
- **Stuck on whether a thing should be a tool, an API endpoint, or a
  CLI subcommand:** if an LLM agent should call it, it's a tool. If a
  human script should call it, it's an API endpoint. If a human
  operator should call it, it's a CLI subcommand. Most things are at
  least two of these.
- **Stuck on whether to add a dependency:** can you do it in <300
  lines of stdlib? Then don't add a dependency. The kit's "no surprise
  dependencies" stance is real.

The contract is strict. The kit is strict. The tests are strict. That
is on purpose. Strictness up front buys reliability later.
