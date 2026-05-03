# Hermes3D Local State Syncthing Template

This template keeps private Hermes3D operator state off GitHub while giving the
operator a local copy on a NAS or second PC. The development machine is the only
sender.

## Topology

- Development machine: Syncthing folder type `Send Only`.
- NAS or second PC: Syncthing folder type `Receive Only`.
- Offsite copy: handled separately by `restic-backup.ps1`; do not place Restic
  credentials in the Syncthing share.

## Folders To Share

Create one Syncthing folder per source so paths stay explicit and reviewable:

| Folder label | Source path template | Purpose |
| --- | --- | --- |
| `hermes-user-env` | `%USERPROFILE%\.env` | Local operator environment file, if used. |
| `hermes-printers` | `<Hermes3D workspace>\03_implementation\config\printers.user.toml` | Private printer inventory. |
| `hermes-user-state` | `%USERPROFILE%\.hermes3d\` | Local Hermes3D state, caches, and metadata. |
| `hermes-roaming-state` | `%APPDATA%\Hermes3D\` | Windows app profile state, if present. |

Use placeholder paths until the operator substitutes their real workspace and
Windows profile paths. Do not commit the substituted values.

## Required Ignore Pattern

Add this ignore rule to the `%USERPROFILE%\.hermes3d\` share so restore
credentials stay outside Syncthing:

```text
(?d)restic-env.ps1
```

## Versioning

Enable Staggered File Versioning on the receiver with this policy target:

- 5 versions retained across the most recent day.
- 4 weekly versions retained after that.
- 4 monthly versions retained after that.

Run a quarterly restore drill by copying the receive-only folder to a temporary
staging directory and confirming Hermes3D can read the restored printer config.

## Safety Checks

- Confirm every folder is `Send Only` on the development machine.
- Confirm the receiver is `Receive Only`.
- Confirm `restic-env.ps1` is not present on the receiver.
- Confirm no folder points at the live Git repository root.
