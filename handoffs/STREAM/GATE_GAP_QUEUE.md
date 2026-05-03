# GATE_GAP_QUEUE.md — gates that should exist but don't

> Either side picks `unclaimed` items, top of priority order. Claim by posting
> TASK_CLAIMED in the other side's inbox with the gap ID as the correlation.
> Status field updated by the claimant. Don't delete entries — strike them
> through with `~~text~~` once `merged`.

---

## Priority key

- **P0** — would have caught a known-historical bug; must land before v5.3.0 release
- **P1** — closes a known coverage gap, no incident yet
- **P2** — defense-in-depth; nice to have

---

## P0 (6 items)

### gap-2026-05-03-001 — license-coverage-gate
- domain: supply-chain
- status: claimed:claude-impl-hp-licenses
- evidence: stub at `scripts/license-and-deps-gates.mjs` exists per git status; never wired
- estimated-effort: M
- dependencies: HermesProof harness

Allowlist of license SPDX identifiers. Reject any transitive dep with
non-permissive license (AGPL, GPL-3, BUSL, etc.). Block PR.

### gap-2026-05-03-002 — sbom-generation-gate
- domain: supply-chain
- status: unclaimed
- evidence: 2026 supply-chain attack surface; SLSA L2 expected by downstream
- estimated-effort: M
- dependencies: license-coverage-gate

CycloneDX or SPDX SBOM auto-generated per release. Stored alongside
`PROOF/latest.json`. Required for any tag.

### gap-2026-05-03-003 — dep-fresh-gate
- domain: supply-chain
- status: unclaimed
- evidence: SDK was 5 minor versions behind in v0.5.0 audit
- estimated-effort: S
- dependencies: none

Asserts every direct dep in `package.json` is within 6 months of latest
or has explicit `@allow-stale` annotation in a sidecar file.

### gap-2026-05-03-004 — workflow-pinning-gate
- domain: supply-chain / security
- status: unclaimed
- evidence: trivy/tj-actions/axios incidents 2026-03; current workflows use `@v4` tags
- estimated-effort: S
- dependencies: none

Asserts every `uses:` in `.github/workflows/*.yml` is pinned to a full
40-char SHA, not a tag. Auto-generates dependabot config to bump them.

### gap-2026-05-03-005 — accessibility-wcag-aa-gate
- domain: a11y
- status: unclaimed
- evidence: round-1 audit found 7 SVGs missing `<desc>` + prefers-reduced-motion
- estimated-effort: M
- dependencies: none

axe-core run on built marketing site + on launcher Gradio UI. Threshold:
0 critical, 0 serious. Fail PR otherwise.

### gap-2026-05-03-006 — mcp-scan-static-gate
- domain: security
- status: unclaimed
- evidence: PipeLab 2026 — 82% of MCP servers fail path-traversal hardening
- estimated-effort: M
- dependencies: none

Run `mcp-scan` (Invariant Labs static analyzer) over `src/server.mjs`
on every PR. Catches tool-poisoning + missing input validation patterns.

---

## P1 (8 items)

### gap-2026-05-03-007 — secret-rotation-evidence-gate
- domain: security
- status: unclaimed
- evidence: 2026-05-03 .env.txt incident; need proof secrets are rotated post-leak
- estimated-effort: S

Asserts `G:\private\.env` (or sibling) modified-time > suspected leak
date OR a `secret-rotation.evidence` row exists for each named secret.
Doesn't read secrets — only metadata.

### gap-2026-05-03-008 — thermal-runaway-detection-gate
- domain: 3d-print-stability
- status: unclaimed
- evidence: M73-runaway is the #1 firmware-side print fire vector
- estimated-effort: L

Asserts orchestrator's monitoring loop fires `EmergencyStop` event within
2s of detecting `extruder.temperature` > target+15°C for >5s OR thermistor
error event from Klipper. Test = sim'd thermistor failure trace.

### gap-2026-05-03-009 — gcode-bounds-precondition-gate
- domain: 3d-print-stability
- status: unclaimed
- evidence: off-bed extrusion damages bed/nozzle, common slicer bug
- estimated-effort: M

Asserts every G-code slated for print is parsed and bounds-checked
against printer's printable volume BEFORE upload. Block + alert on any
move outside (X, Y) bed bounds.

### gap-2026-05-03-010 — material-temperature-window-gate
- domain: 3d-print-stability
- status: unclaimed
- evidence: PETG printed at PLA temp causes layer adhesion failure 100% of time
- estimated-effort: S

Asserts profile's `nozzle_temp` and `bed_temp` are within the loaded
material's window from the material database. Block submission otherwise.

### gap-2026-05-03-011 — printer-availability-heartbeat-gate
- domain: 3d-print-stability
- status: unclaimed
- evidence: silent printer offline = job sits in queue forever
- estimated-effort: S

Asserts Moonraker/OctoPrint endpoint responds within 5s on every job
submission. Fails fast with clear error.

### gap-2026-05-03-012 — emergency-stop-timing-gate
- domain: 3d-print-stability
- status: unclaimed
- evidence: safety-critical, no current automated test
- estimated-effort: M

End-to-end test: `M112` issued → motor halt evidence in firmware response
within 200ms. Run against simulator (Marlin/Klipper sim).

### gap-2026-05-03-013 — docs-changes-reflected-gate
- domain: docs
- status: unclaimed
- evidence: README versioning drifted across v0.5.0
- estimated-effort: S

Asserts: if `package.json` version bumped OR ADR added/changed, README/CHANGELOG
must have a matching diff line.

### gap-2026-05-03-014 — perf-budget-gate
- domain: perf
- status: unclaimed
- evidence: user explicitly: "many should be instant but delay"
- estimated-effort: M

Asserts: cold-start `hermes_doctor` <300ms, lock acquire <50ms p95,
heartbeat <20ms p95. Generates `PERF/latest.json` proof artifact.

---

## P2 (4 items)

### gap-2026-05-03-015 — bed-adhesion-precondition-gate
- domain: 3d-print-stability
- status: unclaimed
- estimated-effort: M

First-layer Z-offset within ±0.05mm of profile target. Bed at temp ≥97% of
profile target before homing. Block start otherwise.

### gap-2026-05-03-016 — print-history-failure-rate-gate
- domain: 3d-print-stability
- status: unclaimed
- estimated-effort: L

Last 10 prints on this printer: ≤3 failures. Otherwise emit advisory and
require operator confirm.

### gap-2026-05-03-017 — release-checksum-gate
- domain: supply-chain
- status: unclaimed
- estimated-effort: S

Every release artifact has a sidecar SHA-256 + signature. Block release
without both.

### gap-2026-05-03-018 — coderabbit-review-gate
- domain: docs / quality
- status: unclaimed
- estimated-effort: S

Asserts CodeRabbit posted at least one comment on the PR (proxy for
"got reviewed"). Doesn't gate on verdict, just on presence of feedback.

---

## Bookkeeping

- 2026-05-03 11:30Z — initial seed by Claude SCRIBE
- claim convention: edit `status:` field in place, post TASK_CLAIMED in other side's inbox
