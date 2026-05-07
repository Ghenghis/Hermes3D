# Security & MCP Proof Audit
**Task**: H3D-CLAUDE-POLISH-AGENT-MCP-PROOF-2026-05-06
**Agent**: claude-polish-security-05
**Date**: 2026-05-06
**Hermes lock**: `03_implementation/docs/handoffs/audit/SECURITY_MCP_2026-05-06.md` (lock_id: e75ff13fa545f33015830632)

---

## Secret Scan Results

**Scan scope**: All 12 UI lane worktrees (`h3d-claude-voice`, `h3d-claude-observe`, `h3d-claude-printers`, `h3d-claude-design`, `h3d-claude-gen3d`, `h3d-claude-jobs`, `h3d-claude-learning-autopilot`, `h3d-claude-source-ui`, `h3d-claude-settings-plugins`, `h3d-claude-artifacts-proof`, `h3d-claude-app-shell`, `h3d-claude-security-mcp`)

**Patterns scanned**: `api_key=`, `apiKey=`, `API_KEY=`, `secret=<literal>`, `SECRET=`, `password=<literal>`, `PASSWORD=`, `token.*=.*[a-zA-Z0-9]{20+}`, `Bearer [token]`, `sk-[key]`, `AZURE.*KEY`, `OPENAI_API_KEY`, `private/.env`

**Result**: PASS — zero real secrets

All 24 matches on `AZURE.*KEY` pattern are **false positives**: they are JSX comment text or UI tooltip strings inside `Voice.tsx` that explicitly document that the key is *never* sent to the frontend:

```
Voice.tsx:328  "Catalog rows come from Azure Speech through the Python backend. The frontend never receives the Speech key."
Voice.tsx:370  "<div>Set `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` in `G:\\private\\.env` to load the live Azure catalog.</div>"
```

These strings are documentation/UI guidance text instructing the user to place secrets in `G:\private\.env` (the project convention). No literal secret values are present. No `api_key=`, `apiKey=`, `sk-`, `Bearer [token]`, or `OPENAI_API_KEY` matches were found in any `.ts`, `.tsx`, or `.js` file.

**Verdict**: SECRET SCAN CLEAN

---

## Path Traversal Check (artifacts.py)

**File**: `03_implementation/src/hermes3d/api/routes/artifacts.py`

**Route audited**: `GET /api/artifacts/proof/{filename:path}`

**Finding**: PASS — path traversal is correctly blocked.

The route resolves the user-supplied `filename` against the locked `_PROOF_DIR` using `Path.resolve()` and then calls `target.relative_to(_PROOF_DIR.resolve())`, which raises `ValueError` (caught → HTTP 400) if the resolved path escapes the proof directory:

```python
# Prevent path traversal
target = (_PROOF_DIR / filename).resolve()
try:
    target.relative_to(_PROOF_DIR.resolve())
except ValueError:
    raise HTTPException(status_code=400, detail="invalid proof file path")
```

This is the correct canonical defence (`realpath`/`resolve` + `relative_to`). Sequences such as `../../../etc/passwd` resolve outside `_PROOF_DIR` and are rejected with HTTP 400 before any filesystem read.

**Secondary route**: `GET /api/artifacts/{artifact_id}/download`

This route looks up `file_path` from the database by `artifact_id` (UUID), not from user-supplied path. The `file_path` value is written at upload time as `storage / f"{artifact_id}_artifact.bin"` — a server-controlled path constructed from a generated UUID. No user input reaches the `file_path` column, so there is no traversal risk on this route.

**Verdict**: PATH TRAVERSAL PROTECTED

---

## Shell Execution Audit

**Scope**: All 26 `hermes3d/api/routes/` directories across all worktrees.

**Patterns**: `subprocess.call`, `os.system`, `shell=True`, `subprocess.Popen.*shell=True`, `eval(request`, `__import__` (user-controlled)

**Findings requiring analysis**: Two patterns flagged in every worktree copy of two files.

### approvals.py:21 — `__import__("json")`

```python
(__import__("json").dumps(statuses),),
```

This is a **false positive**. `__import__("json")` is a Python idiom for inline import of the stdlib `json` module. The argument `"json"` is a **hardcoded string literal**; it is not derived from any user input. The resulting call is `json.dumps(statuses)` — safe JSON serialisation. Not a shell execution risk.

### system.py:454 — `_python_importable(module_name)`

```python
def _python_importable(module_name: str) -> bool:
    try:
        __import__(module_name)
        return True
    except Exception:
        return False
```

This function is called in exactly **one place** across the entire codebase:

```python
design_ready = _python_importable("trimesh")
```

The argument `"trimesh"` is a **hardcoded string literal** — not derived from any request parameter, route path, or body. It is a capability probe to check whether the `trimesh` library is installed. Not a shell execution or user-controlled import risk.

**No `subprocess.call`, `os.system`, `shell=True`, or `subprocess.Popen` with `shell=True` found in any route file.**

**Verdict**: SHELL EXECUTION AUDIT CLEAN — zero dangerous patterns with user-controlled input

---

## .env Commit Check

**Git log scan** (all branches, `--diff-filter=A`): No `.env`, `.env.txt`, `secrets*`, or `credentials*` files have ever been committed to the `h3d-gui-wiring-codex` repository.

**Worktree filesystem scan**: No `.env` or `.env.txt` files found anywhere under `G:/Github/_claude_worktrees/` (excluding `node_modules`).

**`.gitignore` coverage**: The root `.gitignore` explicitly excludes:
```
.env
.env.local
.env.*.local
```
(with `!env/.env.example` allowed for the example template only)

This aligns with the project secret-storage convention (`G:\private\.env`).

**Verdict**: .ENV COMMIT CHECK CLEAN

---

## Security-MCP PR Work (claude/security-mcp branch)

The security-mcp lane commit `fba16bc` added 8 files:

| File | Purpose |
|------|---------|
| `tests/security/test_path_traversal.py` | Asserts `_resolve_project_path` / `_resolve_project_subpath` reject `..`, absolute roots, UNC paths, null bytes, empty paths |
| `tests/security/test_secret_redaction.py` | AST scan of `local_state.py` / `module_runtime.py` for raw-secret literals in log calls; asserts `SECRET_RE` + `_redact_text` present |
| `tests/security/test_prompt_injection.py` | 20+ OWASP LLM-01 vectors (`Ignore previous instructions`, jailbreak personas, base64 payloads, hidden unicode) — each asserts `severity != "clean"` |
| `tests/security/test_mcp_boundary.py` | Pins printer build-plate gate, S1 read-only lock, agent runtime URL loopback restriction, InjectionScanner ruleset presence |
| `tests/security/conftest.py` | Shared test fixtures |
| `tests/security/__init__.py` | Package marker |
| `docs/security/MCP_BOUNDARY_NOTES.md` | Explains the MCP boundary contract |
| `proof/security/SECURITY_AUDIT_2026-05-06.json` | Machine-readable proof bundle |

**Quality verdict**: Tests are real. They use `importlib`, `inspect.getsource`, AST parsing, and live scanner instantiation. No `assert True` placeholders found.

---

## Hermes Evidence Chain Status

`hermes_list_events` returned 252 events. The chain begins at `evt_20260503T170425751Z_b76a8c` (2026-05-03 smoke test) and includes `lock.acquired`, `lock.released`, `task.*`, and `evidence.*` events from all lanes.

The chain is structurally intact: each event carries `event_schema_version: 1`, `event_id`, `created_utc`, `workspace_root`, and `owner`. The current session lock (`e75ff13fa545f33015830632`) was acquired successfully, confirming the MCP server is reachable and accepting writes.

**Verdict**: HERMES EVIDENCE CHAIN INTACT

---

## BLOCKERS (security violations)

**None.**

All flagged patterns on the secret scan were documentation strings.
All flagged `__import__` usages had hardcoded literal arguments.
No `shell=True`, `os.system`, or `subprocess.call` found in any route.
No `.env` files committed to git.
Path traversal is correctly guarded in `artifacts.py`.

---

## PASS (security verified)

| Check | Result |
|-------|--------|
| Secret scan — all 12 UI lane worktrees | PASS (zero real secrets) |
| AZURE_KEY pattern hits | PASS (UI tooltip text only; keys stay server-side) |
| Path traversal — `GET /api/artifacts/proof/{filename}` | PASS (`resolve()` + `relative_to()` guard present) |
| Path traversal — `GET /api/artifacts/{id}/download` | PASS (DB path is server-generated UUID, not user input) |
| Shell execution — all route dirs | PASS (zero `shell=True`, zero user-controlled `__import__`) |
| `__import__("json")` in approvals.py | PASS (hardcoded stdlib import, not user-controlled) |
| `_python_importable("trimesh")` in system.py | PASS (hardcoded literal, capability probe only) |
| `.env` commit history | PASS (no secrets ever committed) |
| `.gitignore` coverage | PASS (`.env` patterns covered) |
| Security-mcp PR tests quality | PASS (real behavioural tests, no assert-True stubs) |
| Hermes MCP reachability | PASS (`hermes_doctor` ok: true) |
| Hermes evidence chain | PASS (252 events, chain intact, lock acquired) |

**Overall audit result: SECURITY VERIFIED — no blockers**
