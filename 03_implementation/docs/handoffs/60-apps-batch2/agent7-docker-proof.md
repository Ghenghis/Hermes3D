# Agent 7 — Docker Proof Lane Validator (`python:3.11-slim`)

> Read-only audit of the Cplus-py311+docker lane (formally deferred 2026-05-09). No source mutation, no `docker run`, no pytest re-execution. Validates Phase 4 patch shape on slim image and forecasts residual surface.

## Lane classification

`env-bound` — 18 of 20 residuals are environment-persistent on `python:3.11-slim`; 2 are cross-test transients in xdist. Zero are v0.13.0 regressions; zero are Hermes3D wrapper bugs; the patch shape itself is well-formed.

## Phase 4 patch shape validation (against §7 v2 sketch)

Pytest invocation `python -m pytest <tests_dir> -m "not integration" --ignore=tests/integration --ignore=tests/e2e --maxfail=<n> -q -n <workers>` is **well-formed** — `--ignore` is a stdlib pytest collection flag (path-based, runs before conftest import), `-m` is selection-time, and `-n` is xdist-recognized when xdist is in `pyproject.toml`. The arg order is interpreter-safe; the pre-existing live `_run_update_checks` (lines 356-359) already uses the same general shape — only the `--ignore` pair, `-n` worker, and `--maxfail` value differ.

Agent-6 must-fix survival on `python:3.11-slim`:

- **#1 skip path fail-closed**: PASS. `requires_confirmation` returns status `fail` with explicit text — slim image cannot bypass the gate by env-omission.
- **#2 workers≥2 in production**: PASS. `HERMES_AGENT_PYTEST_WORKERS in ("0","1")` rejected unless `HERMES_AGENT_DIAGNOSTIC=1`. Slim image has 1 vCPU minimums available; production check valid.
- **#3 meta-test (upstream tests.yml watch)**: PASS analytically. Test fetches `tests.yml` via GitHub API; slim image has `urllib` stdlib so no extra deps needed.
- **#4 maxfail=1 default**: PASS. `maxfail = "5" if diagnostic_mode else "1"` — diagnostic-only widening.
- **#5 firmware archive-dir audit**: PASS (orthogonal to Docker lane; schema-validator scope, no slim-image impact).

CONCERN: none of the 5 guards cover the **WSL-kernel-string leak** (`/proc/version` containing `microsoft` inside Docker Desktop on Windows). That false-positive on `is_wsl()` is the root cause of 10/20 residuals and is upstream-bound (issue #22420), not patch-bound.

## Residual failure forecast on slim image

| Category | Count | Persists on slim? | Root cause |
|---|---|---|---|
| systemd / user D-Bus / WSL detect | 10 | YES | slim has no `systemd-as-PID1`; `dbus-user-session` not installed; `is_wsl()=True` due to Docker Desktop WSL2 kernel |
| Audio / PulseAudio / ALSA | 4 | YES | slim has zero audio runtime (no `libpulse0`, `libasound2`, `sounddevice`) |
| Process / signal / git-config | 4 | YES | PID-namespace + cgroup quirks identical on any `*-slim`; not specific to Python tag |
| Cross-test transient (xdist) | 2 | YES (timing-bound) | parallel ordering flakes; orthogonal to image |

Forecast verdict: **all 20 residuals reproduce on `python:3.11-slim`**. Switching to `python:3.11` (full buildpack-deps) would only resolve a subset of #3 (extra system libs); systemd + audio + WSL-kernel-leak would still surface.

## Receipt #1 — Docker Hub `python` official image (primary)

- **URL**: https://hub.docker.com/_/python
- **Claim**: "This image does not contain the common Debian packages contained in the default tag and only contains the minimal Debian packages needed to run `python`." Slim variant explicitly omits `buildpack-deps`-class packages (which include `dbus`, `libpulse0`, `libasound2`, `systemd`).
- **Impact**: Validates that 14 of 20 residuals (10 systemd + 4 audio) are deterministic absences, not test bugs. Hermes Agent's full pytest suite assumes a non-minimal Linux runtime.
- **Risk**: Even `python:3.11` (full) does not ship `systemd-as-PID1`; only `ubuntu:24.04` + explicit `dbus-user-session` install + `--cgroupns=host` will pass the systemd-D-Bus tests. So upgrading from slim to full Python **does not unlock** the systemd cluster.

## Receipt #2 — `geerlingguy/docker-ubuntu2404-ansible` (cross-project)

- **URL**: https://github.com/geerlingguy/docker-ubuntu2404-ansible/blob/master/Dockerfile
- **Claim**: Explicitly uses `FROM ubuntu:24.04` (not any `python:*-slim`); installs `systemd systemd-cron`; declares `VOLUME ["/sys/fs/cgroup", "/tmp", "/run"]`; runs `CMD ["/lib/systemd/systemd"]` as PID1. Battle-tested for systemd-in-container Ansible test harnesses.
- **Impact**: Confirms the canonical pattern for projects that need real systemd inside a container is `ubuntu:24.04` + cgroup mount + systemd-as-PID1 — not `python:*-slim`. Maps 1:1 to the residual-10 systemd cluster on Cplus-docker.
- **Risk**: The `ubuntu:24.04` template requires `--cgroupns=host` and `--privileged` (or fine-grained capabilities) at `docker run` time — increases attack surface vs slim. Mitigatable with `--security-opt seccomp=unconfined` only on the proof lane (never production).

## Recommendation

Keep `python:3.11-slim` for the **fast-feedback proof lane** (compileall + 5530-test core suite) but **add a second proof env** based on `ubuntu:24.04` + `dbus-user-session` + `pulseaudio --no-daemon` + systemd-as-PID1 for the **full v0.13.0 acceptance gate** when upstream lands `is_container()/is_wsl()` skipif decorators (issue #22420). Two-tier matrix:

1. **Tier 1 — `python:3.11-slim`**: ~5530 fast tests + Phase 4 v2 patch; expected `verified=true` once #22420 lands.
2. **Tier 2 — `ubuntu:24.04` fuller**: 20 currently-residual tests; gated behind explicit user opt-in via `HERMES_AGENT_FULL_ENV=1`, mirroring the existing `HERMES_AGENT_RUN_PYTEST` pattern.

Switching the entire Docker proof lane to `ubuntu:24.04` now would mask the cleaner slim signal (we'd lose the ability to detect a regression that requires a full system runtime to surface) and re-introduce systemd-as-PID1 attack surface to the default path. Two-tier preserves both signals and keeps the standing merge auth gate hard.
