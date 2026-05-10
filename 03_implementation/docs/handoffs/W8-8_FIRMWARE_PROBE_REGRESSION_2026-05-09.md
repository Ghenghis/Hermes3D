# W8-8 — Firmware Source Inventory Probe Regression (2026-05-09)

## Status

- Lock owner: `claude-w8-8-firmware-probe`
- Branch: `claude/w8-8-firmware-probe-regression`
- Base: `feat/hermes3d-7-complete-gui-repo-wiring`
- Failing tests fixed: 5/5
- New regression-pin: 1 (`test_firmware_probe_returns_ready_when_files_exist_and_verifier_index_empty`)
- Adjacent regressions introduced: 0

## TL;DR

W7-3 truth-check flagged 5 parametrized
`test_firmware_source_inventory_is_reference_only_not_executable` failures and
hypothesised an interaction between PR #150 (broad-except cleanup) and PR #120
(firmware source inventory probe). On read, **PR #150 is innocent**: its only
edit to `module_runtime.py` was adding observability to `_private_runtime_env`
(`module_runtime.py:2241-2255`), which is unrelated to the firmware probe path.
The actual regression was caused by PR #120 alone, in two places:

1. **`kind` change:** PR #120 set every firmware row in
   `BUILTIN_RUNTIME_PROBES` from `kind="source_inventory"` to
   `kind="firmware_source_inventory"`. `_safe_runtime_probe` does NOT have a
   dispatch branch for `firmware_source_inventory`, so the row falls through to
   the default executable-path branch and returns `status="blocked"`.

2. **`path` change:** PR #120 also set each firmware row's `path` from `""`
   (empty — falls back to `mod.local_path`) to a hardcoded absolute string
   like `G:/Github/Hermes3D-OS/source-lab/sources/firmware/Marlin`. This
   bypassed the `mod.local_path` fallback in `_source_inventory_probe`
   (`module_runtime.py:1597-1598`), so the test's `tmp_path` setup was
   ignored — the probe pointed at the dev machine's filesystem, which is
   absent in CI.

W7-3's broad-except hypothesis is incorrect for this regression. Documented
here so future audits do not re-blame PR #150.

## Original PR line ranges

- **PR #150 (`ba4194d`)** — `chore(observability): expose 7 silent broad-except
  fallbacks (Wave Agent 7)`. The only `module_runtime.py` change was at
  `_private_runtime_env` (line 2241). Six other files touched. **Not the
  cause.**
- **PR #120 (`144d0c5`)** — `feat(I7): firmware source inventory probes —
  read-only git describe, source_reference_only contract`. Changed firmware
  rows in `BUILTIN_RUNTIME_PROBES`:
  - `kind: "source_inventory"` -> `"firmware_source_inventory"` (lines 638-707
    on the post-#120 file).
  - `path: ""` -> hardcoded absolute paths (same lines).
  - Added `_git_describe`, `probe_firmware_source_inventory`,
    `probe_all_firmware_sources`, `FIRMWARE_SOURCE_PATHS`,
    `FIRMWARE_RUNNER_CONTRACT_TEMPLATE` (lines 3686-3773 post-fix).
  - **Cause of the regression** is the kind+path change, not the new
    function — the new function is only called by direct tests via
    `probe_firmware_source_inventory()`, never via
    `module_runtime_probe -> _safe_runtime_probe -> _source_inventory_probe`.

## Exact interaction

The test `test_firmware_source_inventory_is_reference_only_not_executable`
(parametrized 5 ways at `test_source_runtime_contracts.py:245-304`):

```python
monkeypatch.setattr(module_runtime, "_runtime_verifier_index", lambda: (False, {}))
for relative in required_files:
    target = tmp_path / relative
    ...  # write README.md, mkdir docs/, etc.
runtime = module_runtime.module_runtime_probe({
    "id": "marlin",
    ...
    "local_path": str(tmp_path),
})
assert runtime["status"] == "ready"
assert runtime["kind"] == "source_inventory"
```

Trace through the code at `module_runtime.py`:

1. `module_runtime_probe(mod)` (line 798) calls
   `runtime_probe_config("marlin")`.
2. `runtime_probe_config` (line 1490) sees
   `_runtime_verifier_index() == (False, {})` and returns
   `BUILTIN_RUNTIME_PROBES["marlin"]`.
3. `_safe_runtime_probe(probe, mod, live=False)` (line 1498) inspects
   `probe.get("kind")`.
4. **Pre-#120**: `kind == "source_inventory"` -> dispatch to
   `_source_inventory_probe(probe, mod)`. Inside,
   `path_value = probe.get("path") or mod.get("local_path") or ""` -> with
   `probe["path"]==""`, falls back to `tmp_path`. Files exist -> `ready`.
5. **Post-#120 (regression)**: `kind == "firmware_source_inventory"`. None of
   the `if probe.get("kind") == ...` branches match. Falls through to default
   executable-path block at `module_runtime.py:1515-1594`. Sets
   `path = Path(probe["path"])` (hardcoded), `path.is_file()` is False
   (it's a directory, and may not exist in CI), `audit` is empty -> status
   resolves to `"blocked"`. Test fails.

## Fix rationale

Two surgical edits to `BUILTIN_RUNTIME_PROBES` for the 6 firmware module rows
at `03_implementation/src/hermes3d/services/module_runtime.py:637-708`:

1. Restored `kind: "source_inventory"` (was `"firmware_source_inventory"`).
2. Restored `path: ""` (was hardcoded absolute path).

Why this is the right fix (not a dispatcher patch):

- The `_safe_runtime_probe` dispatcher already handles every kind it knows
  about. Adding a new `firmware_source_inventory` branch would either:
  (a) re-export `_source_inventory_probe`, in which case the kind name change
  buys no behavioural difference but loses the existing
  `_runner_status` mapping (line 2555) that requires
  `verifier_kind == "source_inventory"`, OR
  (b) require parallel changes in `_runner_status`, `_required_verifier_family`,
  `_runner_blocked_reason`, and any other callers reading `runtime["kind"]`.
  That balloons scope well past 30 LoC.
- The firmware-specific provenance the team wanted is **already** carried by
  `tool_key="firmware_source_inventory"` (decorative; for audit grouping) and
  `proof_gate_version="firmware-source-inventory-v1"` (the truth-gate marker).
- The hardcoded `path` field on BUILTIN entries was redundant: the new
  `probe_firmware_source_inventory()` function (added in PR #120, untouched
  here) reads `FIRMWARE_SOURCE_PATHS` directly — that registry remains intact.
- `notes` text now says `Source path (canonical): ...` to preserve the
  documentation value of the absolute path without re-introducing the
  dispatch break.

LoC delta: 12 path/kind value lines edited + 24 lines of inline `# NOTE
(W8-8 ...)` comments documenting why they must stay this way + 56 lines of
new pinning test = 92 LoC total. Behavior change confined to firmware
`BUILTIN_RUNTIME_PROBES` rows — no dispatcher, no other module rows, no API
changes.

## Verification

```
$ python -m pytest 04_testing/pytest/unit/test_source_runtime_contracts.py \
    -k test_firmware_source_inventory --tb=short
...
5 passed, 37 deselected in 1.69s

$ python -m pytest 04_testing/pytest/unit/test_source_runtime_contracts.py \
    04_testing/pytest/unit/test_module_runtime.py \
    04_testing/pytest/unit/test_firmware_farm_probes.py
...
166 passed in 3.01s
```

## Sources

1. **PEP 8 — Style Guide for Python Code, "Programming Recommendations" /
   exception clauses**: `https://peps.python.org/pep-0008/#programming-recommendations`
   — "When catching exceptions, mention specific exceptions whenever possible
   instead of using a bare `except:` clause." Confirms the broad-except
   tightening direction in PR #150 was correct in principle, even though it
   had no causal role in this regression.
2. **PR #150 issue/PR description text** (commit `ba4194d` body, also pasted
   here for posterity):
   `chore(observability): expose 7 silent broad-except fallbacks (Wave Agent 7)`.
   Explicitly scoped: `Sites … services/module_runtime.py:_private_runtime_env
   — warning, runs through redact_text … Scope: Observability only. Zero
   behavior change. No new dependencies.` Confirms PR #150 did not touch
   `_safe_runtime_probe` or `_source_inventory_probe`. The W7-3 hypothesis
   should not have implicated PR #150.

## Files changed

- `03_implementation/src/hermes3d/services/module_runtime.py`
  (6 firmware probe rows updated; ~36 LoC including comments)
- `04_testing/pytest/unit/test_source_runtime_contracts.py`
  (1 regression-pin test added; ~56 LoC)
- `03_implementation/docs/handoffs/W8-8_FIRMWARE_PROBE_REGRESSION_2026-05-09.md`
  (this file)

## Constraint compliance

- No secrets touched.
- Hermes MCP locks acquired/released via `claude-w8-8-firmware-probe`.
- 2 sources cited (PEP 8 + PR #150 description).
- All 5 previously-failing tests pass.
- PR #150's broad-except cleanup is intact (not reverted).
- Firmware probe is not rewritten — only the BUILTIN_RUNTIME_PROBES data is
  reverted to its pre-#120 shape for `kind` and `path`. The new
  `probe_firmware_source_inventory()` function and `FIRMWARE_SOURCE_PATHS`
  registry are unchanged.
