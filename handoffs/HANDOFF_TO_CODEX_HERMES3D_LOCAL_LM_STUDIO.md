# HANDOFF_TO_CODEX — LM Studio default + Ollama fallback + Hipfire optional (Task 4a)

> **Status:** READY for Codex pickup.
>
> **Sequence position:** Task 4a in overnight queue (split from former CP-HERMES3D-LOCAL-INTELLIGENCE which failed audit).
>
> **Owner:** `codex-impl-06`.
>
> **Estimated time:** 2-3 hours.
>
> **Audit history:** parent brief failed audit on path mismatches; this split has been reality-checked against `origin/develop`.

---

## 1. Mission

Make LM Studio the default local LLM provider. The user has 80 local models / 652 GB at `C:\Users\Admin\.lmstudio\models` — Ollama is the wrong default for them.

Three additions:

1. **`lm_studio_provider.py`** (NEW) — talks to LM Studio at `http://localhost:1234/v1` (OpenAI-compatible REST). Streaming + tool-calling.
2. **Ollama fallback** — modify the existing `core/llm/ollama_client.py` (CONFIRMED EXISTS) to register as the second-priority provider in the chain.
3. **Hipfire optional** — `hipfire_provider.py` (NEW), default disabled, opt-in via `HERMES3D_AMD_NODE=1` env var.

NO UI changes. NO Mnemosyne. NO port monitor. Those are 4b and 4c.

---

## 2. Claim

```text
hermes_pick_task
  owner=codex-impl-06
  prefer_task_id=CP-HERMES3D-LOCAL-LM-STUDIO
```

Or fallback: `taskId=CP-HERMES3D-LOCAL-LM-STUDIO`, `title=LM Studio default + Ollama fallback + Hipfire optional`, `reason=User has 80 LM Studio models locally; Ollama is the wrong default. This is split 1/3 of the former mega-task LOCAL-INTELLIGENCE which failed audit.`

---

## 3. Branch

`feat/cp-hermes3d-local-lm-studio` from `develop`.

---

## 4. Lock these files (audit-verified against origin/develop)

```text
hermes_lock_files
  owner=codex-impl-06
  taskId=CP-HERMES3D-LOCAL-LM-STUDIO
  ttlMinutes=180
  files=[
    "03_implementation/config/llm_policy.yaml",
    "03_implementation/config/llm_policy.schema.json",
    "03_implementation/src/hermes3d/core/llm/lm_studio_provider.py",
    "03_implementation/src/hermes3d/core/llm/ollama_client.py",
    "03_implementation/src/hermes3d/core/llm/hipfire_provider.py",
    "03_implementation/src/hermes3d/core/llm/providers.py",
    "04_testing/pytest/integration/test_lm_studio_provider.py",
    "04_testing/pytest/integration/test_ollama_client.py",
    "04_testing/pytest/integration/test_hipfire_provider.py"
  ]
```

**Confirmed existing on develop:** `llm_policy.yaml`, `llm_policy.schema.json`, `core/llm/ollama_client.py`, `core/llm/providers.py` (or equivalent — verify before locking; if not exactly named `providers.py`, check `core/llm/__init__.py`).

**Confirmed NEW:** `lm_studio_provider.py`, `hipfire_provider.py`, the 3 test files.

**If `core/llm/providers.py` does not exist** but the chain logic lives in `core/llm/__init__.py`, swap the lock list entry to match reality. Verify before locking.

---

## 5. Implementation contract

### 5.1 `llm_policy.yaml` — MERGE not REPLACE

The audit flagged the parent brief for proposing a destructive rewrite. Instead:

- **Read the existing YAML, validate against `llm_policy.schema.json`**
- **Merge** the new provider chain entries into the existing structure
- **Preserve** all existing user-set values (cost_caps, model preferences, anything custom)
- **Only add or modify** the `default_chain` ordering and the new `hipfire` provider entry

If the existing YAML doesn't have `local_first_mode` / `cloud_fallback_mode` sections, ADD them with these defaults (keeping `cloud_fallback_mode.enabled: false` opt-in):

```yaml
local_first_mode:
  default_chain:
    - lm_studio       # primary — user has 80 models locally
    - ollama          # fallback — used when LM Studio is offline
    - hipfire         # optional AMD path; activated only if HERMES3D_AMD_NODE=1
  cost_caps:
    daily_usd: 0      # local mode: zero spend
    per_request_max_tokens: 16000

cloud_fallback_mode:
  enabled: false      # explicit opt-in only
  enable_via_env: HERMES3D_CLOUD_FALLBACK   # set to "1" to enable
  default_chain:
    - anthropic
    - minimax
    - deepseek
    - siliconflow
```

Document the cloud-enable path in the ADR (§5.5).

### 5.2 `lm_studio_provider.py` (NEW)

Implements the `LLMProvider` protocol (find the contract in `core/llm/__init__.py` or wherever it's defined — verify before assuming). Key responsibilities:

- Talk to LM Studio at `http://localhost:1234/v1/chat/completions` (OpenAI-compatible)
- Support streaming (SSE) AND non-streaming
- Support tool-calling per OpenAI's `tools` array
- Health probe via `GET /v1/models`

Failure modes (each returns `outcome="provider-unavailable"` and falls through to next in chain):
- LM Studio not running (connection refused)
- LM Studio running but no model loaded
- Streaming connection drop (retry once, then fall through)
- Request takes longer than `httpx` timeout (default 30s)

Port override: `HERMES3D_LM_STUDIO_BASE_URL` env var (e.g., `http://10.0.0.42:1234/v1` for LAN-hosted LM Studio).

**Recommended default model for tool-calling workloads:** `NousResearch/Hermes-4-14B-FP8` — Hermes 4 (May 2026), runs on a single 24 GB GPU, supports tool-calling + `<think>` hybrid reasoning, MIT-aligned with Llama 3.1 Community License (commercial OK under 700M MAU cap). Document this in the ADR's References section but DO NOT bundle the weights — user pulls them via LM Studio's UI. Rationale: Hermes Agent (Nous Research) is the spiritual ancestor of "Hermes3D" — circling back to their 4.x model family closes the loop.

### 5.3 Ollama fallback (modify existing `ollama_client.py`)

The audit confirmed `core/llm/ollama_client.py` exists. Don't create a new `ollama_provider.py`. Either:
- Rename `ollama_client.py` → `ollama_provider.py` (cleaner naming) AND update all imports — but this is more risk
- OR keep `ollama_client.py` and have it conform to the same `LLMProvider` protocol — minimal-change path

Pick the minimal-change path. Just ensure `ollama_client.py` exposes the same protocol shape as `lm_studio_provider.py`.

### 5.4 `hipfire_provider.py` (NEW, default disabled)

Same shape as `lm_studio_provider.py`. Talks to Hipfire at `http://localhost:11435/v1/chat/completions`.

Init guard:
```python
def __init__(self) -> None:
    if os.environ.get("HERMES3D_AMD_NODE") != "1":
        raise ProviderDisabled("Hipfire is opt-in; set HERMES3D_AMD_NODE=1 to enable")
    super().__init__()
```

The chain orchestrator in `providers.py` should catch `ProviderDisabled` and skip to the next provider silently (not log an error — disabled is the expected state).

### 5.5 ADR

**`02_architecture/adr/ADR-015-local-llm-providers.md`** (NEW) — 8 sections per the BLENDER-AUDIT-corrected ADR template:

1. Title — ADR-015: Local LLM provider chain — LM Studio default + Ollama fallback + Hipfire optional
2. Status — Proposed
3. Date — 2026-05-03
4. Context — Why LM Studio default (user has 80 models / 652 GB), why Ollama as fallback (already integrated), why Hipfire is opt-in (AMD-only, only meaningful for users with AMD inference nodes)
5. Decision — chain order: lm_studio → ollama → hipfire (when enabled). Cloud fallback is opt-in via `HERMES3D_CLOUD_FALLBACK=1`
6. Rationale & Consequences — privacy posture, cost ($0 daily cap), capability (LM Studio's catalog is large), user agency (cloud always one env-var-flip away)
7. Alternatives considered — Ollama as primary (rejected: user has more LM Studio capacity); cloud-first (rejected: privacy posture); chain-only with no Hipfire (rejected: lose opt-in path for AMD users)
8. References — LM Studio docs, Ollama docs, Hipfire repo

### 5.6 Tests

3 new integration tests, all using mocks (no real LM Studio / Ollama / Hipfire required in CI):

- `test_lm_studio_provider.py` — happy path (mock at :1234), provider-unavailable path (no listener), streaming path
- `test_ollama_client.py` — protocol conformance after refactor (covers existing logic + new chain integration)
- `test_hipfire_provider.py` — `ProviderDisabled` raised when `HERMES3D_AMD_NODE` not set; happy path when env is set

---

## 6. Tests + gates

```text
hermes_run_gate gateId=git-status      cwd=.
hermes_run_gate gateId=git-diff-check  cwd=.
```

Local:
- `pip install -e ".[all]"` (no new deps required — uses existing `httpx`)
- `pytest -q 04_testing/pytest/` — 670+ existing + 3 new pass
- `ruff check 03_implementation/src 04_testing/pytest`
- `ruff format --check 03_implementation/src 04_testing/pytest`
- LM Studio policy validates against schema: `python -c "import yaml,jsonschema; ..."` (use the existing schema)

CI: Layer A/B/C/D/D3/F/M/T/W must all pass.

---

## 7. PR + close-out

```bash
git push -u origin feat/cp-hermes3d-local-lm-studio
gh pr create --base develop \
  --title "feat: LM Studio default + Ollama fallback + Hipfire optional (Task 4a)" \
  --body "[Hermes evidence chain: PASS; Task: CP-HERMES3D-LOCAL-LM-STUDIO; Gate run via hermes_run_gate]"
```

Close-out:
```text
hermes_append_evidence  owner=codex-impl-06  taskId=CP-HERMES3D-LOCAL-LM-STUDIO  kind=checkpoint  summary=LM Studio default chain shipped; PR #N at SHA <commit>
hermes_release_files  owner=codex-impl-06  files=[the lock list]
hermes_release_task   owner=codex-impl-06  taskId=CP-HERMES3D-LOCAL-LM-STUDIO
```

---

## 8. Hard rules

- DO NOT default-enable Hipfire (must require `HERMES3D_AMD_NODE=1`)
- DO NOT REPLACE `llm_policy.yaml` — MERGE only, preserve user values
- DO NOT add cloud providers as defaults — `cloud_fallback_mode.enabled: false` is the contract; user opts in via `HERMES3D_CLOUD_FALLBACK=1`
- DO NOT touch the React UI in this brief — that's split 4c
- DO NOT touch any file outside the §4 lock list
- DO NOT install LM Studio on the test machine; CI uses mocks only

## 9. Failure protocol

If `core/llm/providers.py` doesn't exist as a separate file (chain logic might live in `__init__.py` instead), update the lock list to include `__init__.py` and proceed. This is a known reality-check item the parent brief got wrong.

If the LM Studio API surface has shifted between your training cutoff and now, do a quick WebFetch of `https://lmstudio.ai/docs/local-server` to confirm the OpenAI-compat endpoint shape before implementing.
