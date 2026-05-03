# Hermes3D Release Directory

`06_release/` holds operator-facing release material, rollback instructions,
proof artifacts, and packaging entry points.

## Contents

- `BRANCH_STRATEGY.md` - gitflow and branch-protection layers.
- `ROLLBACK_RUNBOOK.md` - production rollback procedure.
- `QUICKSTART_NONCODER.md` - zero-to-UI guided setup.
- `installer/` - `install.{ps1,sh}`, component manifest, and install verifier.
- `phase*-bundle/` - per-phase signed proof bundles and sidecars.
- `deploy/` - reserved for the VPS deploy bundle in B3.
- `backup/` - reserved for the local secrets backup bundle in B4.

## Windows Binaries

Windows desktop builds are published from GitHub Releases when a `v*` tag is
pushed. The `Release - Windows` workflow builds a PyInstaller onedir package,
wraps it with Velopack, uploads release artifacts, attaches a CycloneDX SBOM,
and signs artifacts with Sigstore keyless OIDC.

Auto-update is opt-in. Set the environment variable below before launching a
Velopack-packed build:

```powershell
$env:HERMES3D_AUTO_UPDATE = "1"
```

Leave it unset for the default no-update behavior. GitHub Releases remain the
source of truth for downloadable artifacts. Advanced operators can override the
default update feed with `HERMES3D_UPDATE_SOURCE`.

```text
https://github.com/Ghenghis/Hermes3D/releases
```

`winget install` support is deferred until the signed-distribution phase, after
Azure Artifact Signing is wired.
