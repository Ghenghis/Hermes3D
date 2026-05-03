# ADR-014 — Audit of `rakaarwaky/blender-mcp-native` for adoption as Hermes3D's Blender integration path

**Status:** Proposed.
**Date:** 2026-05-03.
**Related:** [ADR-009 orchestration skeleton](ADR-009-orchestration-skeleton.md), existing adapter `03_implementation/src/hermes3d/adapters/blender_mcp.py`.
**Tracking:** ROADMAP.md "Future / Pending Audits" row.

## Context

Hermes3D currently has a Phase-1 detect/version/capabilities skeleton at
`03_implementation/src/hermes3d/adapters/blender_mcp.py` that probes for `uvx`
on PATH and returns a `DetectResult`. Phase 3 is meant to wire this against a
real provider via `claude mcp list`. The adapter assumes the upstream provider
is the `uvx blender-mcp` package — i.e. an out-of-process MCP server that talks
to Blender via Blender's existing addon socket.

A proposal arrived to instead adopt `https://github.com/rakaarwaky/blender-mcp-native`
as the canonical Blender path. The author claims it is a fork of Blender with
"native MCP support" baked in, removing the need for a separate `blender-mcp`
package. This ADR records the audit of that repo and recommends a verdict.

The security stake is high: a Blender MCP integration that exposes "run
arbitrary Python in the Blender process" tools is, by construction,
remote-code-execution-as-a-service. Hermes3D's Phase 4 write-action boundary
(documented in ADR-009) requires that any RCE-shaped capability be (a) opt-in,
(b) authenticated, (c) constrained to an allowlist of operations, or (d) all
three. The audit's primary question is whether `blender-mcp-native` meets any
of these bars.

## Decision

**Verdict: REJECT.**

Hermes3D will **not** adopt `rakaarwaky/blender-mcp-native` as either the
canonical Blender path or as a vendored dependency. The existing
`uvx blender-mcp` provider-manager skeleton at
`03_implementation/src/hermes3d/adapters/blender_mcp.py` remains the path
forward; Phase 3 wiring proceeds against the upstream community provider as
originally planned.

This ADR is a content-based rejection. Three independent properties of
`rakaarwaky/blender-mcp-native` would each on their own be sufficient to
reject; together they make adoption untenable.

## Rationale & Consequences

Audit findings (clone at `tmp/audit-blender-mcp-native`, last commit
`3f6652783bff68198698fd668dbe82c65b5b3908`, dated 2026-04-26):

- **Repo scope is a full Blender source fork, not an addon.** Top level
  contains `source/`, `intern/`, `extern/`, `release/`, `CMakeLists.txt`
  (117 KB), `GNUmakefile` (22 KB), `make.bat` — the canonical Blender source
  tree, 12,936 tracked files, ~50 GB once submodules + libs land. The "native
  MCP support" advertised in the repo description is **one** added file:
  `scripts/startup/blender_mcp.py`, 196 lines.
- **Repo activity is essentially zero.** `git log --all --oneline` returns a
  single commit (`3f66527`, "Initial commit with native MCP support and
  Fedora 44 build fixes"). GitHub metadata confirms 0 stars, 1 fork, 0 open
  issues, 0 releases. There is no evidence the fork tracks upstream Blender
  security fixes; adopting it would freeze us at one snapshot of a
  fast-moving codebase.
- **License is GPL-3.0.** `COPYING` at the repo root states "Blender uses the
  GNU General Public License" and "Apart from the GNU GPL, Blender is not
  available under other licenses"; `README.md` confirms "GNU General Public
  License, Version 3." Hermes3D itself ships under a more permissive license
  (see top-level `LICENSE`). Vendoring or distributing a GPL-3 Blender fork
  as a runtime component of Hermes3D would impose copyleft obligations on
  any downstream Hermes3D distribution that bundles it. The existing
  arrangement — Blender remains the user's separate install, Hermes3D talks
  to it over a socket — sidesteps this entirely. Adopting the fork
  re-introduces a license-class conflict for no architectural gain.
- **The MCP surface is unsafe by design.** `scripts/startup/blender_mcp.py:17-115`
  defines a `BlenderMCPServer` that:
  - Binds `0.0.0.0:9876` (line 18, `host='0.0.0.0'`) — every interface,
    not loopback.
  - Has **no authentication** of any kind. `grep -i 'token|auth|secret|password'`
    against the file returns zero matches. Any process on the LAN that can
    reach port 9876 gets full control.
  - Exposes an `execute_code` handler (line 110) that runs
    `exec(code, ns)` with `bpy` and `mathutils` in scope and **no
    sandboxing** — no restricted builtins, no `os`/`subprocess` denylist,
    no path constraints. An attacker who reaches the port has arbitrary
    Python execution inside Blender, which can read files, write files,
    spawn subprocesses, and exfiltrate data.
  - Auto-starts on Blender launch (`autostart()` at line 179, registered as
    a `bpy.app.timers` callback in `register()` at line 187), so the user
    never opts in; merely launching this Blender build opens the port.
- **The MCP "tool surface" is shallow compared to the upstream community
  provider.** The handler dictionary (lines 90-98) has 4 real handlers
  (`execute_code`, `get_scene_info`, `get_object_info`,
  `get_viewport_screenshot`) plus 3 stubs that return
  `"not ported to native yet"` for PolyHaven, Hyper3D, Sketchfab. The
  upstream `uvx blender-mcp` provider that
  `03_implementation/src/hermes3d/adapters/blender_mcp.py:25-31` already
  targets exposes the full surface. So the fork is a strict **subset**
  feature-wise, not a superset.
- **Protocol is not actually MCP.** Despite the name, the server speaks
  newline-delimited JSON over a raw TCP socket (`_handle_client`, lines
  61-84) — not MCP-over-stdio and not MCP-over-HTTP-SSE. A real MCP client
  cannot speak to it without a translator. Adopting it would require
  Hermes3D to maintain that translator forever, while the upstream
  community provider already speaks MCP natively.
- **Build cost is prohibitive.** Adopting this fork means Hermes3D
  contributors must build Blender from source on every supported platform
  (Windows, Linux, optionally macOS). Upstream Blender's
  build-from-source guide allocates 8-16 GB of disk and 30-90 minutes on
  modern hardware. The skill-store user persona (Dave running a 12-printer
  hobby farm on a workstation) cannot reasonably be asked to build Blender
  to use Hermes3D. The current adapter's `uvx blender-mcp` flow is a
  one-line install.
- **The "Fedora 44 + ROCm 7.2 fixes" co-mingled in the same commit are
  out of scope for Hermes3D.** Even if one wanted the build fixes, they
  are inseparable from the MCP code in commit `3f66527`. Cherry-picking
  is impractical because it is a single 12,936-file initial commit, not
  a series of focused patches.

**Positive consequences of REJECT:**

- Hermes3D keeps its license posture clean (no GPL-3 vendoring).
- No new attack surface: the `BlenderMCPServer` 0.0.0.0:9876 backdoor never
  reaches a Hermes3D user.
- Phase 3 wiring against `uvx blender-mcp` proceeds on the original timeline
  — no rework of the existing adapter skeleton required.
- The "Future / Pending Audits" row in `ROADMAP.md` documents the
  investigation so a future contributor doesn't re-litigate it.

**Negative consequences of REJECT:**

- We do not capture the fork's "Fedora 44 / ROCm 7.2" build fixes. Cost is
  acceptable: those fixes belong upstream in Blender, not in Hermes3D, and
  the audit found no evidence they were ever proposed upstream.
- A future, well-engineered "Blender with built-in MCP" project — e.g. one
  that ships as an addon, listens on loopback only, requires a token, and
  sandboxes `execute_code` — could still be adopted. Rejecting this
  particular repo does not preclude that.

## Alternatives considered

1. **ADOPT as primary Blender path.** Rejected: GPL-3 vendoring conflict,
   single-commit unmaintained snapshot, RCE-by-default network surface,
   non-MCP wire protocol, strict feature subset of upstream community
   provider.
2. **FORK + harden** (vendor `blender_mcp.py` only, not the whole Blender
   tree, then add token auth + loopback bind + sandbox). Rejected for two
   reasons: (a) the file would still be GPL-3 by inheritance from Blender,
   re-creating the licensing problem; (b) the extracted code is 196 lines
   that any of the existing community Blender-MCP providers solve more
   completely — there's no IP worth forking.
3. **Keep `blender_mcp.py` adapter as-is, talking to upstream
   `uvx blender-mcp`.** **Selected.** This is the status quo. Phase 3
   wiring (`claude mcp list` confirmation, real `version()` probe) goes on
   as planned in the existing skeleton.
4. **Build a new Blender MCP from scratch** under Hermes3D's own license,
   using the official Blender Python API. Deferred. If the upstream
   community provider's roadmap stalls, this becomes the right move; today
   it would be premature optimization.

## References

- Repo URL: https://github.com/rakaarwaky/blender-mcp-native
- Last commit at audit time: `3f6652783bff68198698fd668dbe82c65b5b3908`
  (2026-04-26, "Initial commit with native MCP support and Fedora 44 build
  fixes")
- Repo metadata at audit time: 0 stars, 1 fork, 0 open issues, 0 releases,
  1 commit on `main`.
- License file: `COPYING` (top-level) — declares GPL-3 only; `README.md`
  confirms "GNU General Public License, Version 3."
- MCP-specific code: `scripts/startup/blender_mcp.py` (196 lines, the only
  file that diverges in spirit from upstream Blender's `scripts/startup/`).
- Existing Hermes3D adapter:
  `03_implementation/src/hermes3d/adapters/blender_mcp.py` (skeleton,
  Phase-1 detect/version/capabilities only).
- Upstream community provider targeted by the existing adapter:
  `uvx blender-mcp` (PyPI / `uv` runner).
- Blender source-tree licensing reference:
  https://www.blender.org/about/license
- Audit clone path (workspace-relative, ignored via `tmp/` in `.gitignore`):
  `tmp/audit-blender-mcp-native`.
