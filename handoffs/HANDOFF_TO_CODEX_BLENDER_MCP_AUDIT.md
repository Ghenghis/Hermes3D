# HANDOFF_TO_CODEX — Blender-MCP-Native audit (research only)

> **Status:** READY for Codex pickup. Smallest scope of the overnight queue. No code changes — output is an ADR.
>
> **Sequence position:** Task 2 in overnight queue (after B5).
>
> **Owner:** `codex-impl-05`.
>
> **Estimated time:** 30-60 minutes.

---

## 1. Mission

Audit `https://github.com/rakaarwaky/blender-mcp-native` to determine whether it should be adopted as the canonical Blender integration path for Hermes3D.

The current Hermes3D Blender integration is `03_implementation/src/hermes3d/adapters/blender_mcp.py` (the existing adapter). The proposed alternative — `rakaarwaky/blender-mcp-native` — claims to be "MCP-native" but its README on first inspection looked like a pasted Blender upstream README, which is suspicious.

Output a decision ADR with one of FOUR verdicts:

- **ADOPT** — adopt as primary Blender path, deprecate or wrap the existing adapter
- **FORK** — fork it, sandbox what's useful, harden licensing/security, expose only safe tools
- **REJECT** — don't adopt; stay with the existing adapter (use ONLY for content-based rejection: licensing-incompatible, security-unsafe, abandoned, or unrelated to its claims)
- **NEEDS-DEEPER-AUDIT** — couldn't reach a confident verdict in the time budget; recommend specific follow-up work (use for: repo unreachable, low-confidence after 60 min, novel security pattern that needs domain expert review)

The architect (Claude) does NOT have a recommendation. You decide based on the audit.

---

## 2. Claim

```text
hermes_pick_task
  owner=codex-impl-05
  prefer_task_id=H3D-BLENDER-AUDIT
```

Or fallback claim with `taskId=H3D-BLENDER-AUDIT`, `title=Audit blender-mcp-native for adoption`, `reason=Decide whether rakaarwaky/blender-mcp-native is safe to adopt or fork; output an ADR.`

---

## 3. Branch

`docs/blender-mcp-native-audit` from `develop`.

---

## 4. Lock these exact 2 files

```text
hermes_lock_files
  owner=codex-impl-05
  taskId=H3D-BLENDER-AUDIT
  ttlMinutes=90
  files=[
    "02_architecture/adr/ADR-014-blender-mcp-native-audit.md",
    "00_overview/contract/ROADMAP.md"
  ]
```

Both NEW files (ADR-014 doesn't exist yet; ROADMAP gets a new row referencing the decision).

---

## 5. Audit checklist

Spend 30-60 minutes investigating. Use online research agents if needed for narrow questions (e.g., "what does the Blender 4.2 GPL exception say about wrapping the Python API in an MCP server?").

### 5.1 What is it actually?

- Clone `https://github.com/rakaarwaky/blender-mcp-native` to `./tmp/audit-blender-mcp-native` (workspace-relative; ensure `tmp/` is in `.gitignore` so the clone doesn't accidentally get staged — read-only — DO NOT add as a remote or submodule)
- Run `git log --oneline | head -20` to see recent activity
- Run `find . -type f -name "*.py" | head -20` and `find . -type f -name "*.md" | head -20` to see what's actually there
- Look for: addon code (`__init__.py` with `bl_info`), MCP server code (`mcp_server.py` or similar), tool definitions, Blender Python API usage
- Is it a fork of Blender (~50 GB of source) or a small addon/plugin (~hundreds of KB)?

### 5.2 License

- Top-level LICENSE file: GPL? MIT? Apache?
- If GPL-2 or GPL-3 (Blender's default), this would contaminate Hermes3D's MIT license if we statically link or vendor any GPL code into the Hermes3D package
- If it's a separate-process MCP server that Hermes3D talks to over stdio, GPL is fine (the server is its own program; calling it from MIT code over a process boundary is not derivative work)
- Document which interaction model applies

### 5.3 Tool surface

- What MCP tools does it expose? List every tool name + signature
- Does it expose `execute_blender_python` or any "run arbitrary Python in Blender" tool?
- If yes: this is a critical security concern. Blender has full filesystem + network access via Python. An LLM with a `python_eval` tool inside Blender = compromise of the entire host machine.
- Are tools allowlisted to specific operations (mesh repair, render, export) or open-ended?

### 5.4 Authentication / sandbox

- Does the MCP server require auth tokens, or is stdio open?
- Is there sandboxing of Blender Python (e.g., restricted builtins, no `os`, no `subprocess`)?
- Is there a process-isolation layer (Blender runs in a container or jail)?

### 5.5 Activity / maintenance

- Last commit date — actively maintained or abandoned?
- Open issues / closed PRs — does the maintainer respond?
- Stars / forks — what's the community signal?
- Release tags — semver? changelog?

### 5.6 Comparison to existing `blender_mcp.py`

- The existing Hermes3D adapter at `03_implementation/src/hermes3d/adapters/blender_mcp.py` already provides Blender integration via MCP
- What does the existing adapter cover? Read its 200-or-so lines and list its capabilities
- Does the new `blender-mcp-native` cover the same ground? Different ground? Subset? Superset?
- Would adoption mean ripping out the existing adapter, or running both?

### 5.7 Specific safety questions to answer in the ADR

- Can a malicious prompt cause filesystem writes outside `/tmp` or `~/.blender`?
- Can it open network sockets?
- Can it import arbitrary Python modules (pickle, marshal, ctypes, etc.)?
- Does it honor Blender's `--factory-startup` flag to avoid loading user addons?
- Is there any analytics / telemetry / phone-home behavior?

---

## 6. Output: ADR-014

Mirror the shape of `02_architecture/adr/ADR-013-kit-hardening-v5_1.md`.

**`02_architecture/adr/ADR-014-blender-mcp-native-audit.md`** — sections:

8 sections (in order):

1. **Title** — ADR-014: Audit of `rakaarwaky/blender-mcp-native` for adoption as Hermes3D's Blender integration path
2. **Status** — Proposed | Accepted | Rejected (you decide)
3. **Date** — 2026-05-03
4. **Context** — Why this audit is happening: existing `blender_mcp.py` adapter, proposal to use `blender-mcp-native` instead, security concerns about arbitrary Python execution in Blender
5. **Decision** — `ADOPT` / `FORK` / `REJECT` / `NEEDS-DEEPER-AUDIT` (one of the four) with verdict statement
6. **Rationale & Consequences** — 5-15 bullet points walking through the §5 audit findings. Reference specific commits, file paths, license fragments. Cover both positive + negative consequences of the chosen verdict.
7. **Alternatives considered:**
   - Keep `blender_mcp.py` as-is (status quo)
   - Adopt `blender-mcp-native` as primary
   - Fork and harden `blender-mcp-native`
   - Build a minimal new Blender adapter from scratch
8. **References** — GitHub repo URL, last commit SHA at audit time, license file path within the repo, any external blog posts / discussions found via online research

**`00_overview/contract/ROADMAP.md`** — add a row under the `Future / Pending Audits` section (create the section if it doesn't exist):
- `Blender MCP integration path (ADR-014)` | Status: `<your verdict>` | Decision date: 2026-05-03

---

## 7. Tests + gates

```text
hermes_run_gate gateId=git-status      cwd=.
hermes_run_gate gateId=git-diff-check  cwd=.
```

Local:
- ADR-014 has the 8 standard sections (Title, Status, Date, Context, Decision, Rationale & Consequences, Alternatives, References)
- ROADMAP.md still parses (no markdown breakage)

This is a docs-only PR. **Do NOT run `pytest -q`** — it's not necessary and adds 30+ minutes to a 30-60min task. Layer F (honesty gates) on the PR will validate the contract / manifest if needed.

---

## 8. PR + close-out

```bash
git push -u origin docs/blender-mcp-native-audit
gh pr create --base develop \
  --title "docs(adr): ADR-014 — audit of blender-mcp-native (verdict: <ADOPT/FORK/REJECT>)" \
  --body "[mirror prior PR body shape; Hermes evidence chain: PASS; Task: H3D-BLENDER-AUDIT; Gate run: git-status PASS, git-diff-check PASS]"
```

Close-out:

```text
hermes_append_evidence
  owner=codex-impl-05
  taskId=H3D-BLENDER-AUDIT
  kind=checkpoint
  summary=ADR-014 written; verdict <ADOPT/FORK/REJECT>; PR #N opened at SHA <commit>

hermes_release_files  owner=codex-impl-05  files=[the 2 above]
hermes_release_task   owner=codex-impl-05  taskId=H3D-BLENDER-AUDIT
```

---

## 9. Hard rules

- DO NOT add `rakaarwaky/blender-mcp-native` as a git submodule, remote, or runtime dependency without an ADOPT verdict that explicitly authorizes it
- DO NOT execute any code from the cloned repo on your machine. Inspection only — read files, don't `python anything.py`
- DO NOT touch `03_implementation/src/hermes3d/adapters/blender_mcp.py` — that's a code change for a follow-up checkpoint if the verdict is FORK or REPLACE
- DO NOT touch any file outside the 2 locked above
- DO NOT install Blender on the host machine for testing — audit is documentation-only

## 10. Failure protocol

If you can't reach the GitHub repo (network, takedown, etc.), write the verdict as **REJECT** with rationale "repo unreachable at audit time". That's a valid output.

If the repo turns out to be empty or unrelated to its README claims, write the verdict as **REJECT** with rationale "repo content does not match stated purpose".

If you have low confidence after 60 minutes of audit, write the verdict as **NEEDS-DEEPER-AUDIT** (a 4th valid option) and recommend specific follow-up work.
