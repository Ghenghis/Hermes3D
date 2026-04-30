# Hermes3D Rollback Runbook

Rubric criterion 5 — "Rollback path defined." This runbook is the canonical
procedure when a release breaks production and needs to revert.

> **Scope.** Production rollbacks of `main` to a prior tag. Feature-branch
> reverts use the normal PR flow.

---

## Step 1 — Identify the last-known-good tag

```bash
git fetch --tags
git tag -l 'v*' --sort=-v:refname | head -3
```

Pick the most recent tag known to be healthy (skip `-rcN` candidates unless
they were the last green prod). Record the chosen tag as `$LKG_TAG`.

## Step 2 — Create the rollback branch

```bash
INCIDENT_ID="INC-$(date -u +%Y%m%d-%H%M)"
git checkout -b "rollback/${INCIDENT_ID}" "${LKG_TAG}"
git push -u origin "rollback/${INCIDENT_ID}"
```

Naming: `rollback/<incident-id>`. The `rollback/*` prefix is reserved and
will be treated as a `hotfix/*` peer by the gateway (see Step 4).

## Step 3 — Cherry-pick urgent fixes forward

If any commits since `$LKG_TAG` must be preserved (e.g. a security patch
that is *not* the cause of the incident), cherry-pick them:

```bash
git cherry-pick <sha1> [<sha2> ...]
# resolve any conflicts; keep the diff minimal
```

Run the fast test subset locally:

```bash
bash scripts/scaffolding/test.sh --fast
```

## Step 4 — Open expedited PR through the release gateway

The `branch-guard.yml` workflow allows only `release/*` and `hotfix/*` to
target `main`. For rollbacks, rebase/rename onto `hotfix/`:

```bash
git branch -m "rollback/${INCIDENT_ID}" "hotfix/${INCIDENT_ID}"
git push origin -u "hotfix/${INCIDENT_ID}"
gh pr create --base main --head "hotfix/${INCIDENT_ID}" \
  --title "hotfix(${INCIDENT_ID}): rollback to ${LKG_TAG}" \
  --label "rollback,expedited" \
  --body-file .github/PULL_REQUEST_TEMPLATE/rollback.md
```

Required gates (cannot bypass):

- `branch-guard.yml` job `enforce_release_or_hotfix` (passes because head is `hotfix/*`)
- `branch-guard.yml` job `forbidden_pattern_scan`
- `ci.yml` Layers A/B/C

Reviewer SLA for `expedited`-labelled PRs: **30 minutes**.

## Step 5 — Announce via the notifier

After merge and tag (`git tag -a v<x.y.z+1> -m "rollback to ${LKG_TAG}"`),
broadcast through the platform notifier:

```python
from hermes3d.core.notifications import notifier  # core.notifications.notifier
notifier.send(
    channel="incidents",
    severity="high",
    payload={
        "incident_id": INCIDENT_ID,
        "rollback_target": LKG_TAG,
        "summary": "Rolled main back to <tag> due to <cause>.",
    },
)
```

---

## Communication template

Copy into the incident channel / status page. Replace `<...>` placeholders.

```markdown
### Incident <INCIDENT_ID> — Rollback in progress

**Summary**
<one-paragraph description of the failure: what users see, when it started,
how it was detected.>

**Impact**
- Affected users / surfaces: <...>
- Severity: <SEV-1 | SEV-2 | SEV-3>
- Detected at: <UTC timestamp>

**Rollback target**
- Tag: `<LKG_TAG>`
- PR: <link to hotfix PR>
- Hotfix branch: `hotfix/<INCIDENT_ID>`

**ETA**
- Merge: <UTC>
- Deploy: <UTC>
- All-clear: <UTC>

**Follow-up**
- Tracking issue: <link>
- Post-mortem owner: <@handle>
- Re-land plan for reverted commits: <link or "TBD in post-mortem">
```

---

## Verifying the path is intact (quarterly drill)

1. `git tag -l 'v*' --sort=-v:refname | head -3` returns three tags.
2. `cat .github/workflows/branch-guard.yml` contains `release/*|hotfix/*`.
3. A dry-run hotfix branch can be opened against `main` and gated PRs pass.
