# HANDOFF_TO_CODEX — Phase 5.1 wrap + Release / Deploy / Backup infrastructure

> **Status:** READY for Codex pickup. PR #23 (CP5.1-C) is open and Claude will review/merge it. This handoff covers the FOUR remaining bundles to ship Hermes3D-OS as a real product:
>
> 1. **B1 — CP5.1-E:** Phase 5.1 completion report (proof bundle + acceptance gates)
> 2. **B2 — WINREL-MVP:** Windows release infrastructure (PyInstaller + Velopack + GH Releases workflow)
> 3. **B3 — VPS-DEPLOY:** Hostinger VPS deployment bundle (Caddy + Docker Compose + Tailscale docs)
> 4. **B4 — LOCAL-BACKUP:** Local-only secrets backup scripts (Syncthing + Restic→B2)
>
> All four bundles are **scope-disjoint** — each touches a distinct file set. Codex may claim and ship them sequentially via the HermesProof v0.5 task queue. Total estimated work: 4-6 hours of Codex + Claude review.

---

## 0. Pre-flight (every session start)

```text
hermes_doctor                         confirm ok=true
hermes_read_policy                    confirm workspace=G:\Github\Hermes3D
hermes_get_state                      sanity check: no codex-impl-* locks pending
```

Branch base for ALL bundles: `develop` (after PR #23 merges) or `feat/phase-5-1-cp-c-profile-generator-and-doctor` (if PR #23 still open and you want to stack).

Owner string for ALL bundles: `codex-impl-03` (NOT `-01` or `-02` — those are reserved for prior CPs to keep HermesProof state clean).

---

## Bundle B1 — CP5.1-E (Phase 5.1 completion report)

### B1.1 Mission

Aggregate evidence from CP5.1-A (plan + ADR), CP5.1-B (failure_predictor + backup), CP5.1-C (profile_generator + skill_store + doctor JSON), CP5.1-D (Gradio smoke + matrix coverage) into a single completion report and proof bundle that closes Phase 5.1.

Mirror the shape of `00_overview/PHASE3_4_COMPLETION_REPORT.md`.

### B1.2 Claim

```text
hermes_pick_task
  owner=codex-impl-03
  prefer_task_id=H3D-CP5.1-E
```

If queue is empty (task wasn't enqueued):

```text
hermes_claim_task
  owner=codex-impl-03
  taskId=H3D-CP5.1-E
  role=implementation
  title=CP5.1-E: Phase 5.1 completion report + proof bundle
  reason=Wrap Phase 5.1 per PHASE5_1_PLAN.md §5 acceptance gates. Aggregates A/B/C/D evidence into single shippable artifact.
```

### B1.3 Branch

`feat/phase-5-1-cp-e-completion-report` from `develop` (after PR #23 lands) — or stack on `feat/phase-5-1-cp-c-profile-generator-and-doctor` if PR #23 is still open.

### B1.4 Lock these exact 4 files

```text
hermes_lock_files
  owner=codex-impl-03
  taskId=H3D-CP5.1-E
  ttlMinutes=90
  files=[
    "00_overview/PHASE5_1_COMPLETION_REPORT.md",
    "00_overview/contract/HONESTY_LEDGER.md",
    "00_overview/contract/ROADMAP.md",
    "scripts/scaffolding/_build_phase_proof.py"
  ]
```

### B1.5 Implementation contract

**`00_overview/PHASE5_1_COMPLETION_REPORT.md`** (NEW) — mirror `PHASE3_4_COMPLETION_REPORT.md` shape:
- Header: title, version (v5.1.0), date, owner
- §1 Summary — 3-5 paragraphs: what shipped, what didn't, why
- §2 Checkpoints — table: A/B/C/D with PR #s, commit SHAs, brief description
- §3 Acceptance gates per `PHASE5_1_PLAN.md §5` — table with status (PASS/FAIL/SKIPPED), evidence link
- §4 Truth-gate evidence — list every CI Layer (A/B/C/D/D3/E/F/M/T/W) with its current pass-rate on develop
- §5 Honesty ledger updates — what claims were promoted from "advisory" to "gated"
- §6 What didn't ship — explicit list of deferrals (e.g., Layer D3 still non-blocking)
- §7 Next phase — pointer to v5.2 / v6.0 ROADMAP

**`00_overview/contract/HONESTY_LEDGER.md`** — append rows for any Phase 5.1 claims that became real (failure_predictor real, backup scheduler real, profile_generator skill-aware real, doctor JSON envelope real).

**`00_overview/contract/ROADMAP.md`** — mark Phase 5.1 row as `✅ shipped v5.1.0` with completion date.

**`scripts/scaffolding/_build_phase_proof.py`** (NEW or extension of existing) — script that emits `00_overview/proofs/phase_5_1_proof.json` aggregating all CP evidence (commit SHAs, test counts, gate results). Pattern mirrors `02_architecture/scripts/scaffolding/phase3_4_proof.py`.

### B1.6 Tests

No new tests required. The completion report itself is the artifact.

### B1.7 Gates

```text
hermes_run_gate gateId=git-status      cwd=.
hermes_run_gate gateId=git-diff-check  cwd=.
```

Local:
- `python scripts/scaffolding/_build_phase_proof.py --phase 5.1` emits valid JSON
- `python -m json.tool 00_overview/proofs/phase_5_1_proof.json` round-trips clean
- All existing tests still pass: `pytest -q` (full suite, expected ~670 pass)

### B1.8 PR

```bash
git push -u origin feat/phase-5-1-cp-e-completion-report
gh pr create --base develop \
  --title "Phase 5.1 — CP5.1-E: completion report + proof bundle" \
  --body "[mirror CP3.4-E PR body shape; Hermes evidence chain: PASS; Task: H3D-CP5.1-E; Gate run via hermes_run_gate: git-status PASS, git-diff-check PASS]"
```

### B1.9 Close-out

```text
hermes_append_evidence  owner=codex-impl-03  taskId=H3D-CP5.1-E  kind=checkpoint  summary=Phase 5.1 closed; PR #N at SHA <commit>
hermes_release_files    owner=codex-impl-03  files=[the 4 above]
hermes_release_task     owner=codex-impl-03  taskId=H3D-CP5.1-E
```

---

## Bundle B2 — WINREL-MVP (Windows release infrastructure)

### B2.1 Mission

Add the smallest delta to ship a real Windows binary on GitHub Releases, unsigned for now. Stack: PyInstaller + Velopack. Code signing is deferred to a follow-up bundle (B2-SIGN, separate task).

This is "Phase 5A — Unsigned MVP" from the master plan. Reference: research bundle `aed53268cc604670e` (Windows distribution audit) and `a70b4b9276d2ccd85` (existing release infra audit).

### B2.2 Claim

```text
hermes_pick_task
  owner=codex-impl-03
  prefer_task_id=H3D-WINREL-MVP
```

Or fallback claim with `taskId=H3D-WINREL-MVP`, `title=Windows release MVP — PyInstaller + Velopack + GH Releases workflow`, `reason=Smallest delta to ship a real .exe on every v* tag. Unsigned MVP first; signing follows in B2-SIGN.`

### B2.3 Branch

`feat/release-windows-mvp` from `develop`.

### B2.4 Lock these exact 5 files

```text
hermes_lock_files
  owner=codex-impl-03
  taskId=H3D-WINREL-MVP
  ttlMinutes=120
  files=[
    "requirements-dev.txt",
    "03_implementation/src/hermes3d/app/launcher.py",
    "scripts/build/windows_pack.ps1",
    ".github/workflows/release-windows.yml",
    "06_release/README.md"
  ]
```

`scripts/build/windows_pack.ps1` and `.github/workflows/release-windows.yml` are NEW files. The other three are MODIFIED.

### B2.5 Implementation contract

**`requirements-dev.txt`** — append:
```
pyinstaller>=6.10,<7
velopack>=0.0.1052,<1
```

**`03_implementation/src/hermes3d/app/launcher.py`** — wrap the existing `if __name__ == "__main__":` entrypoint with `velopack.App().run()` if and only if `velopack` is importable. Soft-import pattern (don't break existing run-from-source workflow):

```python
def _maybe_init_velopack():
    try:
        import velopack
    except ImportError:
        return  # running from source / dev mode
    velopack.App().run()  # no-op if not in a Velopack-packed bundle

# at top of __main__ block, BEFORE Gradio launch:
_maybe_init_velopack()
```

Add an `UpdateManager.checkForUpdates()` call gated on `HERMES3D_AUTO_UPDATE=1` env var (default off, opt-in). Keep the existing CLI argparse + Gradio launch path unchanged — Velopack is purely additive.

**`scripts/build/windows_pack.ps1`** (NEW) — PowerShell script for local + CI Windows packaging:
```powershell
# Phase 1: PyInstaller --onedir bundle
pyinstaller --onedir `
  --name=Hermes3D `
  --paths=03_implementation/src `
  --collect-all=hermes3d `
  --collect-all=gradio `
  --collect-all=trimesh `
  --hidden-import=manifold3d `
  --hidden-import=rtree `
  --noconfirm `
  --distpath=dist/win `
  03_implementation/src/hermes3d/app/launcher.py

# Phase 2: Velopack pack
$tag = if ($env:GITHUB_REF_NAME) { $env:GITHUB_REF_NAME -replace '^v', '' } else { '0.0.0-dev' }
vpk pack `
  --packId=Hermes3D-OS `
  --packVersion=$tag `
  --packDir=dist/win/Hermes3D `
  --mainExe=Hermes3D.exe `
  --outputDir=dist/release-win
```

**`.github/workflows/release-windows.yml`** (NEW) — trigger on `v*` tags, build on `windows-latest`, run windows_pack.ps1, attest SBOM via `actions/attest-sbom@v2` (CycloneDX), Sigstore-sign via existing OIDC pattern, upload artifacts to the GitHub Release. Mirror `.github/workflows/ci.yml` Layer E shape but for actual binary build, not dry-run.

Critical: must use `permissions: contents: write, id-token: write, attestations: write` for the Sigstore + attest-sbom calls to work without secrets.

**`06_release/README.md`** — add a "Windows binaries" section pointing at the GitHub Releases page, explain Velopack auto-update opt-in (`HERMES3D_AUTO_UPDATE=1`), reference the SBOM and Sigstore artifacts.

### B2.6 Tests

Smoke test: `node --check` equivalent for PowerShell — `pwsh -NoProfile -Command "& { $ErrorActionPreference='Stop'; . ./scripts/build/windows_pack.ps1 -WhatIf }"` (parses and confirms no syntax errors). Add as Layer E2 step in `.github/workflows/ci.yml` (advisory, not gating).

DO NOT add a real "build a wheel and run it" CI step — that's a regression risk for non-release commits. The release-windows.yml workflow is gated on `v*` tags, so it runs only when a release is cut.

### B2.7 Gates

- `hermes_run_gate gateId=git-status cwd=.` PASS
- `hermes_run_gate gateId=git-diff-check cwd=.` PASS
- `pwsh -NoProfile -Command "Test-Path scripts/build/windows_pack.ps1"` returns True
- `gh workflow list -R Ghenghis/Hermes3D` shows new "Release — Windows" workflow
- All existing tests still pass: `pytest -q`

### B2.8 PR + close-out

Same shape as B1. PR title: `feat(release): Windows binary MVP — PyInstaller + Velopack + GH Releases workflow`.

### B2.9 Hard rules

- DO NOT add code signing in this bundle. That's a separate `H3D-WINREL-SIGN` task once the user signs up for Azure Artifact Signing.
- DO NOT touch `pyproject.toml` console-scripts entries — Velopack wraps the existing entrypoint, doesn't replace it.
- DO NOT bundle `04_testing/` or `02_architecture/` into the PyInstaller output — those are dev-only.
- DO NOT modify the existing `scripts/scaffolding/release.sh` or Layer E in `ci.yml` — keep those for source-zip releases.

---

## Bundle B3 — VPS-DEPLOY (Hostinger VPS deployment bundle)

### B3.1 Mission

Ship a turnkey deployment bundle for hosting Hermes3D on a Hostinger VPS while keeping LLM inference on the user's local machine. Topology: Caddy 2.8 (auto-SSL) → Gradio + FastAPI on VPS, calling out to user's local Ollama via Tailscale tailnet. No public LLM endpoint, no port forwarding.

Reference: research bundle `a8450c4a4b74765d5` (Hostinger VPS topology). The blueprint is opinionated — implement it as stated, defer flexibility to v6.

### B3.2 Claim

```text
hermes_pick_task
  owner=codex-impl-03
  prefer_task_id=H3D-VPS-DEPLOY
```

Fallback: `title=VPS deployment bundle — Caddy + Compose + Tailscale + Restic-B2`, `reason=Per-master-plan Phase 6: VPS hosts public UI, local PC hosts inference, Tailscale connects them, Restic backs up VPS to B2.`

### B3.3 Branch

`feat/deploy-vps-bundle` from `develop`.

### B3.4 Lock these exact 7 files

```text
hermes_lock_files
  owner=codex-impl-03
  taskId=H3D-VPS-DEPLOY
  ttlMinutes=90
  files=[
    "06_release/deploy/vps/docker-compose.yml",
    "06_release/deploy/vps/Caddyfile",
    "06_release/deploy/vps/restic-backup.sh",
    "06_release/deploy/vps/restic-backup.timer.conf",
    "06_release/deploy/vps/.env.vps.example",
    "06_release/deploy/local/tailscale-setup.md",
    "06_release/deploy/README.md"
  ]
```

ALL files are NEW.

### B3.5 Implementation contract

**`06_release/deploy/vps/docker-compose.yml`** — services:
- `caddy:2.8-alpine` exposing :80 + :443, mounting `./Caddyfile`, `caddy_data` + `caddy_config` volumes
- `hermes3d` (build from `Dockerfile.vps` referencing `pip install hermes3d-os` from the GH Release wheel — explicit version pin, not `latest`), exposing :7860 (Gradio) and :8000 (FastAPI), reading `.env`, depending on postgres + redis + tailscale-sidecar
- `postgres:16-alpine` for jobs/queue, named volume `hermes_pg_data`
- `redis:7-alpine` for locks + ephemeral state
- `tailscale/tailscale:latest` as a sidecar with `TS_AUTHKEY` from env, advertising routes to local LLM host

Do NOT bake any user-specific config into the compose file. ALL hostnames, auth tokens, IP ranges go in `.env.vps.example` for the user to copy + customize on their VPS.

**`06_release/deploy/vps/Caddyfile`** — single domain block:
```
{$HERMES_PUBLIC_DOMAIN} {
    encode zstd gzip
    @gradio path / /assets/* /file=*
    handle @gradio { reverse_proxy hermes3d:7860 }
    handle /api/* { reverse_proxy hermes3d:8000 }
    handle_errors { respond "Hermes3D is starting..." 503 }
    log { output file /var/log/caddy/access.log }
}
```

WebSocket pass-through is implicit in Caddy's reverse_proxy.

**`06_release/deploy/vps/restic-backup.sh`** — Restic snapshot script: backs up `/var/lib/docker/volumes/hermes_*` + `/etc/hermes` to Backblaze B2, retention 7d/4w/12m, repo init handled idempotently. `B2_ACCOUNT_ID` + `B2_ACCOUNT_KEY` + `RESTIC_PASSWORD` from env.

**`06_release/deploy/vps/restic-backup.timer.conf`** — systemd timer + service unit pair (Type=oneshot), running `restic-backup.sh` nightly at 03:30 UTC.

**`06_release/deploy/vps/.env.vps.example`** — documented env file with EVERY variable the compose stack expects: `HERMES_PUBLIC_DOMAIN`, `OLLAMA_BASE_URL` (Tailscale-resolved hostname), `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `HERMES3D_PROOF_KEY`, `TS_AUTHKEY`, `B2_ACCOUNT_ID`, `B2_ACCOUNT_KEY`, `RESTIC_PASSWORD`, `RESTIC_REPOSITORY`. Comment EACH variable. NO actual values — placeholders only.

**`06_release/deploy/local/tailscale-setup.md`** — step-by-step for the user's gaming PC:
1. Install Tailscale on Windows
2. Authenticate as the same tailnet as the VPS
3. Install Ollama 0.5+, set `OLLAMA_HOST=0.0.0.0:11434`, restart
4. Verify VPS can reach `http://gaming-pc.tailnet-name.ts.net:11434/api/tags`
5. Tailscale ACL JSON snippet showing `tag:vps → tag:llm-host:11434` only (rest blocked)

**`06_release/deploy/README.md`** — overview, quick-start, security notes (no port forwarding, basic-auth on Caddy in front of Gradio recommended), troubleshooting, restore-from-backup procedure.

### B3.6 Tests

- `docker compose -f 06_release/deploy/vps/docker-compose.yml config` parses without error (CI step, ubuntu-latest)
- `caddy validate --config 06_release/deploy/vps/Caddyfile --adapter caddyfile` passes (CI step)
- `bash -n 06_release/deploy/vps/restic-backup.sh` — syntax check
- `python -c "import yaml; yaml.safe_load(open('06_release/deploy/vps/docker-compose.yml'))"` — YAML valid

Add as a new optional CI job `layer_v_vps_deploy_lint` (advisory, ubuntu-latest, runs on PR open). Non-gating.

### B3.7 Gates + close-out

Same shape as B1/B2. PR title: `feat(deploy): Hostinger VPS bundle — Caddy + Compose + Tailscale + Restic-B2`.

### B3.8 Hard rules

- DO NOT bundle any actual auth tokens, IPs, hostnames, or `B2_ACCOUNT_*` values. The .env.vps.example is templates only.
- DO NOT pin to `caddy:latest`, `postgres:latest`, etc. Pin every image tag explicitly.
- DO NOT use Cloudflare Tunnel for the inference path. Tailscale is the chosen mesh per master plan.
- DO NOT enable Caddy admin API (`localhost:2019`) — disable explicitly.

---

## Bundle B4 — LOCAL-BACKUP (User's local-only secrets backup)

### B4.1 Mission

Ship the local-side backup story to complement B3. User's `.env`, `printers.user.toml`, model paths, and any other private state get replicated via Syncthing to a NAS + offsite to Backblaze B2 via Restic. NEVER touches GitHub.

Reference: research bundles `ae15989b4ad7c56a5` (config audit verdict GREEN) and `a8450c4a4b74765d5` (B2 + Syncthing pattern).

### B4.2 Claim

```text
hermes_pick_task
  owner=codex-impl-03
  prefer_task_id=H3D-LOCAL-BACKUP
```

Fallback: `title=Local-only secrets backup — Syncthing + Restic-B2 scripts`, `reason=Master plan Phase 7. .env + printers.user.toml + model metadata never touch GitHub; replicated to NAS + B2 nightly.`

### B4.3 Branch

`feat/local-secrets-backup` from `develop`.

### B4.4 Lock these exact 4 files

```text
hermes_lock_files
  owner=codex-impl-03
  taskId=H3D-LOCAL-BACKUP
  ttlMinutes=60
  files=[
    "06_release/backup/syncthing-share-template.md",
    "06_release/backup/restic-backup.ps1",
    "06_release/backup/restic-restore.ps1",
    "06_release/backup/README.md"
  ]
```

ALL files are NEW.

### B4.5 Implementation contract

**`06_release/backup/syncthing-share-template.md`** — step-by-step for setting up a Syncthing share covering: `.env`, `03_implementation/config/printers.user.toml`, `~/.hermes3d/` (if exists), and `~/AppData/Roaming/Hermes3D/` (Windows). Recipient: a NAS or second PC. Send-only mode from the dev machine. Versioning: staggered (5 versions × 1d, 4 × 7d, 4 × 30d).

**`06_release/backup/restic-backup.ps1`** — Windows scheduled-task script. Backs up the same paths as the Syncthing share to a Backblaze B2 bucket. Pulls credentials from a separate `~/.hermes3d/restic-env.ps1` file (NOT in repo, NOT in Syncthing share — restoration credentials only). Pattern:
```powershell
# Read env from ~/.hermes3d/restic-env.ps1 (gitignored, separate)
. $HOME\.hermes3d\restic-env.ps1
restic backup `
  $HOME\.env `
  $HOME\AppData\Roaming\Hermes3D `
  G:\Github\Hermes3D\03_implementation\config\printers.user.toml `
  --tag local-secrets `
  --exclude-caches
restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 12 --prune
```

Hard rule: this script MUST NOT be runnable without the separate restic-env.ps1 — fail loudly if missing.

**`06_release/backup/restic-restore.ps1`** — restoration script. Lists snapshots, prompts for snapshot ID, restores to a specified path (NOT the live location, to prevent overwrite accidents).

**`06_release/backup/README.md`** — operator guide:
- What gets backed up + why
- One-time setup: Syncthing config, B2 bucket, Restic init
- Schedule: nightly via Windows Task Scheduler (template XML included)
- Restoration drill: steps to test recovery quarterly
- DR scenario: full machine loss → restore from B2

### B4.6 Tests

- `pwsh -NoProfile -Command "& { . ./06_release/backup/restic-backup.ps1 -WhatIf }"` — parses without error (will exit 1 on missing restic-env, expected)
- `Test-Path 06_release/backup/syncthing-share-template.md`

Advisory, no CI gate.

### B4.7 Gates + close-out

Same shape as B1/B2/B3. PR title: `feat(backup): local-only secrets backup — Syncthing + Restic-B2 scripts`.

### B4.8 Hard rules

- DO NOT include any actual B2 credentials, bucket names, or paths to actual private files.
- DO NOT reference any specific NAS hostname or model.
- DO NOT bundle sample `.env` content. Templates only.

---

## Cross-bundle hard rules

1. Each bundle's PR is independent. Codex MUST NOT chain bundles in a single PR.
2. Each bundle uses owner `codex-impl-03`. Each bundle has its own task ID. Release locks + task at the end of each bundle before claiming the next.
3. NO bundle modifies the same file. The 4 lock lists are scope-disjoint by design.
4. NO bundle touches `04_testing/playwright/`, `.github/workflows/ci.yml`, `pyproject.toml` (except B2.5 documented additions), or any file owned by Phase 5.1 CPs A/B/C/D.
5. Each bundle MUST pass `hermes_run_gate gateId=git-status` and `git-diff-check` before push.
6. Each bundle's evidence chain MUST report PASS via `hermes_verify_evidence`.

## Failure protocol (per bundle)

If blocked at any point, write `handoffs/HANDOFF_TO_CLAUDE_<TASKID>_BLOCKED.md`:
- Branch + tip SHA
- Locks held at block time
- Files attempted, succeeded, unchanged
- Last 50 lines of error output
- Suggested fix or open question
- HermesProof evidence id

Then release locks + task, append evidence with `kind=block`, stop. Do not push partial work.

## Sequencing recommendation

Order: **B1 → B2 → B3 → B4**.

Rationale:
- B1 closes Phase 5.1 cleanly (smallest change, highest doc value, lowest risk)
- B2 ships the first real Windows binary (highest user-visible value)
- B3 is the deploy bundle (logical extension of having a binary)
- B4 is the smallest in scope (purely local docs + scripts, can ship anytime)

If Codex hits a blocker on B2 or B3, B4 is always shippable independently.

## References

- Master plan: this conversation's "Hermes3D — Master Arc Plan" message
- Research bundles (HermesProof tasks dir): `aed53268cc604670e` (Windows dist), `a70b4b9276d2ccd85` (release infra audit), `a8450c4a4b74765d5` (VPS topology), `ae15989b4ad7c56a5` (config audit GREEN)
- Prior CP completion shape: `00_overview/PHASE3_4_COMPLETION_REPORT.md`

## Architect contact

If any spec is ambiguous, write `handoffs/HANDOFF_TO_CLAUDE_<TASKID>_CLARIFY.md` quoting the section. Claude (`owner=claude-lead`) will respond with a path-fix-style mini-PR if needed.
