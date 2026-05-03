# ADR-016 — In-house prompt-injection scanner aligned to OWASP LLM-01:2025

**Status:** Proposed.
**Date:** 2026-05-03.
**Related:** [ADR-009 orchestration skeleton](ADR-009-orchestration-skeleton.md) (write-action boundary), PR #37 (security-stub scaffolding, on a different branch and out of scope here).
**Tracking:** `feat/cp-h3d-injection-scanner-v2` branch.

## Context

Hermes3D ingests untrusted text from many sources: user prompts, MCP tool
outputs, LLM-gateway responses, slicer reports, lock-orchestrator handoff
notes. Several of those sources have been or could be a vector for OWASP
LLM-01-shaped prompt injection — including 3D-printing-specific risks
(forged G-code, "skip thermal_runaway") and HermesProof-specific risks
(forged handoff approvals, lock-release directives, owner-string spoofing).

A previous proposal suggested porting `injection_scanner.py` from
`NousResearch/hermes-agent`. That repository **does not contain a file
by that name** — the prior agent who audited the proposal correctly
refused to fabricate a port, and this ADR records that refusal as a
deliberate decision, not an oversight.

The goal of this ADR is to record the design of a real, in-house
prompt-injection scanner authored from scratch and aligned to the public
OWASP LLM-01:2025 catalogue plus a curated Hermes3D-specific ruleset.

## Decision

**Build an in-house scanner.** No third-party port. Pattern files are
authored in-house from publicly documented OWASP LLM-01 markers and
project-internal threat-modelling.

### Module shape

```
03_implementation/src/hermes3d/core/security/
    __init__.py             # public API: InjectionScanner, ScanResult, Finding
    __main__.py             # python -m hermes3d.core.security CLI shim
    injection_scanner.py    # core engine
    cli.py                  # argparse CLI implementation
    patterns/
        __init__.py
        owasp_llm01.yaml    # OWASP LLM-01:2025 patterns (4 categories)
        curated_inhouse.yaml # Hermes3D-specific patterns (3D-printing + HermesProof)
```

The public API is exactly:

```python
from hermes3d.core.security import InjectionScanner, ScanResult, Finding
```

### Data shapes

- `Finding` (frozen dataclass):
  `rule_id: str`, `severity: "low" | "medium" | "high"`,
  `match_excerpt: str` (<= 80 chars), `position: int`, `description: str`.
- `ScanResult` (dataclass):
  `severity: "clean" | "low" | "medium" | "high"`,
  `findings: list[Finding]`,
  `text_redacted: str`,
  `fail_closed: bool`.

`InjectionScanner` exposes:

- `scan(text: str) -> ScanResult`
- `scan_dict(data: dict, fields: list[str] | None = None) -> ScanResult`
- Constructor accepts `ruleset_paths`, `fail_threshold`, and
  `match_timeout_seconds` (POSIX-only; ignored on Windows).

### Severity model

```
no findings                     -> "clean"
>= 1 high finding               -> "high"
>= 2 medium findings (no high)  -> "medium"
otherwise (only low/medium=1)   -> max per-rule severity, floored at "low"
```

`fail_closed` is True iff aggregate severity is at or above the
configured `fail_threshold` (default `"high"`). Callers decide what to
do with the result — the scanner itself never raises on findings.

### Pattern sources

`owasp_llm01.yaml` rules (each cited to the OWASP page):

| Category                         | Rule ids                                                                          |
|----------------------------------|-----------------------------------------------------------------------------------|
| Indirect injection / role spoof  | LLM01-IGN-PREV, LLM01-DISREGARD, LLM01-SYSPROMPT-TAG, LLM01-CHATML-START/END, LLM01-USER-CLOSE, LLM01-INST-TOKEN |
| Tool poisoning / RCE             | LLM01-EXEC-FOLLOWING, LLM01-RM-RF-ROOT, LLM01-CURL-PIPE-SH, LLM01-WGET-PIPE-SH, LLM01-POWERSHELL-IEX |
| Prompt leak                      | LLM01-LEAK-SYSPROMPT, LLM01-LEAK-INSTRUCTIONS, LLM01-LEAK-VERBATIM                |
| Jailbreak personas               | LLM01-JB-DAN, LLM01-JB-DEVMODE, LLM01-JB-IGNORE-SAFETY, LLM01-JB-NO-RESTRICTIONS, LLM01-JB-PRETEND-AI |

`curated_inhouse.yaml` rules (Hermes3D threat-model):

| Category                      | Rule ids                                                                                                |
|-------------------------------|---------------------------------------------------------------------------------------------------------|
| 3D-printing safety override   | H3D-EXTRUDER-OVERTEMP, H3D-BED-OVERTEMP, H3D-DISABLE-THERMAL-RUNAWAY, H3D-DISABLE-ENDSTOP, H3D-EMERGENCY-DISABLE, H3D-GCODE-RAW-PRELUDE, H3D-GCODE-FW-RESET, H3D-DISABLE-FAN |
| HermesProof / lock orchestration | H3D-LOCK-RELEASE-ALL, H3D-HANDOFF-FORGE, H3D-OWNER-SPOOF, H3D-PROOF-BYPASS, H3D-MERGE-FORCE, H3D-PROOF-KEY-LEAK |

Patterns are **data, not code** — operators can ship pattern updates
without code review on the engine. The loader validates structure and
compiles regexes at scanner construction; failures raise
`InjectionScannerError` immediately rather than at scan time.

### Regex hardening

All patterns are bounded:

- No nested unbounded `.*` or `.+` groups.
- Wildcards are bounded with explicit `{0,N}` upper limits where
  variable-length matching is needed (e.g. `LLM01-CURL-PIPE-SH`).
- Case-insensitivity is applied uniformly via `re.IGNORECASE` at compile
  time so that pattern authors don't have to encode it themselves.

A SIGALRM-based per-pattern timeout is available on POSIX. On Windows
the timeout is silently ignored — bounded patterns are the primary
defence and the timeout is a defence-in-depth layer. This is documented
in code and in this ADR.

### Redaction

Each match is replaced with `[REDACTED-<rule_id>]` in
`ScanResult.text_redacted`. Overlapping spans collapse to the
earliest-starting (widest) span so that overlapping rule hits don't
produce nested or torn redactions. Redacted text is intended for safe
logging; `findings` carry the rule metadata if the original needs to be
inspected.

### CLI

Two equivalent invocations:

```
python -m hermes3d.core.security <args>            # via __main__.py shim
python -m hermes3d.core.security.injection_scanner <args>   # explicit module path
```

The latter (specified in the brief) emits a benign `RuntimeWarning`
from `runpy` because `__init__.py` re-exports symbols from
`injection_scanner` — this is documented in code and is the standard
Python behaviour when a package re-exports its `__main__` module's
symbols. The `__main__.py` shim avoids this cosmetic warning.

Exit codes: `0` for clean / below threshold, `1` for fail-closed, `2`
for usage / IO error.

### What this ADR explicitly does NOT do

- **No** vendor-licence file (no `THIRD_PARTY_LICENSES/hermes-agent.LICENSE`).
- **No** "ported from" / "based on" attribution language.
- **No** scraping or vendoring of any third-party scanner.
- **No** inline shell execution by the scanner (it's pure regex match
  + redact).

## Alternatives considered

- **Port from `NousResearch/hermes-agent`.** Rejected: the file does
  not exist there. A port that is not a port would be a falsehood in
  the audit trail.
- **Adopt a third-party Python library (e.g. PromptGuard, garak).**
  Rejected for v1: those tools are heavyweight, ML-based, and would
  introduce a model dependency at the moment we need a deterministic,
  fast first line of defence. They remain candidates for a later
  defence-in-depth layer (Layer B in security_review patterns).
- **Hard-code patterns in Python source.** Rejected: making patterns
  data lets ops update them on a faster cycle than the engine.
- **No fail-closed flag — always raise.** Rejected: callers across the
  codebase have different policies (e.g. logger middleware vs.
  pre-flight gate), so the policy decision belongs at the call site.

## Consequences

**Positive:**

- A real, deterministic, fast (microseconds-per-scan) injection
  detector is now in-tree.
- Pattern catalogues are discoverable and auditable as YAML.
- The scanner can be invoked as a library, a CLI, or a CI gate.
- Test coverage includes both positive cases per category and an
  explicit negative-case suite over legitimate Hermes3D project text
  to guard against false positives.

**Risks / follow-ups:**

- Regex catastrophic-backtrack remains a theoretical risk; bounded
  patterns and the POSIX timeout mitigate but do not eliminate it.
  Layer-B follow-up: re-engine on the `regex` module with a hard timeout
  if the threat model justifies it.
- Pattern catalogue will need ongoing maintenance as OWASP LLM-01
  updates and as Hermes3D's own threat model expands. ADR-016 should
  be revised, not replaced, when materially new pattern categories are
  added.
- Layer-B integration with `gateways/llm.py` (scan inbound LLM
  responses) is left for a follow-up PR — this PR ships the engine and
  rulesets only, no integration into call sites.
