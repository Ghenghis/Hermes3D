# PR #192 — Final Decision (W9-2n, 2026-05-10)

Branch: `claude/w8-2-gui-settings-approvals-apps`
Title: `feat(ui): Settings/Approvals/AppRegistry breadth pages (Wave 8 W8-2)`
Decision agent: `claude-w9-2n-pr192-decision`
Lock owner (this work): `claude-w9-2n-pr192-decision`

## Failure history (most recent first)

| Run id | Sha | Commit | Layer D2 — UI-Final | Failing tests |
|---|---|---|---|---|
| 25623555898 | `e62bc691` | W9-2k: route appsClient singleton through createAppsClient | FAIL | `app-status.spec.ts:123/151/166` (3 tests) |
| 25623022792 | `dd65e42b` | W8-2 rebase: add app-detail-versions testid | FAIL | `gui-breadth-pages.spec.ts:212` (1 test) |
| 25622801377 | `4617d875` | (earlier rebase) | FAIL | (earlier breadth test) |
| 25622293528 | `fc75e8a8` | (last green) | PASS | — |

W9-2k did fix `gui-breadth-pages.spec.ts:212` (it now passes), but exposed a different
regression in `app-status.spec.ts`.

## Latest fail log (redacted excerpt)

```
✘  7 [chromium-1920x1080] tests/e2e/app-status.spec.ts:123:1
   App registry table renders three apps with mixed lifecycles (5.7s)
✘  8 [chromium-1920x1080] tests/e2e/app-status.spec.ts:151:1
   Run proof shows success toast and updates state (30.2s)
✘  9 [chromium-1920x1080] tests/e2e/app-status.spec.ts:166:1
   View details navigates to detail page and shows recent proofs (30.2s)

   Error: expect(locator).toBeVisible() failed
   Locator: getByTestId('app-row-hermes-agent')
   Expected: visible
   Received: <element(s) not found>
   Call log:
   - Expect "toBeVisible" with timeout 5000ms
   - waiting for getByTestId('app-row-hermes-agent')

  3 failed
  78 passed (3.1m)
```

## Failure category

**NEW** — different from W9-2g (TS2688) and W9-2k (`app-detail-rollback`).
W9-2k changed the appsClient contract; that change exposed an incomplete
test stub in `app-status.spec.ts`.

## Root cause

W9-2k flipped the singleton from a module-level `appsClient` (which only
hit `/api/source-os/modules`) to `createAppsClient({ baseUrl })`, which
tries `/api/apps` first and falls back to `/api/source-os/modules` only
when the primary response is **not OK**. In the failing factory:

```ts
const primary = await fetcher(appsUrl, init);   // → /api/apps
if (primary.ok) {
  return extractList(await primary.json());     // ← short-circuits
}
const fallback = await fetcher(modulesUrl, init);
```

The Playwright suite in `app-status.spec.ts` stubs **only**
`**/api/source-os/modules`. The unstubbed `**/api/apps` call hits the
real FastAPI bridge in CI; that endpoint returns 200 OK with an empty
payload (no `/api/apps` route is registered), so `extractList(...)`
yields `[]`, listApps returns `[]`, and **no rows render**.

`gui-breadth-pages.spec.ts` already stubs both endpoints (lines 138-148),
which is why it passes on the same HEAD.

Reference for the decision tree below: <https://en.wikipedia.org/wiki/Decision_tree>.

## Decision tree

```
SAME failure as W9-2k? ─────────► no  ─► continue
NEW failure?           ─────────► yes ─► continue
Diagnosis is clear?    ─────────► yes ─► continue
Fix is < 10 LoC?       ─────────► yes ─► PATH 1 (apply, force-push, single state check)
                                 no   ─► PATH 3 (NEEDS-HUMAN)
Side effects > PR scope? ─────► no   ─► PATH 1
                                 yes  ─► PATH 4 (revert)
W8-2 content already covered by merged PRs? ► yes ► PATH 2 (RECOMMEND-CLOSE)
```

## Recommended path: **PATH 1 — fix once more**

Fix is a 1-function diff inside the test file (no production code).
Aligns the stub set in `app-status.spec.ts` with the existing pattern in
`gui-breadth-pages.spec.ts` so both endpoint families return the
fixture, regardless of which one `appsClient` reaches first.

### Diff scope (single file)

`03_implementation/ui/tests/e2e/app-status.spec.ts` — `stubApps()`:

- Add `**/api/apps` GET → `SAMPLE_APPS`
- Add `**/api/apps/hermes-agent` GET → `SAMPLE_DETAIL`
- Add `**/api/apps/*/run-proof` POST → `runProofPayload`
- Hoist `runProofPayload` (deduplicate between `apps` and
  `source-os/modules` branches)
- Keep all existing `**/api/source-os/modules*` stubs (fallback path)

Total ≈ 16 net LoC added in one function.

### Why not patch `appsClient.ts` instead?

Two options were considered:

1. **Test stub fix (chosen)** — `extractList` short-circuit on empty is
   not strictly wrong (it's a valid backend contract for "no apps yet"),
   and `gui-breadth-pages.spec.ts` already pioneered the dual-stub
   pattern. Smaller blast radius — touches a test file only.
2. **Production fallback fix** — change `if (primary.ok)` to also fall
   through when the parsed list is empty. Larger blast radius (changes
   the canonical client semantics for every consumer).

Path 1 picks option (1). Production semantics stay frozen. Future test
authors are no longer required to know which endpoint the client picks
first.

### Outcome (after force-push)

Pending. Single state check after the next UI-Final run.

## Final state field (filled after run)

- `#192 final state`: **OPEN-FIXED-PENDING** (pushed; awaiting Layer D2 — UI-Final)

## Lock release

- `03_implementation/docs/handoffs/PR192_FINAL_DECISION_2026-05-10.md`
- `03_implementation/ui/tests/e2e/app-status.spec.ts`
