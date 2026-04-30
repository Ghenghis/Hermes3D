# Hermes3D Branch Strategy

Gitflow, enforced by `.github/workflows/branch-guard.yml` and
`.githooks/pre-push`.

| Branch              | Purpose                          | Source                | Merges to        |
|---------------------|----------------------------------|-----------------------|------------------|
| `main`              | Production. Protected, tagged.   | `release/*`,`hotfix/*`| —                |
| `develop`           | Integration trunk for features.  | `feat/*`              | `release/*`      |
| `feat/<area>/<desc>`| Feature work (one feature each). | `develop`             | `develop`        |
| `release/v<x.y.z>`  | Release stabilization & RC tags. | `develop`             | `main`,`develop` |
| `hotfix/<id>`       | Urgent production fixes & rollbacks. | `main` (or tag)   | `main`,`develop` |

## Enforcement

- **Pre-push hook** (`.githooks/pre-push` / `.githooks/pre-push.ps1`):
  refuses pushes to `main`/`master`; runs the fast test subset.
- **branch-guard workflow** on PRs to `main`:
  - rejects same-branch PRs (`main` → `main`),
  - rejects PRs whose head is not `release/*` or `hotfix/*`,
  - runs `forbidden_pattern_scan.py` to block STUB/TODO leaks.
- **CI workflow** runs the full matrix (Ubuntu + Windows × Python 3.11 + 3.12).

## Tag scheme

- `vX.Y.Z` — production release tag (semver).
- `vX.Y.Z-rcN` — release candidate cut from a `release/v<x.y.z>` branch.
- Tags are immutable; rollbacks create a *new* tag (e.g. `v1.4.2` after
  rolling back `v1.4.1`), never overwrite.

## Naming rules

- Lowercase ASCII, digits, and hyphens only: `[a-z0-9-]`.
- Max 40 characters for the trailing slug.
- Use `scripts/new-feature.sh <area> <short-desc>` (or `.ps1`) to create
  feature branches — it validates naming and bases off `origin/develop`.

## Day-to-day flow

```text
        feat/api/parse-stl ──► develop ──► release/v1.5.0 ──► main
                                                        │
                                                        └► tag v1.5.0
                                                hotfix/INC-2026-04-29 ──► main ──► tag v1.5.1
```

## Rollback

See `06_release/ROLLBACK_RUNBOOK.md`. Rollbacks ride the `hotfix/*` lane
so they pass the same `branch-guard` gates as any production change.
