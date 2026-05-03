# Local-Only Backup

This bundle keeps private Hermes3D operator state out of GitHub while giving the
operator two recovery paths:

- LAN replication via Syncthing to a NAS or second PC.
- Offsite encrypted snapshots via Restic to Backblaze B2.

## What Gets Backed Up

- Local operator environment file path, if used.
- `03_implementation/config/printers.user.toml`.
- `%USERPROFILE%\.hermes3d\`, excluding `restic-env.ps1`.
- `%APPDATA%\Hermes3D\`, if present.

Do not back up repository source, build products, or generated proof bundles
with this local-secret flow.

## One-Time Setup

1. Configure Syncthing from `syncthing-share-template.md`.
2. Create a private Backblaze B2 bucket for Restic snapshots.
3. Install Restic on the Windows machine.
4. Create `%USERPROFILE%\.hermes3d\restic-env.ps1` outside Git and outside the
   Syncthing share. It must set `RESTIC_REPOSITORY`, `RESTIC_PASSWORD`,
   `B2_ACCOUNT_ID`, and `B2_ACCOUNT_KEY`.
5. Run `restic init` once after loading that environment file.

No sample credential values are committed here. Keep the environment file in a
password manager and test that it is not visible in Syncthing.

## Nightly Schedule

Use Windows Task Scheduler with a daily trigger. The action should run
PowerShell with this shape:

```xml
<Command>pwsh.exe</Command>
<Arguments>-NoProfile -ExecutionPolicy Bypass -File "C:\Path\To\Hermes3D\06_release\backup\restic-backup.ps1"</Arguments>
```

The script fails loudly if `%USERPROFILE%\.hermes3d\restic-env.ps1` is missing.

## Restore Drill

Run a quarterly recovery drill:

1. Start `restic-restore.ps1`.
2. Pick a snapshot ID from the printed snapshot list.
3. Restore to a temporary staging directory.
4. Compare the restored printer config and Hermes3D state with the live files.
5. Delete the staging directory after verification.

The restore script refuses to restore directly into live Hermes3D state.

## Full Machine Loss

1. Reinstall Hermes3D on the replacement machine.
2. Restore Restic credentials from the password manager.
3. Run `restic-restore.ps1` to a staging directory.
4. Copy only the reviewed files into their live locations.
5. Reconnect Syncthing after the live state is verified.
