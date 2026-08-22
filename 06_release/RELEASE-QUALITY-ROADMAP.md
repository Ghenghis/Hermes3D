# Hermes3D Release-Quality Roadmap

## Current state (HermesProof snapshot)

| Area | Status | Detail |
|------|--------|--------|
| Workspace | `G:\Github\Hermes3D` | Active Hermes3D workspace |
| Branch | `codex/w21-mvp6-gen3d-bgremove` | Non-main release branch |
| Commit | `87a96ebf...` | Current HEAD |
| Test mode | `release` | Release mode active; open blocker tickets will block release |
| Open tickets | 0 | No active bug tickets |
| Workspace hygiene | **dirty_blocked** | 53 tracked modifications, 12 untracked paths |
| Evidence ledger | 1542 chained / 23 unchained | 23 evidence entries are not hash-chained |
| Contract | Default `project-truth-contract` | `required_gates` empty; basic required_evidence defined |

## Release-quality standards

1. **Workspace hygiene is clean** — no uncommitted tracked changes and no unexpected untracked files, or an approved `expected-diff` manifest.
2. **Contract is explicit** — `required_gates` and `required_evidence` are set and match the release scope.
3. **All required gates pass** — lint, build, tests, diff-check, and any project-specific gates.
4. **Evidence ledger is intact** — all entries chained; no accepted breaks.
5. **No open release-blocking tickets** — zero open `critical`/`high` bugs in `release` mode.
6. **Protected paths untouched** — no unreviewed changes to `.github/`, `src/`, `package.json`, `pyproject.toml`, etc.

## Roadmap to release

### Phase 1 — Stabilize the workspace (next step)

- [ ] Decide the fate of the 53 tracked changes:
  - Commit intentional work with a descriptive message, **or**
  - Create a reviewed `expected-diff` manifest and re-run `hermes_workspace_hygiene`.
- [ ] Decide the fate of the 12 untracked paths:
  - Add to `.gitignore` (e.g., `.claude/`, `phase-0-log/`, `*.db`), **or**
  - Commit if they belong in the release.
- [ ] Run `hermes_workspace_hygiene` again until `release_ready: true`.

### Phase 2 — Lock the release contract

- [ ] Update `project-truth-contract` to include release gates:
  - `git-status`
  - `git-diff-check`
  - `npm-lint` / `npm-typecheck` (Node/UI packages)
  - `npm-build`
  - `npm-test`
  - `playwright` (if E2E is in scope)
- [ ] Keep `required_evidence`:
  - Test/proof command output for changed behavior
  - Exact changed files
  - Truthful remaining gaps
- [ ] Protect release-critical paths (already present):
  - `.gitlab-ci.yml`, `.github/`, `src/`, `scripts/`, `external/`, `package.json`, `pyproject.toml`

### Phase 3 — Run every required gate

- [ ] `git-status` — clean
- [ ] `git-diff-check` — no whitespace or merge conflicts
- [ ] `npm-lint` — no lint errors
- [ ] `npm-typecheck` — no TS errors
- [ ] `npm-build` — production build succeeds
- [ ] `npm-test` — all unit tests pass
- [ ] `playwright` — E2E passes (if enabled)
- [ ] Fix or ticket any failure before continuing.

### Phase 4 — Repair the evidence chain

- [ ] Investigate 23 unchained evidence entries.
- [ ] Re-run the sources that produced them, or append `evidence.appended` entries that close the chain.
- [ ] Re-run `hermes_verify_evidence` until `breaks: []`.

### Phase 5 — Final release review

- [ ] Open a merge request from `codex/w21-mvp6-gen3d-bgremove` to `main`.
- [ ] Attach gate results and evidence IDs to the MR.
- [ ] Obtain approval via the contract (CODEOWNERS or HermesProof approval gate).
- [ ] Tag the release and merge.

## Immediate next action

**Create an expected-diff manifest or commit the 53 modified files, then clean up the 12 untracked paths.** This is the only blocker that prevents the workspace from being `release_ready`.

Use these commands as a starting point:

```powershell
# Preview what is dirty
git status --short

# If the changes are intentional
git add .
git commit -m "feat: W21 MVP6 gen3d bgremove stabilization"

# If the changes are temporary/local only, create a manifest and ask HermesProof
cat > expected-w21-mvp6.json <<EOF
{
  "sourceRoot": "G:\\Github\\Hermes3D",
  "archiveRoot": "G:\\Github\\Hermes3D\\06_release\\backup",
  "archiveId": "w21-mvp6-expected",
  "manifest": {}
}
EOF
```
