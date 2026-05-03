# Hermes3D v5.3.0 Release Notes

Status: draft for review — do not tag or publish from this file.
Target branch: `develop` → release candidate branch → user-authorized release.
Last updated: 2026-05-03.

## Summary

Hermes3D v5.3.0 is the first release candidate track for the Contract Kit after
the Phase 5.1 hardening sweep. It combines the previously shipped Contract Kit
foundation with operational evidence, Windows packaging, local/VPS backup
templates, and a clearer release/documentation surface.

The release remains local-first. No cloud account is required, no release step
reads private `.env` files from the repository, and secrets remain outside Git
under the user's launcher or `HERMES3D_ENV_FILE` convention.

## Highlights

- Phase 5.1 hardening is complete: print history now feeds the failure
  predictor, backups run through an opt-in scheduler tick, profile generation can
  read skill-store context, and doctor scripts emit versioned JSON.
- CI is broader: Windows and Ubuntu are both covered across Python 3.11 and
  3.12, with matrix-completeness checks and the advisory Gradio launcher smoke.
- Windows release infrastructure exists: PyInstaller onedir packaging,
  Velopack wrapping, SBOM generation, and Sigstore keyless signing are wired for
  `v*` tag workflows.
- Deployment docs are in place for Hostinger-style VPS hosting with Caddy,
  Docker Compose, Tailscale, and Restic-B2 backup templates.
- Local secret-backup docs and scripts are in place for Syncthing plus Restic-B2
  without committing operator secrets.
- Marketing/docs surfaces were refreshed with a first GitHub Pages landing page
  and the v5.3 release infrastructure references.
- ADR-014 rejects adopting `rakaarwaky/blender-mcp-native` for now, preserving
  the current adapter boundary until a safer Blender integration is justified.

## What Changed Since v5.1.0

| Area | Evidence | Notes |
|---|---|---|
| Phase 5.1 closeout | PR #26 | Completion report and proof JSON committed. |
| Windows release MVP | PR #28 | `Release - Windows` workflow, `windows_pack.ps1`, launcher updates, release README. |
| VPS deploy bundle | PR #29 | Caddy, Compose, Tailscale setup notes, Restic-B2 systemd timer templates. |
| Local backup bundle | PR #30 | Syncthing ignore template, Restic PowerShell backup/restore helpers, backup README. |
| Marketing site v1 | PR #25 | Static site, SVG assets, GitHub Pages workflow. |
| SOTA marketing brief | PR #27 | Design/README follow-up brief, not final product code. |
| Overnight queue briefs | PR #31 | Handoff queue merged, but some follow-up briefs require architect cleanup before execution. |
| Blender MCP audit | PR #32 | ADR-014 verdict: reject direct adoption for this release line. |

## Verification Snapshot

Use the committed Phase 5.1 proof for the hardening baseline:

- `00_overview/PHASE5_1_COMPLETION_REPORT.md`
- `00_overview/proofs/phase_5_1_proof.json`
- `00_overview/contract/HONESTY_LEDGER.md`

Expected gates before final v5.3.0 release:

- `pytest -q`
- `ruff check` and `ruff format --check`
- GitHub Actions Layer A/B/C/D/D3/F/M/T/W green or explicitly documented
  advisory/skipped where the workflow marks them non-release-only.
- Windows release workflow validated from a `v*` tag or release-candidate tag.
- No `.env*` secrets in repository diffs; only `.env.example` templates allowed.

## Operator Notes

- Auto-update remains opt-in for Velopack builds. Set
  `HERMES3D_AUTO_UPDATE=1` only when you want update checks enabled.
- `HERMES3D_ENV_FILE` may point to a private env file outside the repo, such as
  `G:\private\.env`; release scripts and docs should not assume a repo-root
  `.env`.
- VPS deployment templates are examples only. Do not run deployment commands
  against live infrastructure without user authorization.
- Restic/Syncthing backup scripts are templates. Keep B2 credentials, repository
  passwords, and local printer config values out of Git.

## Deferred

- Final `v5.3.0` tag and GitHub release creation.
- Hard promotion of Layer D3 from advisory to required.
- Azure Artifact Signing and `winget` manifest work.
- SOTA marketing v2 implementation.
- LM Studio default provider, Mnemosyne recall, Service Health, Settings tab,
  and Hermes Agent pattern ports.
- Any production VPS connection or live deployment.

## Morning Review Checklist

- [ ] Confirm no open release-blocking PRs remain.
- [ ] Confirm `develop` is the intended source for the release-candidate branch.
- [ ] Re-run full tests on the final release-candidate SHA.
- [ ] Verify release artifacts and proof evidence cite the same commit.
- [ ] User explicitly authorizes tag/release publication before any `gh release`
      command is run.
