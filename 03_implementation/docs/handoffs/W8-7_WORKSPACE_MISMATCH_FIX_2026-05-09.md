# W8-7 Workspace Mismatch Fix (2026-05-09)

**Agent**: W8-7 (Claude)
**Branch**: `claude/w8-7-workspace-mismatch-fix`
**Base**: `feat/hermes3d-7-complete-gui-repo-wiring`
**Lock owner**: `claude-w8-7-workspace-fix`
**Trigger**: W7-3 truth-check P2 environmental failure

---

## Problem (W7-3 finding)

When `04_testing/pytest/unit/test_code_operator.py::test_recovery_*` runs from
a non-canonical worktree (e.g. `G:/Github/_claude_worktrees/h3d-w8-7-workspace-fix`),
six tests fail with:

```
422 != 200
{"detail":{"reason":"MCP lock workspace does not match the Hermes3D edit workspace."}}
```

The check at `code_history.py:3652` (and its sibling at `code_history.py:1263`)
compared `Path(MCP_LOCK_WORKSPACE).resolve() == PROJECT_ROOT.resolve()`. When
the linked worktree path differs from the configured `MCP_LOCK_WORKSPACE`
(the canonical workspace at `G:\Github\h3d-gui-wiring-codex`), the strict
string equality fails even though both paths resolve to the same git repository.

## Root cause

`PROJECT_ROOT` is computed from `Path(__file__).resolve().parents[3]` - the
worktree's own root - so any agent running tests from a linked git-worktree
of the canonical repo gets a different absolute path. The check rejected
that as a "workspace mismatch", though the worktree shares the same git
common-dir, same source files, and same lock semantics.

## Fix

Added `_workspace_paths_equivalent(configured, project_root) -> bool` in
`code_history.py`. Two-tier acceptance:

1. **Fast path** - both paths resolve to the same canonical filesystem
   path. This preserves all prior canonical-workspace behaviour byte-for-byte.
2. **Worktree path** - both paths produce the same resolved
   `git rev-parse --git-common-dir`. This is the documented contract from
   `git-worktree(1)`: "linked working trees share the same repository data"
   via `$GIT_DIR/worktrees/<name>`.

The check is **only** widened to other worktrees of the *same* git
repository. It does NOT widen to:

- arbitrary subpaths of the configured workspace
- the parent of the workspace
- unrelated repositories (different git-common-dir)
- non-git directories

Both call sites updated:

- `code_history.py:1260-1265` (`mcp_lock_readiness`)
- `code_history.py:3654-3659` (`_call_mcp_tool`)

## Sources

1. **git-worktree(1)** - "Linked working trees share the same repository data
   ... `$GIT_DIR/worktrees/<id>` ... `git common-dir`". `git-common-dir` is
   the canonical "are these the same repo" key.
   `git help worktree` | DETAILS section.
2. **Python `pathlib.Path.resolve(strict=False)`** - "Make the path absolute,
   resolving any symlinks. ... If strict is False, the path is resolved as far
   as possible."
   <https://docs.python.org/3/library/pathlib.html#pathlib.Path.resolve>
   This is what canonicalises the gitdir junctions / symlinks Windows + Linux
   git both use for worktrees.

## Verification

### Six previously-failing tests now PASS in the worktree

```
$ cd G:/Github/_claude_worktrees/h3d-w8-7-workspace-fix
$ PYTHONPATH=03_implementation/src \
  MCP_LOCK_WORKSPACE='G:\Github\h3d-gui-wiring-codex' \
  python -m pytest 04_testing/pytest/unit/test_code_operator.py \
    -k 'test_recovery_records_gate_fail or test_recovery_records_patch_rejected or test_recovery_records_merge_git_fail or test_recovery_redacts_secret_like_values or test_recovery_mark_outcome_recovered or test_recovery_state_route_returns_attempts'
6 passed, 46 deselected in 8.63s
```

### New unit pin: `test_workspace_check_accepts_worktrees`

Pins the helper directly with a real `git init` + `git worktree add` flow
inside `tmp_path`. Verifies all four required behaviours:

- identical resolved path -> True
- two linked worktrees of the same repo -> True (both directions)
- non-git directory -> False
- two unrelated repos -> False

```
1 passed in 4.46s
```

### Adjacent regression (13 unit-test files importing `code_history`)

```
156 passed, 2 skipped in 33.36s
```

The two skips pre-date this PR (P2-6 cross-version test, POSIX-only fsync test).
**No new failures.**

### Canonical-workspace regression (proves fast path unchanged)

Same six tests run from the canonical `G:/Github/h3d-gui-wiring-codex` workspace:

```
6 passed, 46 deselected in 7.53s
```

## Files changed

| File | Lines | Change |
|------|-------|--------|
| `03_implementation/src/hermes3d/services/code_history.py` | +66, -2 | Helper + two call-site updates |
| `04_testing/pytest/unit/test_code_operator.py` | +66 | New unit pin |
| `03_implementation/docs/handoffs/W8-7_WORKSPACE_MISMATCH_FIX_2026-05-09.md` | +new | This doc |

## Locks

- `03_implementation/src/hermes3d/services/code_history.py`
- `04_testing/pytest/unit/test_code_operator.py`
- `03_implementation/docs/handoffs/W8-7_WORKSPACE_MISMATCH_FIX_2026-05-09.md`

Owner `claude-w8-7-workspace-fix`. Released after PR open.
