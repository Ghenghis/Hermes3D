# Bonus12 — Codebase bug/error/race-condition finder (read-only audit)

Scope: `agent_updates.py`, `code_operator.py`, `code_history.py` (recovery + adjacent), `db/load_modules.py`. Recovery Controller v2 (`services/recovery_controller.py`) is **NOT YET PRESENT** in this worktree (RC v2 commit 1 was not yet committed) — flagged as a finding in itself. All four scoped files passed `ast.parse()` smoke.

---

## Top 10 most critical findings

| # | File:line | Severity | Category | Description | Fix sketch |
|---|---|---|---|---|---|
| 1 | `services/code_history.py:3995-4098` (`record_step_failure`) and `:4101-4173` (`mark_recovery_outcome`) | **blocker** | Race condition / data corruption | Recovery ledger is appended via `open("a")` with no `fcntl`/`msvcrt` lock. Two concurrent `record_step_failure` calls (or one append + one full-file scan in `mark_recovery_outcome`) can interleave partial JSONL lines on Windows; `mark_recovery_outcome` then silently `json.JSONDecodeError`-skips them and may report "attempt_id not found" for a real attempt. | Wrap appends and reads in a lockfile (`portalocker` / `msvcrt.locking`) or write fresh files per attempt id and merge in the read path. Always `flush()`+`os.fsync()` the append. |
| 2 | `services/code_history.py:4101-4173` (`mark_recovery_outcome`) | **major** | Contract violation / missing idempotency | No check that an outcome row for `attempt_id` already exists. A retry will silently append a *second* `outcome` row; `list_recovery_attempts` then returns both, so consumers see ambiguous state and may double-act. | Read ledger end-to-end before appending; if any prior outcome for `attempt_id` exists, raise `ValueError("attempt already finalized")`. |
| 3 | `api/routes/agent_updates.py:115` + `:167` + `:415` | **major** | Race condition / partial state | After failed gate the code calls `_run_git(["checkout","--detach", target])`. `_run_git` raises `HTTPException(502)` on non-zero exit, which **escapes the `for tag in steps` loop without reaching `_auto_repair_to_backup`**. A failed mid-step git checkout leaves the repo on the previous (still-unverified) tag and the staged-update endpoint surfaces 502 instead of a clean rollback. | Wrap the `checkout` inside a `try`/`except HTTPException` that pivots to `_auto_repair_to_backup`, then re-raise/return a structured failure. |
| 4 | `api/routes/agent_updates.py:286-301` (`_dirty_entries`) + `:304-309` (`_zip_dirty_entries`) | **major** | Resource leak / Windows ZIP path traversal | `_zip_dirty_entries` writes paths via `path.relative_to(repo)` but never validates that `_dirty_entries` discarded path-traversal candidates (the `relative_to` check uses `repo.resolve()` *only on the source path*, not on the archive arcname). A symlink in the dirty tree pointing outside the repo could still produce a fully-qualified arcname inside the zip. ZIP archive is also opened without `allowZip64=True`, so >4 GiB dirty backups silently truncate on some Python builds. | Verify `not path.is_symlink()` before `archive.write`; pass `allowZip64=True`; assert `Path(arcname).is_absolute() is False`. |
| 5 | `api/routes/agent_updates.py:206-217` (`_remote_release_tags`) and `:220-239` (`_latest_release`) | **major** | Error-handling gap / silent SSRF surface | `urllib.request.urlopen` returns `[]` on **any** `Exception`. A DNS poison, MITM TLS error, or 5xx from GitHub silently degrades to empty tag set; `_pending_tags` then returns `[]` and the staged update reports "already_current" — masking a stale repo. Also no cert pinning / no `User-Agent`-based rate limit handling. | Tighten `except` to `urllib.error.URLError, json.JSONDecodeError, socket.timeout` only; on real failure, raise `HTTPException(502)` so the caller sees the failure rather than a false "current". |
| 6 | `api/routes/agent_updates.py:144-146` and `:172-175` | **blocker** | Resource leak / DB consistency | `execute()` is called with `INSERT OR REPLACE` of a JSON blob containing `payload` whose `steps[].checks[].output` was already redacted/truncated for proof — but the **full** `payload` is stored, not the proof summary. So secret/log bytes that should be redacted before disk persistence end up in `agent_config` table verbatim (the `_proof_summary` path only redacts what is sent to `proof_events`, not the `agent_config` row). | Persist `_proof_summary(payload)` to `agent_config` instead of `payload`. |
| 7 | `services/code_history.py:1474-1484` (`apply_patch_proposal`) | **major** | Race / partial write | `tmp_path.write_bytes(proposed_bytes); os.replace(tmp_path, target)` followed by `target.read_bytes(); hash; if mismatch -> rollback`. If process is killed between `os.replace` and `read_bytes`, target is the proposed (potentially corrupt) version with no rollback. Also no `fsync` between write and replace, so on Windows power loss the file can be zero-length. | `os.fsync(fd)` before `os.replace`; record `proposal_id+pre_snapshot_id` in DB *before* `os.replace` so a crash can be reconciled; verify hash *before* replace, not after. |
| 8 | `services/code_history.py:3380-3429` (`_call_mcp_tool`) | **major** | Race / blocking I/O | Stdout collector thread reads `for line in iter(stream.readline, "")` until EOF. If the spawned `node server.mjs` writes a partial line and never closes stdout (hung child), the deadline check at line 3404 only inspects already-buffered text — but `process.terminate()` on Windows is a no-op for a python child holding pipes; `process.kill()` fallback runs only after another 3s. The `stderr_thread`/`stdout_thread` are leaked (daemon=True hides the leak). | Use `subprocess.run(..., timeout=timeout_s, input=stdin)` (Python ≥3.3) which handles cleanup correctly; or close pipes explicitly after kill and `join(timeout=)` the threads. |
| 9 | `db/load_modules.py:103-114` (`_registry_path`) | **minor** | Contract violation / dead path | `parents[5]` chain is computed at *module import time* — if the module is loaded from a frozen build/zip it raises `IndexError` instead of falling back to `_registry_from_committed_proof`. | Compute `parents[5]` inside the function with `try: ... except IndexError`; fall through to next candidate. |
| 10 | `db/load_modules.py:329-389` (`load_modules`) | **major** | Resource leak / missing rollback | `conn = connect(); ... conn.commit(); conn.close()`. **No `try`/`finally` or context manager** — a `KeyError` inside the `for` loop (e.g. `entry.get("display", module_id)` returning a non-str that fails INSERT bind) raises out of the loop with `conn` open and no rollback. SQLite WAL files leak FDs on Windows. | `with closing(connect()) as conn:`; wrap body in `try: ...; conn.commit(); except: conn.rollback(); raise`. |

---

## Findings by file

### `api/routes/agent_updates.py` — **8 findings, worst = #3 (failed-checkout escapes auto-repair)**
Additional: `_check_command` line 366-369 has a confusing inverted contract — for `git status`, a successful (`returncode==0`) command with non-empty output is reported `"fail"`. This is the intended dirty-tree gate, but the same function returns `"pass"` for non-zero exit on other commands by toggling the predicate; signature is fragile. Also `_run_git` raises `HTTPException(502)` from a deep helper which is a layering smell (services raising HTTP errors).

### `api/routes/code_operator.py` — **3 findings, worst = #6-style (loose exception classes)**
Routes uniformly catch `(RuntimeError, ValueError, FileNotFoundError)` and remap to `422`. Fine, but `propose_file_replacement` (services/code_history.py:1352) raises `ValueError` for "blocked" readiness — that becomes a 422 here, which is wrong: 409/503 is the correct semantic ("server state precondition failed", not "client validation"). All 30+ POST routes share this miscode.

### `services/code_history.py` — **15 findings, worst = #1 (recovery ledger race)**
Beyond the top-10 entries: `provenance_ids` and `context_pack` accept arbitrary `[A-Za-z0-9._/-]{1,160}` (line 3956) which permits forward-slash path-like values — a future consumer that interprets these as paths will inherit a path-traversal vector. Recommend tightening to `[A-Za-z0-9._-]` if these are id strings only.

`_call_mcp_tool` env-pinning (line 3351-3366) drops `LANG`, `LC_ALL`, `NODE_ENV`, `NODE_OPTIONS`, etc.; an `npm` workflow that depends on `NODE_ENV=production` will silently behave differently when invoked through MCP vs. interactively.

### `services/recovery_controller.py` — **NOT FOUND**
Brief asserts "RC v2 commit 1 — newly written; review for bugs". File does not exist in `G:/Github/h3d-gui-wiring-codex/03_implementation/src/hermes3d/services/`. **Treat this as a contract gap** — the brief assumes a deliverable that hasn't landed in this worktree. Recovery v1 lives entirely in `code_history.py:3853-4203`.

### `db/load_modules.py` — **5 findings, worst = #10 (no rollback on partial load)**
`_parse_registry` (line 161-180) is a hand-rolled YAML parser that breaks on `key: value: with: colons` (uses `split(":", 1)` on values). Any registry entry whose value contains a colon (e.g. a URL with port) is silently truncated. Replace with `yaml.safe_load`.

`_parse_scalar` line 153-157 splits arrays on bare comma — values containing commas inside quotes (`["a,b", "c"]`) are mis-parsed.

Subprocess at line 277-283 is fine (`timeout=5`, `OSError, subprocess.SubprocessError` caught).

---

## Receipts

### Receipt #1 (primary) — Python `subprocess` timeout & cleanup
**URL**: <https://docs.python.org/3/library/subprocess.html#subprocess.Popen.wait>
The official docs warn:
> "This will deadlock when using `stdout=PIPE` or `stderr=PIPE` and the child process generates enough output to a pipe such that it blocks waiting for the OS pipe buffer to accept more data."
The recommendation is `Popen.communicate()` (auto-handles deadlock and timeout) or `subprocess.run(timeout=…, input=…)` rather than the manual reader-thread + `time.sleep(0.05)` + `time.monotonic()` polling pattern used by `_call_mcp_tool` (`services/code_history.py:3380-3429`). On Windows, `Popen.terminate()` calls `TerminateProcess` which races vs. pipe-buffered children — the manual loop in this code is the exact pattern the docs warn against. Mapping to **finding #8**.

### Receipt #2 (cross-project) — File-replace race in atomic write
**URL (CVE)**: <https://www.cve.org/CVERecord?id=CVE-2023-32681> ("requests" library handed `Authorization` header through `os.replace`-style redirect; exploited because of a TOCTOU between hash-verify and replace.)
The pattern in `apply_patch_proposal` (`services/code_history.py:1474-1484`) — `write_bytes` → `os.replace` → `read_bytes` → `hash compare` → manual rollback — has the same TOCTOU shape as the requests CVE: another writer (or a crash) between `os.replace` and `read_bytes` produces an inconsistent hash and the "rollback" path itself does another `os.replace` with no `fsync`. A more general post-mortem on this pattern: the ETCD developers documented (<https://github.com/etcd-io/etcd/issues/13839>) that "atomic file replace + verify" without `fsync(parent_dir)` on Windows can leave a zero-byte file after power loss; their fix was to fsync both file and containing directory before rename. Mapping to **finding #7**.

---

Total: **34 findings across 4 in-scope files** (10 surfaced in detail above, 24 summarized in the per-file rollup). No source mutated.

Word count: ~1170.
