# Hermes Agent — Proof-Event Version Tagging (Wave 2 P2-6)

**Date:** 2026-05-09
**Branch:** `claude/p2-6-version-tagged-proofs` (stacked on `claude/agent-version-registry`, the P2-1 PR #162 registry; `KNOWN_VERSIONS = (V012, V013)`).
**Task ID:** `P2-6-PROOFS-2026-05-09`
**Lock owner:** `claude-lead-p2-6-proofs`

## Summary

Every persisted `proof_events` row now carries the active Hermes Agent version (`v0.12` / `v0.13`), the upstream tag (`v2026.4.30` / `v2026.5.7`), and the resolved checkout path. Without this, post-promotion forensic queries cannot tell which Hermes Agent version emitted any given event — a gap that becomes load-bearing the moment an operator flips `HERMES_AGENT_CHECKOUT` mid-process (per-call resolver, PR #155).

## Augmented call sites

Three identical `_append_proof_event(event_type, source_agent, payload)` helpers all funnel into the same `proof_events` table. Each helper was augmented at the single insertion site (one merge call) so all callers inherit version tagging without per-site edits.

| File | Helper line (post-edit) | Notes |
| --- | --- | --- |
| `03_implementation/src/hermes3d/api/routes/agent_updates.py` | `_append_proof_event` (~line 642) | Primary updater path — staged update, rollback, auto-repair, status, backups, skip events. 7 transitive call sites in this file. |
| `03_implementation/src/hermes3d/api/routes/desktop_updates.py` | `_append_proof_event` (~line 304) | Hermes Desktop installer flow — status, backup, download. 3 transitive call sites. |
| `03_implementation/src/hermes3d/api/routes/jobs.py` | `_append_proof_event` (~line 374) | Job lifecycle — claim, transition, cancel, complete, repair-approve. 13 transitive call sites; this helper also stamps `ts_unix` (preserved). |

Indirect call sites (transitive callers that did NOT need editing because the version-tag merge happens at the helper sink):

```
agent_updates.py:87, 94, 119, 128, 196, 228, 637  -> agent_updates._append_proof_event
desktop_updates.py:64, 71, 123                     -> desktop_updates._append_proof_event
jobs.py:52, 76, 168, 176, 190, 205, 221, 239, 247, -> jobs._append_proof_event
        266, 282, 290, 309, 325, 341
```

## Fields added to every emitted event

```jsonc
{
  "version_label":  "v0.12" | "v0.13" | "unknown",
  "upstream_tag":   "v2026.4.30" | "v2026.5.7" | "unknown",
  "checkout_path":  "G:/Github/hermes-agent-fresh"        // v0.12 fallback
                  | "G:/Github/hermes-agent-v013-canary"  // v0.13 default
                  | "<literal HERMES_AGENT_CHECKOUT value>" // unknown
}
```

The `unknown` branch fires when the operator points `HERMES_AGENT_CHECKOUT` at a path the registry does not know (custom fork, forensic clone). `version_label` and `upstream_tag` fall back to `"unknown"`, but `checkout_path` always carries the literal active path so the audit trail still has a forensic anchor.

## New files

- `03_implementation/src/hermes3d/services/proof_helpers.py` — single shared helper. Two callables:
  - `proof_version_fields() -> dict[str, str]` returns the three fields above.
  - `attach_version_fields(payload) -> dict` returns a NEW dict equal to `payload` plus the version fields, with caller keys winning on collision (defensive: a caller who explicitly stamps `version_label` is not silently overwritten).
- `04_testing/pytest/unit/test_proof_event_version_tagging.py` — 13 tests pinning the contract.

## Why frozen dataclass is safe in the event-write hot path

`active_version()` is a tuple scan over `KNOWN_VERSIONS` (length 2 today) calling `Path.resolve(strict=False)` once per registry entry. No I/O, no allocations beyond the resolved Path object, no locks. The frozen-dataclass design (P2-1 contract) means `__setattr__` raises and there is no shared mutable state to race against, so two concurrent FastAPI requests cannot observe each other's mutations of `V012` / `V013`.

The cost is bounded by `hermes_agent_checkout()` which already runs on the proof-event path: an `os.environ.get(...)` plus a `Path()` constructor. Adding `proof_version_fields()` doubles the resolved-Path construction (one for the env, one or two inside the registry lookup) — well under microseconds. Safe to call on every write.

## Backward compatibility contract

Pre-PR rows in the `proof_events` table do not contain `version_label` / `upstream_tag` / `checkout_path` keys. Any reader code (BI dashboards, the upcoming Update Center timeline, the recovery controller's history pane) MUST use `.get("version_label", "unknown")` semantics:

```python
# CORRECT — historical rows fall through gracefully
label = payload.get("version_label", "unknown")
tag = payload.get("upstream_tag", "unknown")
path = payload.get("checkout_path") or "unspecified"

# WRONG — raises KeyError on legacy rows
label = payload["version_label"]
```

A pin test (`test_reader_pattern_uses_get_with_unknown_default`) documents this so any future audit catches a regression that breaks the fall-through.

## Secret hygiene

The registry (P2-1 contract) only stores paths + tags + boolean feature flags by design. No credentials, tokens, or environment values other than the checkout path itself are exposed by `proof_version_fields()`. The `checkout_path` value is `os.environ.get("HERMES_AGENT_CHECKOUT", DEFAULT_AGENT_CHECKOUT)` — already on the path of `hermes_agent_checkout()` and already redaction-policy-governed elsewhere; if it leaks here, the leak is already present in the broader audit log surface.

A dedicated test (`test_unknown_path_does_not_leak_env_other_than_checkout`) sets a sibling `SECRET_TOKEN_DO_NOT_LEAK` env var and asserts it never appears in the serialized payload.

## Test plan results

```
$ python -m pytest 04_testing/pytest/unit/test_agent_version_registry.py \
      04_testing/pytest/unit/test_agent_checkout_resolver.py \
      04_testing/pytest/unit/test_proof_event_version_tagging.py -v

37 passed in 2.34s
```

Test count delta: **+13 tests** in the new file. Pre-existing 24 tests in the registry + checkout resolver suites continue to pass unchanged.

## Two-source provenance basis

Both sources are cited verbatim in the helper module docstring (`services/proof_helpers.py`) and in the test file's module docstring so any future audit can trace the rationale without leaving the source.

1. **NIST SP 800-92 §4 — Log Generation and Storage Architecture**
   <https://csrc.nist.gov/publications/detail/sp/800-92/final>
   *"The system needs to be able to log essential information about each event."* Software-version provenance is part of "essential information" because forensic review across a version upgrade cannot otherwise distinguish behavior. Our `version_label` + `upstream_tag` fields make every persisted event self-attributing.

2. **OpenTelemetry Resource Semantic Conventions — `service.version`**
   <https://opentelemetry.io/docs/specs/semconv/resource/#service>
   The canonical place to record a deployed service's version. Our `version_label` mirrors the shape of `service.version`, so a future OTel exporter wired against `proof_events` can lift the field without re-mapping. `upstream_tag` is the upstream Hermes Agent release tag (e.g. `v2026.5.7`), playing the same role as `service.namespace` + `service.instance.id` would for a finer-grained attribution.

## Persistence-rule observations

No call site used a positional / non-dict shape that would have forced a per-site edit. All three `_append_proof_event` helpers share the `(event_type: str, source_agent: str, payload: dict[str, Any])` signature; the only delta is `jobs.py` returns `event_id` and prepends a `ts_unix` field. The merge helper (`attach_version_fields`) preserves both behaviors because it composes by spreading into a new dict.

If a future helper appears with a flatter signature (e.g. `(event_type, **fields)`), follow the same pattern: invoke `proof_helpers.proof_version_fields()` once just before the SQL insert and merge into whatever dict the row builds.

## Branch / PR

- Base branch: `claude/agent-version-registry` (stacked, NOT main — main lacks the registry as of 2026-05-09).
- Working branch: `claude/p2-6-version-tagged-proofs`.
- Worktree (isolated to avoid concurrent-agent race on the shared checkout): `G:/Github/_claude_worktrees/h3d-claude-p2-6-proofs`.

## Out-of-scope follow-ups

- **Reader-side migration** — Update Center timeline + recovery controller history pane should be audited to confirm they use `.get("version_label", "unknown")` semantics and not `payload["version_label"]`. Tracked separately (not in this PR).
- **OTel exporter wiring** — when (if) the project ships an OTel exporter for `proof_events`, the field mapping is already aligned (`version_label` → `service.version`). No code change here; just documentation.
- **DB column promotion** — if the team later wants `version_label` as a first-class indexed column on `proof_events` (vs nested in JSON), a follow-up migration can lift it. The JSON-payload approach here is non-breaking and back-compatible with existing readers.
