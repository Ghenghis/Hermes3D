# W21 Audit — 3-Pass Synthesis & Action List

**Date:** 2026-05-12
**Auditor:** Claude
**Inputs:** 3 pass markdowns + 1 prior reality-gap doc, 45 sub-agent reports total, ~100 evidence checkpoints.
**Develop SHA at synthesis:** `be2755f` (#258 MVP-2 + #259 hotfix merged; #260 reality-gap docs in-flight)

This is the operator-facing roll-up. Each finding has: (a) what's wrong, (b) what we measured, (c) the smallest viable fix, (d) the priority.

---

## §0. The single most-important answer

**Question (operator):** "Is it 95% E2E?"

**Synthesis answer:** No. After 45 sub-agent probes across 3 differently layered passes:

* **Reachable surface — ~95%.** 279 routes registered, 25 hash routes registered, 60-app + 4-printer + 8-persona + 27-table schemas in place.
* **Working surface — ~80%.** 61/63 GETs return 200, 10/16 critical POSTs WORKING_REAL, 4/16 honest-blocked, 2/16 broken. DB **IS** populated (751 rows; the prior "0 rows" claim was the wrong DB file).
* **Completable user journeys — ~50%.** 5/15 WORKING_REAL · 4/15 WORKING_WITH_REFRESH/POLLING/UX_GAP · 4/15 PARTIAL or BLOCKED · 1/15 NOT_WIRED · 1/15 MOSTLY_WORKING.

**Weighted gut: ~65-75% E2E day-to-day** — better than the prior gap doc's 55-65% estimate because the **DB IS populated**, the **reconciler IS working**, **14/24 UI tabs already poll**, the **Plugin/Apps/Autopilot/Jobs/Approvals/Printers paths all work**, and **MiniMax+DeepSeek smoke is PASS_LIVE**.

But not 95% because of these confirmed gaps:

* **MVP-3 (persona execution) is 0%.** Claim works, work does not.
* **Gen3D pipeline is 5-10%.** Calibration cube local fallback works; no real image-to-3D path; 22 GB GPU pinned by another tenant.
* **UI hash-route registers 25 tabs, but 4 have STALE_FETCH_ONCE** (Artifacts, Gen3D, Voice, Roadmap) and 5 are MANUAL_REFRESH_ONLY.
* **Queue release endpoint is broken** (returns success but doesn't move the file back to pending).
* **`/api/proof/events` silently drops** events from durable ledgers.
* **40% of proof envelopes** fail re-verify with the default key.

---

## §1. Cross-pass alignment — what each pass uniquely proved

| Concern | Pass 1 (Structural) | Pass 2 (Behavioral) | Pass 3 (E2E Journey) |
|---|---|---|---|
| **Backend routes** | 279 registered, no dead files | 61/63 GETs OK; 2 timeouts | Routes work but UI adapters use slightly different paths (J1 finding) |
| **DB tables** | 27 declared, 11 indexes, 10 FKs | 751 rows live (vs "0" old claim) | Approvals flows work end-to-end (J15) |
| **UI tabs** | 25 registered hash routes | 14 of 24 tabs poll | Apps/Plugins/Autopilot/Jobs WORKING_REAL (J5-8); Agents NOT_WIRED for queue panel (J4) |
| **Slicer** | `slicer.py` 540 LOC | Real subprocess.run to PrusaSlicer | STL→G-code chain works (J3) |
| **MiniMax/DeepSeek** | Provider modules + smoke route registered | PASS_LIVE 1047 ms + 1151 ms | not journey-tested directly; used by Agents/Code/Recovery |
| **Hermes Agent execution** | `queue_poller` + `queue_bridge` 380 LOC | Bridge claims + heartbeats | **Zero execution code anywhere** (J12 BLOCKED_AT_STEP_4) |
| **Gen3D providers** | `generation.py` 585 LOC | All 4 not_installed; calibration_cube fallback works | Image upload disconnected from generation (J2 BLOCKED_AT_STEP_5) |
| **Source-OS modules** | 60 registered + `modules.py` 2394 LOC | 56 paths exist; 4 mis-rooted | Backup→Check→Apply works but UI freshness lags (J9) |
| **Proof envelope** | `proof_envelope.py` + `truth_gate` registered | 40% of recent proofs fail re-verify | not directly journey-tested; deferred |
| **Event ledger** | 3 stores (SQLite proof_events, orchestrator NDJSON, evidence NDJSON) | `/api/proof/events` accepts but **silently drops** | not directly journey-tested |
| **Printer fleet** | `printers.py` 877 LOC + `printer_safety.py` 151 LOC | 4 printers LAN-reachable; S1 lock enforced | Bi-directional safety; no operator bypass path (J11 WORKING_REAL) |
| **CAD toolchain** | 6 backends declared in `modeling_backend.py` | OpenSCAD/Blender 5.1.1/trimesh/manifold3d installed; CadQuery+FreeCAD absent | OpenSCAD's trivial STL export fails (Pass-2 surfaced; Pass-3 didn't retest) |

---

## §2. The honest scorecard (weighted)

| Pillar | Score | Pass-3 evidence |
|---|---|---|
| GUI shell (boot, routing, themes, persistence) | ~88% | J1 dashboard mounts; J10 settings persist; theme list 6 entries (labels missing) |
| Backend HTTP wiring | ~92% | 61/63 GETs OK · 10/16 POSTs real · only 2 routes broken |
| Slicer subprocess to PrusaSlicer/Orca | ~95% | J3 produces real G-code; verified subprocess.run on disk |
| Plugin activate / deactivate | ~90% | J6 DB persists; UI auto-reloads |
| Apps registry + per-app proof | ~75% | J5 works per-app; no bulk button; 18 apps unproven; cadquery+langchain fail at Python import |
| Approvals lifecycle | ~85% | J15 pending→approved transition + 5s polling |
| Jobs (cancel/retry/repair/rollback) | ~85% | J8 all 4 transitions wired; immediate refetch after cancel |
| Autopilot (write-plan/next-gate/write-report) | ~85% | J7 real bytes + SHA + proof_event_id; honest-blocked 409 correct |
| Provider keys + MiniMax/DeepSeek smoke | ~75% | PASS_LIVE; 5 other providers have keys but no smoke endpoint |
| Voice (Azure-dep) | ~70% | J13 honest-blocked; STT is client-side Web Speech (not a bug) |
| Learning workbench | ~75% | J14 candidates queue; 9 blockers prevent run (correct safety policy) |
| Settings + Update Center | ~70% | J10 SQLite-backed; update-center schema partial; theme labels null |
| Source OS modules | ~65% | J9 backup+check+apply work; 4 mis-rooted paths; no auto-refresh post-action |
| Design tab (1 template) | ~70% | J3 desk_organizer template works end-to-end |
| Printer fleet + safety | ~95% | J11 4 reachable; S1 bi-directional lock |
| Files / artifacts / DB tracking | ~90% | reconciler in sync (202=202); /api/files under-counts by 13% |
| Realtime UI refresh | ~70% | 14/24 tabs poll; 4 strictly stale; 5 manual-refresh |
| **Hermes Agent execution loop** | **10%** | **J12 zero executor code; MVP-3 not started** |
| **Gen3D pipeline (real providers)** | **10%** | **J2 all 4 providers blocked; rembg missing; VRAM pinned** |
| Test route coverage | ~43% | 21/37 routes have no direct test |
| Event ledger durability | ~50% | 3 ledgers, no propagation between them; /api/proof/events silently drops |
| Proof envelope re-verify | ~60% | 40% mismatch with default key |

**Weighted estimate:** ~65-72% E2E. Solid foundation, two big P0 craters (MVP-3 + Gen3D), several P1 leaks (refresh gaps, stale locks, queue release bug, silent event routing).

---

## §3. Ranked fix list

The order to ship fixes, ranked by **(operator pain × ease-of-fix)**. Each item is one PR.

### P0 — ship today or this week

1. **P0-A: Queue release bug** (Pass 2 §3, Pass 3 J4)
   *Effect:* operator/poller cannot put a claim back to `pending` through the API. Tasks stuck.
   *Fix:* `services/queue_bridge.py:release_task` — destination path math is wrong; one-line move correction + unit test.
   *Effort:* small (~30 min).

2. **P0-B: `/api/proof/events` silent routing** (Pass 2 §11)
   *Effect:* proof events accepted by API are NOT written to SQLite `proof_events`, NOT to `events.ndjson`, NOT to `evidence/ledger.ndjson`. Events vanish on restart.
   *Fix:* add SQLite insert + evidence-ledger append in the POST handler; cover with integration test.
   *Effort:* small-medium (~2 h).

3. **P0-C: `/api/health/services` 3-second timeout** (Pass 2 §1)
   *Effect:* every Dashboard mount blocks 3 s on this endpoint.
   *Fix:* cache probe results with 30s TTL; per-probe timeout 500 ms; return partial-success.
   *Effort:* small (~1 h).

4. **P0-D: Source-OS path mismatch for 4 modules** (Pass 2 §15, Pass 3 J9)
   *Effect:* blender_mcp_candidates, open3d, numpy_stl, pymesh report `local_path` under `03_implementation/source-lab/…` which doesn't exist (real clones are at `Hermes3D-OS/source-lab/`).
   *Fix:* re-seed registry rows with correct workspace root.
   *Effort:* small (~1 h).

5. **P0-E: Recover 6 stale MCP locks** (Pass 3 J10)
   *Effect:* 6 of 12 active locks are from past `w18-a1`, `w18-a10`, `w18-a16` Claude sessions and never reaped.
   *Fix:* call `mcp__hermes3d-locks__hermes_recover_stale_locks` (one MCP call).
   *Effort:* trivial (~1 min).

### P0.5 — the two big craters

6. **P0.5-A: MVP-3 persona execution surface** (Pass 3 J12, Pass 2 §3-extend)
   *Effect:* the orchestrator queue is a claim graveyard. 8 W21 tasks claimed, 0 deliverables auto-produced.
   *Fix scope:* a `persona_executor.py` service that:
     1. Watches `tasks/claimed/` for tasks whose `claimed_by` matches one of our personas.
     2. For audit-class tasks (W21-A1, A2, A3, A5, A6, A7, A8): dispatch the task summary + handoff_path through MiniMax/DeepSeek with a small reusable prompt template, capture the response, write the `handoff_path` markdown to disk.
     3. For build-class tasks: mark `BLOCKED_HUMAN` honestly with a 1-line reason (don't fake a code change).
     4. Move task to `done/` after persisting the deliverable. Append to `evidence/ledger.ndjson`.
   *Effort:* medium (~1-2 days). This is the highest-leverage P0.

7. **P0.5-B: Gen3D minimum-viable pipeline** (Pass 3 J2)
   *Effect:* Logo → 3D model journey is structurally complete but pipelinically disconnected.
   *Fix scope:* three small PRs in sequence:
     - PR-a: `pip install rembg --upgrade` (resolve NumPy 1.x ↔ 2.3.2 conflict; pin via pyproject.toml).
     - PR-b: install TripoSR (lightest at 4 GB VRAM); GPU cleanup required first.
     - PR-c: wire `generation.run` to read `reference_artifact_id`, run rembg, run TripoSR, persist resulting STL with proof envelope.
   *Effort:* medium (~3-5 days) — depends on GPU VRAM being freed by operator.

### P1 — visible to operator, fix this sprint

8. **P1-A: Agents tab UI panel for `/api/agents/queue/status`** (Pass 3 J4)
   *Effect:* W21-A4 MVP-2 backend is wired; UI panel shows different data (TeamTasksPanel). Operators can't see claimed W21 tasks in the GUI.
   *Fix:* one new component `ClaimedTasksPanel` rendering `pending/claimed/done/blocked` counts + per-task heartbeat. Wire into `Agents.tsx`.
   *Effort:* small (~3-4 h).

9. **P1-B: SourceOS auto-refresh after Backup/Check/Update actions** (Pass 3 J9)
   *Effect:* `latest_backup` field doesn't update without a tab reload.
   *Fix:* AppDetailPanel passes `onRefresh` to ActionButton; ActionButton calls `onRefresh()` after every success.
   *Effort:* small (~30 min).

10. **P1-C: Design.tsx auto-refresh "Recent STLs" after slice** (Pass 3 J3)
    *Effect:* G-code lands on disk but UI doesn't show it without a tab reload.
    *Fix:* Design.tsx's slice handler triggers a `/api/files?bucket=slicer` re-fetch.
    *Effort:* small (~30 min).

11. **P1-D: Add polling to 4 STALE tabs** (Pass 2 §12)
    *Effect:* Artifacts / Gen3D / Voice / Roadmap don't refresh.
    *Fix:* one `useEffect(setInterval, 15000)` per tab.
    *Effort:* small (~2 h total).

12. **P1-E: Run the 18 unproven app proofs** (Pass 2 §6)
    *Effect:* 18 apps have `proof_command` set but `last_proof_status=null`. Operator confidence is poor on those rows.
    *Fix:* add a "Run all unproven" button OR a one-time batch script.
    *Effort:* small UI work (~2 h), or 30 min scripted.

13. **P1-F: Fix cadquery + langchain Python-env mismatch** (Pass 2 §6, Pass 3 J5)
    *Effect:* both apps listed as `install_state:installed` but `python -c "import"` fails.
    *Fix:* either (a) reinstall in the active env or (b) downgrade `install_state` to `source_available` to be honest.
    *Effort:* small (~15 min).

14. **P1-G: `/api/voice/stt` 502 → 503** (Pass 2 §2, Pass 3 J13)
    *Effect:* honest-block returned with wrong status code.
    *Fix:* return 503 service-unavailable when Azure not configured.
    *Effort:* trivial (~10 min).

15. **P1-H: `/api/generation/run` silently aliases unknown templates** (Pass 2 §5)
    *Effect:* "unknown" template_id silently maps to calibration_cube — UX surprise.
    *Fix:* 422 + supported_templates list.
    *Effort:* trivial (~15 min).

16. **P1-I: Settings update-center response missing keys** (Pass 3 J10)
    *Effect:* `components` and `velopack` missing; UI must fallback.
    *Fix:* return the documented shape from `update_center.py:list_updates`.
    *Effort:* small (~30 min).

17. **P1-J: Themes `label` field is null** (Pass 3 J10)
    *Effect:* UI can't show human-readable theme names.
    *Fix:* either populate `label` in `data/themes/*.json` or compute from `id`.
    *Effort:* small (~15 min).

18. **P1-K: 8 stale W18-A7/A9 jobs blocking Learning runner** (Pass 3 J14)
    *Effect:* operator can queue Learning candidates but they sit forever.
    *Fix:* cancel/complete those 8 jobs via `POST /api/jobs/{id}/cancel`.
    *Effort:* small (~5 min).

19. **P1-L: J1 Dashboard 4-route adapter-path mismatch** (Pass 3 J1)
    *Effect:* Dashboard adapter sees 404 on workflows / proof_bundles / system_snapshot / dimensional_reports; Pass-2 saw 200 on the canonical paths.
    *Fix:* read the adapter strings in `adapters.live.ts` vs the route declarations and reconcile (probably an `/api/` prefix or trailing slash).
    *Effort:* small (~30 min).

### P2 — backlog (still real)

20. **Proof envelope key rotation:** 40% mismatch. Decide: rotate `HERMES3D_PROOF_KEY` and re-sign historical envelopes, or accept legacy batch as unverifiable.
21. **Connector + Skills registries:** both honest-blocked stubs. Implement when needed.
22. **21 untested route files:** add minimal smoke test per route (200 + shape).
23. **34 skipped tests:** un-skip what's unskippable, document why for the rest.
24. **/api/files under-counts var/ by ~13%:** scanner skips designs/ subdir variants.
25. **5 providers have keys but no live smoke:** OpenAI, HuggingFace, GitHub, CodeRabbit, Azure Speech, SiliconFlow. Wire smoke endpoints only if the operator uses them.

---

## §4. What this 3-pass audit accomplished

* Caught the **wrong-DB-file** mistake in the prior gap audit (Pass 2 §4) — turns out 751 rows are tracked, not 0.
* Caught the **3 mis-counted UI button claims** (`Plugins.tsx:151`, `SourceOS.tsx:534`, `:547`) — those buttons DO have onClick handlers. Earlier "5 buttons broken" was 0.
* Caught the **release-task path-math bug** in PR #258's queue_bridge code (Pass 2 §3 reproducer).
* Surfaced the **silent routing of proof events** to a never-reached ledger (Pass 2 §11).
* Surfaced the **adapter-path vs route-registration drift** in J1 (Dashboard 4-route 404).
* Surfaced the **Source-OS path mis-rooting** (Pass 2 §15) — 4 modules pointing at the wrong workspace root.
* Surfaced the **MVP-3 zero-executor reality** (Pass 3 J12) with file:line citations across the entire `src/hermes3d/` tree.
* Verified **bi-directional S1 safety** (J11) — non-bypassable through both UI and backend.
* Verified **MiniMax + DeepSeek live smoke** (PASS_LIVE 1047 / 1151 ms, body_sha256 captured) and the strict separation from LM Studio.

---

## §5. Rules followed in all 3 passes

* **No printer hardware writes.** Read-only Moonraker probes only; S1 lock test confirmed via 423 response (not an actual heat command).
* **No fake pass.** Every claim cites file:line, HTTP response, byte count, or filesystem evidence.
* **No route-only green.** Pass 2 + Pass 3 cross-check the live behavior, not just route registration.
* **No broad skips.** 45 sub-audits dispatched across 3 passes; missing 4 (2 in P2, 2 in P3) were filled by direct probes.
* **LM Studio NOT presented as MiniMax.** §1 + §8 keep them separate in both audit doc and live response shape.
* **Lag-protection:** behavioral probes use timeouts + bounded retries; the `/api/agents/action-catalog` 0-byte result on first probe was re-probed with longer timeout and the real 57 KB body recovered.

---

## §6. Doc trail

These four audit docs ship together as one PR:

* `W21_AUDIT_PASS1_STRUCTURAL_2026-05-12.md` — what exists
* `W21_AUDIT_PASS2_BEHAVIORAL_2026-05-12.md` — what each surface does live
* `W21_AUDIT_PASS3_E2E_JOURNEYS_2026-05-12.md` — what 15 user paths actually complete
* `W21_AUDIT_3PASS_SYNTHESIS_2026-05-12.md` — this doc

End of synthesis. Next action: open one docs PR for all four, then start the P0 fix chain in the order above.
