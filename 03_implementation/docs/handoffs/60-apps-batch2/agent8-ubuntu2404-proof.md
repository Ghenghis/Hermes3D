# Batch 2 Agent 8 — ubuntu:24.04 Proof Lane Plan

> Read-only plan. No source mutation, no build, no run.
> Builds on Batch 1 Agent 2 §6.2 — fuller container closing 18 env-bound residuals (10 systemd-DBus + 4 audio + 4 process) the slim image hit on Hermes Agent v0.13.0 lane Cplus-py311+docker.

## Lane classification

`pass` (conditional — `pass` if the Phase 4 v2 patched pytest invocation runs INSIDE this container with all 18 residuals resolved; `env-bound` for any that persist; `is_container()/is_wsl()` skipif decorators stay `upstream-bound` regardless until issue #22420).

## Canonical Dockerfile

```dockerfile
# WHY ubuntu:24.04: Canonical LTS, /lib/systemd/systemd at PID 1 viable;
# python:3.11-slim cannot host systemd (no init, no D-Bus, no PulseAudio).
FROM ubuntu:24.04

# WHY noninteractive: avoid tzdata / debconf prompts during apt build.
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    container=docker

# WHY package set:
#  - systemd + dbus-user-session: closes 10 systemd-DBus residuals (user bus + linger).
#  - pulseaudio + libasound2 + alsa-utils: closes 4 audio residuals (TestDetectAudioEnvironment).
#  - python3.11 + venv + pip: matches upstream tests.yml uv Py3.11.
#  - sudo: loginctl enable-linger + sudo -u hermes hand-off.
#  - ca-certificates + curl: HTTPS to PyPI / GitHub.
#  - ripgrep + git: parity with Hermes3D dev shell.
#  - tini: PID-1 reaper for ad-hoc exec; systemd remains main PID 1.
RUN apt-get update && apt-get install -y --no-install-recommends \
        systemd systemd-sysv dbus dbus-user-session \
        pulseaudio pulseaudio-utils libasound2t64 alsa-utils \
        python3.11 python3.11-venv python3-pip python3-dev \
        sudo ca-certificates curl ripgrep git tini \
    && rm -rf /var/lib/apt/lists/*

# WHY mask udevd: geerlingguy pattern. Without it, systemd-udevd loops in
# unprivileged containers (no /dev access).
RUN systemctl mask \
        systemd-udevd.service systemd-udevd-control.socket \
        systemd-udevd-kernel.socket systemd-firstboot.service \
        systemd-modules-load.service \
        sys-kernel-debug.mount sys-kernel-tracing.mount

# WHY user + linger: audio + user-session paths need /run/user/1000/bus.
# linger creates it on boot, not on login — pytest is non-interactive.
RUN useradd -m -s /bin/bash -u 1000 hermes \
    && echo "hermes ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/hermes \
    && mkdir -p /var/lib/systemd/linger \
    && touch /var/lib/systemd/linger/hermes

# WHY VOLUME: CONTAINER_INTERFACE spec. cgroup host-mapped (NOT sub-hierarchy);
# /run + /tmp tmpfs avoids stale-PID conflicts across restarts.
VOLUME ["/sys/fs/cgroup", "/run", "/tmp"]

# WHY SIGRTMIN+3: systemd graceful-shutdown signal. SIGTERM skips ordered
# teardown; SIGKILL leaves /run dirty.
STOPSIGNAL SIGRTMIN+3

# Entrypoint is invoked by oneshot unit AFTER systemd boots; CMD stays systemd.
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# WHY absolute path: per CONTAINER_INTERFACE, /sbin/init symlinks can drift.
CMD ["/lib/systemd/systemd"]
```

## `docker run` command

```bash
docker run --rm -it \
  --name hermes-agent-proof \
  --cgroupns=host \
  --tmpfs /run \
  --tmpfs /tmp \
  -v /sys/fs/cgroup:/sys/fs/cgroup:rw \
  --stop-signal=SIGRTMIN+3 \
  -e HERMES_AGENT_RUN_PYTEST=1 \
  -e HERMES_AGENT_PYTEST_WORKERS=auto \
  hermes-agent-proof:ubuntu2404
```

**`--privileged` trade-off:** Agent 2 recommends `--privileged` first-iteration to skip cap-drop debugging. Non-privileged works on Docker ≥ 20.10 + cgroup v2 with `--cgroupns=host` + `/sys/fs/cgroup:rw` + udevd mask all in place. **Decision:** start non-privileged; escalate only if a residual maps to `CAP_SYS_ADMIN` / `CAP_AUDIT_WRITE` (typical: cgroup writes from user units).

## Entrypoint script (pseudocode)

```bash
#!/usr/bin/env bash
# Invoked by oneshot unit AFTER systemd reports running, OR via docker exec.
set -euo pipefail

# 1. Wait for user-session bus for uid 1000 (hermes).
until [ -S /run/user/1000/bus ]; do sleep 0.5; done

# 2. Start PulseAudio for hermes (deterministic gate before audio tests).
sudo -u hermes -i bash -c \
  'pulseaudio --check || pulseaudio --start --exit-idle-time=-1'

# 3. Hand off to pytest with Phase 4 v2 patched invocation.
exec sudo -u hermes -i \
  env HERMES_AGENT_RUN_PYTEST=1 HERMES_AGENT_PYTEST_WORKERS=auto \
  python3.11 -m pytest /home/hermes/hermes-agent/tests \
    -m "not integration" \
    --ignore=tests/integration --ignore=tests/e2e \
    --maxfail=1 -q -n auto
```

## Image-size budget

Agent 2's ~600 MB+ holds. vs `python:3.11-slim` (~125 MB compressed): ubuntu base ~78 MB + systemd/dbus ~85 MB + pulseaudio/alsa ~110 MB + python3.11+venv ~95 MB + ripgrep/git/sudo/tini/curl ~35 MB ≈ **~400 MB compressed / 600–700 MB uncompressed**. Inherent cost of in-container systemd-DBus + audio; no slim path exists.

## Receipt #1 (primary — official)

- **URL**: https://hub.docker.com/_/ubuntu (tags page, `24.04` aka `noble`, digest-pinned by Canonical).
- **Claim**: ubuntu:24.04 is the LTS base with systemd-as-PID-1 viable; Canonical signs pushes and publishes SHA256 digests; `/lib/systemd/systemd` lives at the documented path.
- **Impact**: anchors `FROM`; image-digest pin (NOT `:latest`) required for reproducible proof builds.
- **Risk**: `:latest` drifts — must pin to digest in the staged update lane so Canonical rebasing mid-build cannot invalidate proofs.

## Receipt #2 (cross-project — different from geerlingguy in §6.2)

- **URL**: https://catalog.redhat.com/software/containers/ubi9-init/6183297540a2d8e95c82e8d6 — Red Hat UBI9-Init, industry-standard "systemd-in-container" reference outside the Ansible-test ecosystem.
- **Claim**: UBI9-Init ships systemd pre-configured with udevd masked, `VOLUME ["/sys/fs/cgroup"]`, `STOPSIGNAL SIGRTMIN+3`, documented `--cgroupns=host` — confirms every Dockerfile decision above and proves the pattern is industry-standard, not Ansible-specific.
- **Impact**: validates non-privileged path; cross-confirms `STOPSIGNAL SIGRTMIN+3` + `/lib/systemd/systemd` CMD; usable as fallback base if ubuntu:24.04 regresses.
- **Risk**: UBI9 uses dnf/yum + Py3.9 default; not drop-in. Cross-validation reference only — adopting as alt base would widen the test matrix.

## Open questions

- Does `loginctl enable-linger` via `/var/lib/systemd/linger/hermes` survive container recreate, or do we need an idempotent oneshot unit re-running `loginctl enable-linger hermes` at boot?
- Are the 4 process residuals (separate from systemd-DBus + audio) bound to `CAP_SYS_PTRACE` / `/proc/1/cgroup`-read-by-uid-1000 — needing `--cap-add=SYS_PTRACE` even with user-session bus working?
- Will Phase 4 v2 `--ignore=tests/integration` + `-n auto` xdist cooperate with the user-session bus, or does xdist fork before bus-bind and miss `/run/user/1000/bus` in workers (forcing `-n 0` diagnostic mode)?
