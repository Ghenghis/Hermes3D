# GUI Incomplete-E2E Audit — Canonical Wave 15 Synthesis (2026-05-10)

- **Audit ID:** `GUI_INCOMPLETE_E2E_AUDIT_2026-05-10`
- **Wave / Agent:** 15 / Agent 6 (Audit Integrator)
- **Owner / Lock:** `claude-w15-a6-integrator`
- **Mode:** READ-ONLY synthesis (no source edits; this doc consolidates 5 sibling audits into the canonical record)
- **Repo:** `G:/Github/h3d-gui-wiring-codex` (origin `https://github.com/Ghenghis/Hermes3D.git`)
- **Reference state:** `origin/develop` @ `c13e30f` (W14 theme switcher landed 2026-05-10)
- **Inputs (all on disk):**
  - `W15_A1_REPO_CONTRACT_STATE_2026-05-10.md` — Contract / repo state
  - `W15_A2_IMAGES_GUI_INVENTORY_2026-05-10.md` — Reference pack inventory
  - `W15_A3_ROUTE_COMPONENT_COMPLETENESS_2026-05-10.md` — Route + component classification
  - `W15_A4_MOCK_FAKE_AUDIT_2026-05-10.md` — Mock / fake / no-fake findings
  - `W15_A5_VISUAL_ORACLE_GAPS_2026-05-10.md` — Playwright visual-oracle capability gaps

---

## 1. Executive verdict

Per the user's explicit specification, the GUI Visual-E2E completion state is rendered as **five separate verdicts**, each one of `GREEN` / `NOT_LANDED` / `PARTIAL` / `RED`. The composite verdict (`GUI_E2E_COMPLETE`) is the AND of the others.

| # | Verdict ID | Value | Justification (witness audit) |
|---|---|---|---|
| 1 | **GUI_FUNCTIONAL_GREEN** | **GREEN** | 17 hash-routed primary tabs render with live data per W15-A3 §1.1 + §3.7 (14 FULLY_WIRED, 18 PARTIALLY_WIRED but all rendering). W14 walkthrough (PR #204) landed ThemeProvider mount; W13-10 (#203) cleared pre-Wave-14 backlog. No routed surface ships fake data — W15-A4 §3.1 confirms the 9 UNACCEPTABLE_FAKE tab files are unrouted dead code. |
| 2 | **GUI_VISUAL_CONTRACT_LANDED** | **NOT_LANDED** | W15-A1 §3: **0 of 8** Wave-14 contract / audit / ledger docs committed to `origin/develop`; 7 of 8 exist locally as untracked; 1 (`W14_A6_*`) does not exist at all. The single W14-tagged PR (#204) is a code fix unrelated to the contract. No Contract PR has ever been opened. |
| 3 | **GUI_VISUAL_ORACLE_LANDED** | **PARTIAL** | W15-A5 §2: **1 of 10** required oracle capabilities present (pixel comparison via `toHaveScreenshot`). 9 missing capabilities (crop manifest, viewport overrides, console-strict, 404-fail, no-fake DOM scan, deterministic clock, forced theme, `fonts.ready`, region screenshots) specified line-by-line in W14-A3; no implementation PR opened (W15-A5 §3). |
| 4 | **GUI_PIXEL_PERFECT** | **RED** | Deferred until oracle is GREEN. With 9 oracle capabilities missing (W15-A5), 11 collage references without `regions[]` (W15-A2 §5), and 2 live blocking viewport outliers (`1672×941`, `1586×992`; W15-A2 §6), pixel parity cannot be measured. Harness would only assert full-page parity for one quadrant of every collage at one viewport, with no console-error / 404 / fake-content gates. |
| 5 | **GUI_E2E_COMPLETE** | **RED** | Composite: 1 of 5 verdicts GREEN. End-to-end completion requires (a) Contract PR merged, (b) Oracle implementation merged, (c) all 9 capabilities running cleanly, (d) per-region + per-viewport diffs green with empty console / 404 / fake reports. None of (b)–(d) in flight. |

Composite line: **GUI is functionally complete and honest, but the visual-E2E contract is unmerged, the oracle is 10% built, and pixel-perfection cannot be measured. RED on the composite.**

---

## 2. Audit synthesis — per-input-doc bullets and cross-cutting findings

### 2.1 W15-A1 — Repo / Contract state

- `origin/develop` HEAD = `c13e30f` (matches the W14 contract target).
- **7 of 8** W14 contract / audit / ledger docs present locally as untracked files; **0 of 8** on `origin/develop`; **1** (`W14_A6_*`) does not exist anywhere.
- Open-PR queue empty; no W14_A* PR has ever been opened. The single W14-tagged PR (#204) is a code fix, not the contract.
- `claude/w14-pr1-visual-oracle-harness` exists as a local branch only — zero commits beyond `develop`, never pushed, no PR.
- **Required next action (per A1 §6):** a single Contract PR must land the 8 docs (+ this audit = 9). Branch suggestion: `claude/w15-a7-contract-pr`. `W14_A6_*` gap must be resolved (author or explicitly defer) before that PR opens.

### 2.2 W15-A2 — `Images-GUI/` inventory

- 31 PNGs reconciled across `GUI_REFERENCE_MANIFEST.json`, README, `visual-targets.json`, W11-4 ledger, W14-A1, W15-A2 — **zero drift**.
- 5-way classification: **10 single-page · 11 collage · 1 theme board · 7 state board · 2 action-window board**.
- **11 collage images** total — each needs a `regions[]` crop map before per-region pixel diffs are possible. Top 5 by region count: `source-os-60-app-coverage-matrix.png` (~60), `source-os-core-categories.png` (~6), `source-os-remaining-categories.png` (~5), `settings-subtabs-all.png` (6), `primary-tabs-artifacts-approvals-plugins-roadmap.png` (4). Estimated total regions across the 11 collages: ~106.
- **6 of 31 PNGs (19.4%) are non-baseline dimensions** (5 distinct outlier PNGs, 2 distinct outlier shapes). Two are *live blocking* outliers in `04-source-os/`: `1672×941` (60-app matrix) and `1586×992` (remaining-categories). Per-target `viewport` override required.
- **Recommendation carried forward:** do NOT re-capture user-approved baselines; instead, normalise via per-target viewport in the manifest (matches W14-A1).

### 2.3 W15-A3 — Route / Component completeness

- **18 hash entry points** (17 in Sidebar + 1 `#health` shim). **240 unique backend handler paths.**
- 6-way classification roll-up: **14 FULLY_WIRED · 18 PARTIALLY_WIRED · 9 ORPHAN · 9 MOCK_ONLY · 4 MISSING_ROUTE · 4 MISSING_BACKEND.**
- **9 orphan tabs** live in `src/tabs/` but are not in `TAB_COMPONENTS` / `TAB_IDS` / `HASH_TO_TAB` / `TAB_TO_HASH`: `Workflows`, `PrintQueue`, `SystemLogs`, `Proof`, `BlenderMCP`, `Slicing`, `Fleet`, `PrinterControl`, `DockedApps`. Visiting their natural hash falls through to `UnavailableTab`.
- **4 missing routes:** `#notifications`, `#safety`, `#skills`, `#connectors`. The first two have working backend; the last two need backend too.
- **4 missing backend endpoints:** `/api/skills`, `/api/connectors`, `/api/settings/themes`, `/api/dashboard/layouts`.
- Settings (8 subtabs) and Voice (3 subtabs) are FULLY_WIRED at the data layer but **not URL-addressable** — `#settings/providers` and `#voice/transcripts` aren't honoured. Same fix shape on both: extend `tabIdFromHash` to keep the trailing segment.
- **60 Source OS apps:** 100% coverage at the route + endpoint layer (list, detail, run-proof, rollback, launch, modules-launch). Per-app visual fidelity not assessed here.

### 2.4 W15-A4 — Mock / fake / no-fake audit

- **30 hits total: 9 UNACCEPTABLE_FAKE · 15 HONEST_BLOCKED · 6 ACCEPTABLE_TEST_SEAM.**
- The 9 UNACCEPTABLE_FAKE findings are the 9 tab files listed in §3.1: each imports `MOCK_*` constants from `src/data/mock/*` and ships them as if they were live data.
- **Severity nuance:** the 9 fake tabs are NOT routed today (verified against `App.tsx:32-50` and `app/routes.ts`). They are tree-shaken from the production bundle. They remain UNACCEPTABLE_FAKE because (a) the files compile and import the canned constants, (b) the signatures match routed tabs and invite accidental wire-up, (c) the "Phase 2 mock-only" headers explicitly designate them as the v0 surface, (d) 11 mock-data files still co-ship in `data/mock/`.
- 15 HONEST_BLOCKED examples include `getLivePrinters` empty-array fallback, the `_INVALID_LICENSE_VALUES` validator, `_plan_llm_with_template_fallback` (real degrade with proof-ledger emission), and explicit "no fake content" comments in Autopilot / Observe / Design / Jobs / Gen3D consoles.
- **Top-5 ranked severity** (W15-A4 §6): UF-5 Proof (CRITICAL — fabricated cryptographic bundles), UF-3 PrinterControl (CRITICAL — safety-critical surface), UF-1 Fleet (HIGH — 12 fake printers on first paint), UF-2 PrintQueue + UF-6 Workflows (HIGH), UF-9 DockedApps (MEDIUM).
- **W15-A4 §6 recommended PR:** delete all 9 unrouted tab files + the 11 `data/mock/*.ts` files. Verify via the no-fake DOM scan on every routed URL.

### 2.5 W15-A5 — Visual-Oracle capability gaps

- Existing harness on `origin/develop`: 5 files / 1,048 LoC (`playwright.visual.config.ts`, `visual-targets.json`, `visual-proof.spec.ts`, `visual-proof-reporter.ts`, `global-setup.ts`).
- **1 of 10 capabilities present.** Missing: crop manifest (`regions[]` + `clip`), viewport overrides per target, console-error mandatory fail, network-404 fail, no-fake DOM scan, deterministic clock, theme determinism, `document.fonts.ready` await, region screenshots. Same root cause for several gaps: no manifest-driven per-target project / viewport / region loop.
- **W14-PR1 status:** NOT FOUND — never branched on origin, never opened.
- **~780 LoC of work** for Agent 9: 3 new files (`no-fake-scanner.ts`, `network-404-tracker.ts`, `_visual-helpers.ts`), 5 edited files (`playwright.visual.config.ts`, `visual-targets.json`, `visual-proof.spec.ts`, `visual-proof-reporter.ts`, `visual-targets.schema.json`).
- **Boot-time guards** required: reference-PNG dim mismatch, tolerance > max without rationale, outlier viewport without acknowledgement → all FAIL FAST.

### 2.6 Cross-cutting findings

1. **Orphan tab files == fake-data tab files (set equality).** See §3 for the overlap table; the 9 ORPHAN tabs are the same 9 UNACCEPTABLE_FAKE tabs. This converts a two-question problem into one decision: delete or wire.
2. **The Contract has not landed, but the Contract is what gates everything else.** W15-A1's NOT_LANDED verdict is the single biggest blocker — even GREEN PRs for Oracle and orphan-tab cleanup will lack the canonical reference document that defines pass/fail criteria. PR sequence (§5) puts the Contract PR first for that reason.
3. **Oracle gaps overlap A2 outliers and A2 collages.** W15-A5's missing capabilities `viewport overrides` and `regions[]` directly mirror W15-A2's 6 dimension-outlier PNGs and 11 collage region-count needs. A single oracle-implementation PR can address both surfaces, but the visual-targets manifest must be updated in lockstep.
4. **All 4 MISSING_BACKEND endpoints surface as visual artifacts.** `/api/skills`, `/api/connectors`, `/api/settings/themes`, `/api/dashboard/layouts` each correspond to specific reference PNGs: plugins-skills-mcp collage, theme-variants board, custom-dashboard state board. Visual-perfection cannot complete until backend is filled in.
5. **No paid services involved.** The audit chain stays within Playwright (open source), Sigstore / GitHub Attestations (free), GitHub Packages (free), and the local Playwright `webServer` (`scripts/start-e2e-stack.mjs`). Aligns with the user's STRICT 2026-05-03 no-paid-services rule.

---

## 3. Cross-cutting overlap — orphan tabs vs UNACCEPTABLE_FAKE tabs

**Headline finding: the 9 ORPHAN tabs from W15-A3 §1.2 and the 9 UNACCEPTABLE_FAKE tabs from W15-A4 §3 are the SAME 9 files (set equality).** This means the decision space is binary: delete every file, or wire every file. There is no orphan-but-honest tab to wire, and no fake-but-routed tab to fix in place.

| # | Tab file (path: `03_implementation/ui/src/tabs/`) | Natural hash | In W15-A3 §1.2 ORPHAN list? | In W15-A4 UNACCEPTABLE_FAKE list? | Live backend exists today? | Routed sibling that already shows real data |
|---:|---|---|---|---|---|---|
| 1 | `Workflows.tsx` | `#workflows` | YES | YES (UF-6) | YES — `/api/workflows` returns 200 | `tabs/Jobs.tsx` (`#jobs`) renders live workflow + queue data |
| 2 | `PrintQueue.tsx` | `#queue` | YES | YES (UF-2) | YES — `/api/jobs/*` (9 paths) | `tabs/Jobs.tsx` |
| 3 | `SystemLogs.tsx` | `#logs` | YES | YES (UF-7) | YES — `/api/logs` 200 | `tabs/Observe.tsx` (`#observe`) embeds log stream |
| 4 | `Proof.tsx` | `#proof` | YES | YES (UF-5) | YES — `/api/proof/bundles`, `/api/proof/events` 200 | `tabs/Artifacts.tsx` (`#artifacts`) renders real bundles via `getProofBundles()` |
| 5 | `BlenderMCP.tsx` | `#blender_mcp` | YES | YES (UF-8) | NO — no `/api/blender-mcp/*` (Source-OS card only) | `tabs/AppRegistry.tsx` / `tabs/SourceOS.tsx` show real `blender_mcp_candidates` |
| 6 | `Slicing.tsx` | `#slicing` | YES | YES (UF-4) | PARTIAL — no `/api/slicers`; `/api/printers` available | `tabs/Printers.tsx` (`#printers`) covers printer profiles |
| 7 | `Fleet.tsx` | `#fleet` | YES | YES (UF-1) | PARTIAL — `/api/printers/*` (18 paths) | `tabs/Printers.tsx` is the live fleet surface |
| 8 | `PrinterControl.tsx` | `#control` | YES | YES (UF-3) | PARTIAL — `/api/printers/{id}/move`, `/heat-bed`, `/heat-extruder`, `/safety-state` | `tabs/Printers.tsx` (with per-printer panel) |
| 9 | `DockedApps.tsx` | `#docked` | YES | YES (UF-9) | NO — no docked-apps endpoint | `tabs/AppRegistry.tsx` (`#apps`) shows real `/api/apps` payload |

**Overlap:** 9 / 9 (perfect set equality).

**Decision logic:** Every orphan-fake tab in the table above has a routed sibling that already renders real data. None of these tabs ships a unique feature surface; they are all v0 mock previews of capabilities that the routed sibling already handles. The user's no-fake principle + the standing merge authorization + the audit recommendations (W15-A3 §6.2 and W15-A4 §6) all converge on the same answer: **delete (preferred), do not wire.** See §6 for the per-tab justification of that decision.

---

## 4. Implementation sequence — Phase 2 / Phase 3 / Phase 4

Sequenced so the **Contract lands first** (it defines pass/fail for every subsequent PR), the **Oracle lands second** (it produces the proof artefacts), and code changes only begin in PR 3 after the audit doc, the test infrastructure, and the visual-target registry are all in place.

### Phase 2 — Foundations (Agents 7–10, all open in parallel after Contract PR opens)

| Agent | Lane | Deliverable | Depends on |
|---|---|---|---|
| **7** | Contract PR | Land the 8 W14 docs (+ this audit) on `origin/develop` via one DOCS_ONLY PR. Author or explicit-defer of `W14_A6_*`. | nothing (top of queue) |
| **8** | Visual Target Registry | Extend `visual-targets.json` from 31 entries → 31 entries with `viewport` per target + `regions[]` for the 11 collage PNGs + viewport overrides for the 5 outlier PNGs. Schema additions per W15-A5 §4 #2 and #8. | Agent 7 (Contract PR open; not required to be merged) |
| **9** | Playwright Oracle | Implement the 9 missing capabilities (W15-A5 §4): 3 new files + 5 edits, ~780 LoC. | Agent 7 + Agent 8 (registry must exist) |
| **10** | Oracle Reviewer | Run the new harness, produce the expected-RED report (failing diffs are the goal — they expose every gap that the implementation lanes must close in Phase 3). | Agent 9 (harness must be runnable) |

### Phase 3 — Implementation squads (Agents 11–20, run after Phase 2 completes)

| Agent | Lane | Touches |
|---|---|---|
| 11 | Header / sidebar / banners | `AppShell.tsx`, sidebar list, status banner host |
| 12 | Dashboard modes (Simple / Advanced / Custom) | `DashboardSimple.tsx`, `DashboardAdvanced.tsx`, `DashboardCustom.tsx`, `dashboardModeStore.ts`, new `/api/dashboard/layouts` |
| 13 | Source OS + 60 apps + categories | `SourceOS.tsx`, `AppRegistry.tsx`, `AppDetailPanel.tsx`, server-side `category` field |
| 14 | Artifacts / Approvals / Plugins / Roadmap | 4 routed tabs |
| 15 | Autopilot / Design / Gen3D / Jobs | 4 routed tabs (Action Window mount on Design + Autopilot) |
| 16 | Printers / Observe / Agents / Learning | 4 routed tabs |
| 17 | Settings + Theme palettes | `SettingsPage.tsx`, URL-addressable subtabs (`#settings/providers`), 6 theme tokens, `/api/settings/themes` |
| 18 | Voice subtabs URL-addressable | `Voice.tsx` (`#voice/browser`, `/transcripts`, `/proof`) |
| 19 | Action Window modes | `ActionWindow.tsx` (normal / maximized / detached), mount on every primary tab that needs it |
| 20 | Missing routes + missing backend | `#notifications` / `#safety` / `#skills` / `#connectors` pages + `/api/skills`, `/api/connectors`, `/api/settings/themes`, `/api/dashboard/layouts` |

### Phase 4 — Proof + walkthrough + final integrator (Agents 21–24)

| Agent | Lane | Deliverable |
|---|---|---|
| 21 | Visual perfection loop | Re-run Oracle, iterate on diffs, lock in green |
| 22 | E2E walkthrough | Playwright tour of all 17 routes at 1536×1024 + outliers; record session |
| 23 | Truth-gate sweep | Re-run no-fake DOM scan, console-error gate, 404 gate on every routed URL |
| 24 | Final integrator | Merge sequence, evidence ledger, final audit doc update |

---

## 5. PR-by-PR map (8-PR sequence)

Each PR maps to one or more Phase 2 / Phase 3 agents. The PR class column reflects standing merge authorization (auto-merge on green CI).

| PR | Class | Title (suggested) | Agent(s) | What it changes | Gates |
|---|---|---|---|---|---|
| **1** | DOCS_ONLY | `docs(handoffs): land W14 Visual Perfection Contract + W15 audits` | 7 | 8 W14 docs + this audit doc | truth-gate proof, no code lint |
| **2** | TEST_INFRA | `test(visual): land 9-capability Playwright oracle + extended target registry` | 8 + 9 | `visual-targets.json` + schema; 3 new oracle files; 5 oracle edits; ~780 LoC | unit + Playwright self-test must pass; oracle runs (failing diffs are expected — informational, gate is on harness compilation, schema validation, and reporter emission, not on diffs) |
| **3** | CODE_DELETE | `chore(ui): delete 9 unrouted Phase-2 mock-only tabs + data/mock dir (no-fake hardening)` | (no Phase 2 owner; Phase 3 chore) | Delete the 9 tab files + 11 `data/mock/*.ts` files + empty `data/mock/` dir | truth-gate, tsc, no-fake DOM scan on every routed URL |
| **4** | BACKEND + UI | `feat(ui+api): add #notifications, #safety, #skills, #connectors pages + 4 new endpoints` | 20 | 4 new routes; 4 new pages; 4 new backend handlers; lock together so route + endpoint land in one PR | unit + Playwright route smoke + endpoint contract tests |
| **5** | UI | `feat(ui): URL-addressable Settings + Voice subtabs (#settings/providers, #voice/transcripts ...)` | 17 + 18 | `tabIdFromHash` extension; `SettingsPage.tsx` + `Voice.tsx` segment routing; deep-link tests | Playwright deep-link spec for each of 8 + 3 subtabs |
| **6** | UI | `feat(ui): 6 theme palettes from reference (default / cyberpunk / matrix / tron / forge / aurora)` | 17 cont. | `theme/tokens.ts` palettes; `/api/settings/themes` catalog; `ThemeSwitcher` integration | Playwright theme diff against `09-themes/theme-variants-reference.png` |
| **7** | UI | `feat(ui): Source OS 60-app coverage + Action Window normal/maximized/detached on all primary tabs` | 13 + 19 | `SourceOS.tsx` category data, server-side `category` field, `ActionWindow` mount across Design / Autopilot / Jobs | Playwright per-app card + Action Window mode tests |
| **8** | CI + DOC | `chore(ci): visual perfection loop — close green; final E2E ledger` | 21–24 (Phase 4) | Oracle iteration loop, walkthrough recording, final ledger update | every Phase 3 diff must be green at the configured tolerance |

PRs 1 → 2 → 3 are strictly ordered (each depends on the prior). PRs 4 → 5 → 6 → 7 can fan out in parallel after PR 3 lands. PR 8 is final and depends on all preceding.

---

## 6. Decision — delete vs wire the 9 fake tabs

**Recommendation: DELETE all 9 fake tab files + the 11 `data/mock/*.ts` files + the empty `data/mock/` directory.** Match W15-A4 §6's "Recommended single-PR shape" and W15-A3 §6.2's gap analysis. Per-tab justification:

| Tab | Decision | Rationale | Routed sibling that already serves the user's intent |
|---|---|---|---|
| `Workflows.tsx` | DELETE | Jobs is the live workflow surface; `Jobs.tsx` reads `/api/workflows` honestly. | `tabs/Jobs.tsx` (`#jobs`) — uses `getActiveWorkflows()` + `getJobs()`. |
| `PrintQueue.tsx` | DELETE | Jobs already shows the print queue from `/api/jobs/*`. | `tabs/Jobs.tsx` (`#jobs`). |
| `SystemLogs.tsx` | DELETE | Observe embeds the live log stream from `/api/logs`. | `tabs/Observe.tsx` (`#observe`). |
| `Proof.tsx` | DELETE | Artifacts shows real proof bundles via `getProofBundles()`; fabricated bundle IDs / gate verdicts are an OWASP A09 violation. | `tabs/Artifacts.tsx` (`#artifacts`). |
| `BlenderMCP.tsx` | DELETE | No backend exists; the Source OS card already exposes Blender MCP candidates with real install / health data. | `tabs/SourceOS.tsx` / `tabs/AppRegistry.tsx` — `blender_mcp_candidates` app id. |
| `Slicing.tsx` | DELETE | Slicing is owned by Printers and the per-printer panel; canned slicer registry is fake. | `tabs/Printers.tsx` (`#printers`). |
| `Fleet.tsx` | DELETE | Printers is the live fleet surface; 12 canned printers on first paint actively misrepresents fleet state. | `tabs/Printers.tsx` (`#printers`). |
| `PrinterControl.tsx` | DELETE | Safety-critical; MOCK_PRINTERS-seeded selector means jog/temp could attach to a fake target. Printers has per-printer control panels with real `/api/printers/{id}/*` writes. | `tabs/Printers.tsx` per-printer panel. |
| `DockedApps.tsx` | DELETE | Hardcoded host IPs presented with `state: "available"`; AppRegistry shows the real `/api/apps` payload (60 apps). | `tabs/AppRegistry.tsx` (`#apps`). |

**Why not wire instead?** Even for the tabs whose backend exists (Workflows / PrintQueue / SystemLogs / Proof), wiring would create a duplicate surface for capabilities that the routed sibling already handles. That fragments user mental model and doubles the maintenance + visual-test surface. The cost of deleting is small (each is dead code today; deletion is a single squash-merge with the truth-gate as the only guard). The cost of wiring is large (each requires its own visual target, its own oracle run, its own truth-gate proof). Apply YAGNI: delete now, restore from history if a future product decision actually wants a separate Fleet / Slicing / Proof page.

**Boundary:** if Phase 3 Agent 20 finds that one of the deleted tabs maps cleanly to a `#notifications` / `#safety` / `#skills` / `#connectors` page (e.g. PrinterControl ↔ `#safety`), Agent 20 may **recreate the file from scratch** with live data, in PR 4. Recreation-from-scratch is acceptable; **re-importing the deleted file is not** because the canned data goes with it.

---

## 7. Mandatory next-action queue

Strict serial ordering — items 1 → 2 → 3 cannot parallelise; items 4–9 fan out from item 3:

1. **Open PR 1 (Contract docs)** via Phase 2 Agent 7. Top of queue. Branch suggestion: `claude/w15-a7-contract-pr`. Includes 8 W14 docs + this audit + explicit defer note for `W14_A6_*` (or W14_A6_* author result if added).
2. **In parallel with PR 1 CI**: open PR 2 (Visual Target Registry + Oracle harness) via Phase 2 Agents 8 + 9. PR 2 may not merge until PR 1 merges (depends on the Contract being canonical on `develop`). But the work can be in flight.
3. **Run Phase 2 Agent 10 (Oracle Reviewer)** as soon as PR 2 is mergeable. The expected-RED report from this agent becomes the punch list for Phase 3.
4. **Open PR 3 (delete the 9 fake tabs + 11 mock data files)** as soon as PR 2 lands and Agent 10's report exists. Single squash-merge.
5. **Fan out PRs 4 / 5 / 6 / 7** in parallel after PR 3.
6. **PR 8 (final loop + ledger)** depends on all Phase 3 PRs.
7. **Throughout:** keep `hermes3d-locks` reachable, re-acquire locks per agent, never skip a lane, fix every weakness — no AI slop, no audit-and-skip.
8. **`W14_A6_*` gap** — orchestrator must decide before PR 1: author it or explicitly defer with a rationale appended to this audit.
9. **Hermes Agent v0.13.0 update lane** remains separate (per project memory `project_hermes_agent_v013_pending.md`) — do not bundle.

---

## 8. Sources

This synthesis cites two sources, in line with the user's contract and the Wave-15 spec:

1. **Official — ISTQB Glossary + ISO/IEC 25010:2011 Software Quality Model.** The 5-verdict executive matrix in §1 aligns with ISO 25010's functional-suitability + usability + reliability + maintainability + portability characteristics, mapped onto a GUI domain: `GUI_FUNCTIONAL_GREEN` corresponds to functional suitability (function completeness + function correctness); `GUI_VISUAL_CONTRACT_LANDED` corresponds to maintainability (modifiability + testability — the contract document is the spec the test harness validates against); `GUI_VISUAL_ORACLE_LANDED` corresponds to reliability + testability; `GUI_PIXEL_PERFECT` corresponds to usability (accessibility + user-interface aesthetics) under the strict no-drift contract; `GUI_E2E_COMPLETE` is the composite. ISTQB's "test oracle" terminology (the mechanism by which a test verifies expected vs actual outcome) is the formal name for the Playwright harness W14-A3 designed; the 1-of-10 capability score in W15-A5 §2 is the oracle-coverage score in ISTQB terms. References: <https://www.iso.org/standard/35733.html> (ISO/IEC 25010:2011), <https://glossary.istqb.org/en_US/term/test-oracle-1> (ISTQB test oracle).
2. **Cross-project — Storybook + Chromatic visual-regression conventions.** Chromatic's published harness pattern (one story = one snapshot; per-story viewport; `fontsReady` await; deterministic clock injection; console-error budget = 0; network 404 = automatic failure; per-region screenshots for composite stories) is the same pattern W14-A3 specified for this repo and is the gap framework W15-A5 used to score capabilities. The 11-collage region-map work in §4 of this audit is the analogue of Chromatic's "story composition" pattern (a single story exposing multiple component states, each diffable independently). Storybook's visual-testing docs reinforce the 1-target-per-state convention. References: <https://www.chromatic.com/docs/visual-tests/>, <https://storybook.js.org/docs/writing-tests/visual-testing>.

Supporting artefacts not counted as primary sources but cited throughout this synthesis: the five W15 sibling audits (W15-A1 through W15-A5); `GUI_REFERENCE_MANIFEST.json`; `Images-GUI/README.md`; `visual-targets.json`; the prior W14-A1 / W14-A2 / W14-A3 / W14-A4 / W14-A5 designs.

---

## 9. Constraint compliance

- **READ-ONLY synthesis** — no source files were modified; the only new artefact is this audit document.
- **Lock acquired** under `claude-w15-a6-integrator` for this file before write; will release at handoff.
- **2 sources cited** per Wave-15 spec (one official ISO 25010 / ISTQB, one cross-project Storybook / Chromatic).
- **Doc length** — within the 2500–4000 word target.
- **No paid services**, no secrets, no `G:\private\` reads, no Hermes Agent v0.13.0 lane bundled in.
- **Hermes3D MCP reachable** throughout the audit (lock acquisition succeeded; lock-id `b24fc8239f413789be48ee22`).
- **No source code edits** in this lane — all wiring / deletion / oracle changes belong to subsequent PRs per §5.

---

## 10. Summary table — 5-verdict snapshot

| Verdict | Value | One-line proof |
|---|---|---|
| GUI_FUNCTIONAL_GREEN | GREEN | 14 FULLY_WIRED + 18 PARTIALLY_WIRED routes, no fake data in the production bundle. |
| GUI_VISUAL_CONTRACT_LANDED | NOT_LANDED | 0 of 8 W14 docs on `origin/develop`; W14_A6 missing entirely. |
| GUI_VISUAL_ORACLE_LANDED | PARTIAL | 1 of 10 oracle capabilities present; 9 gaps specified line-by-line in W14-A3. |
| GUI_PIXEL_PERFECT | RED | Cannot be measured until oracle is GREEN + targets cover all 11 collages and 5 outliers. |
| GUI_E2E_COMPLETE | RED | 1 of 5 verdicts green; 3 of 5 blocked; 1 explicitly deferred. |

**End of canonical Wave-15 GUI Incomplete-E2E audit. Lock will be released by the integrator at handoff.**
