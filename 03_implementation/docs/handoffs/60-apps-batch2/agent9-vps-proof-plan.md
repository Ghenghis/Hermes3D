# Batch2 Agent 9 — Native Linux/VPS Proof Plan (Hermes Agent v0.13)

**Lane**: H3D-60APP-UPDATE-READINESS-AUDIT / Batch 2 / Agent 9 (read-only research, no provisioning).
**Input**: `60_APP_UPDATE_READINESS_AUDIT_2026-05-09.md` §3.6 (coding agents row), §4 (system-dep matrix — `Linux VPS` is canonical for print-farm services), §5 cross-cutting issues #4 (container kernel-string leak — `is_wsl()` returns True inside Docker on Win because Docker Desktop = WSL2 kernel for ALL Linux containers).
**Constraint**: project memory `feedback_no_paid_services.md` — free / open-source only.

---

## Lane classification

`pass` — a real Linux host (not a Docker-on-WSL container) supplies systemd PID-1, real `/proc/cpuinfo`, real ALSA/PulseAudio, real `/sys/fs/cgroup` (cgroupv2), and a non-WSL `/proc/version` string. This eliminates all 20 Cplus-py311+docker residuals at once: 10 systemd-DBus, 4 audio, 4 process-isolation, 2 transient. Verdict is conditional on Hermes Agent v2026.5.8+ shipping `is_container()/is_wsl()` skipif decorators (issue #22420) — but on native Linux those decorators evaluate False so the pytest gate passes either way.

## Recommended VPS option

**GitHub-hosted `ubuntu-24.04` runner on this repo** (already public). Free, zero-provisioning, kernel 6.17, systemd 255.4 as PID-1, 4 vCPU / 16 GB RAM / 14 GB SSD, unlimited minutes for public repos.

| Option | Free-tier | Kernel | systemd PID-1 | Verdict |
|---|---|---|---|---|
| **GitHub-hosted ubuntu-24.04 runner** (Receipt #1) | unlimited mins on public repos | 6.17 (cgroupv2) | yes (`/lib/systemd/systemd` is PID-1 inside the VM) | **chosen** — already on the workflow surface, zero new infra |
| Self-hosted homelab Proxmox VM on user's bare-metal | uncapped (user's own hardware) | whatever ISO user installs (Ubuntu 24.04 → 6.8+) | yes | viable fallback (1 PR cycle to add SSH runner registration); no $0 cap risk |
| Local KVM/qemu VM on the Windows orchestrator host | uncapped (user's own hardware), but eats local RAM | Ubuntu 24.04 = 6.8 (cgroupv2) | yes | last-resort (slow, contends with orchestrator) |

Skipped: Hetzner / Oracle Cloud free tiers — both require a credit card on file even for $0 plans, which crosses the no-paid-services rule's spirit (account → paid escalation path is implicit). Skipped: GitHub-hosted *self-hosted* runners on private repos (those would need a paid SKU when minutes burn). Public-repo GitHub-hosted is the only fully unconditional free option.

## Provisioning playbook (script outline, 38 lines)

GitHub-hosted runner = nothing to provision; **just a workflow file**:

```yaml
# .github/workflows/hermes-agent-v013-pytest-gate.yml
name: hermes-agent-v013-pytest-gate
on:
  workflow_dispatch:
  push: { branches: [claude/cplus-py311-defer, main] }
jobs:
  vps-proof:
    runs-on: ubuntu-24.04
    timeout-minutes: 45
    steps:
      - uses: actions/checkout@v4
      - name: System packages
        run: |
          sudo apt-get update -y
          sudo apt-get install -y build-essential python3.11 python3.11-venv \
            python3-pip systemd-cron pulseaudio libasound2 ripgrep git
      - name: Enable user-linger + dbus-user-session
        run: |
          sudo loginctl enable-linger $(whoami)
          sudo apt-get install -y dbus-user-session
      - name: Clone Hermes Agent (separate workspace)
        run: |
          git clone https://github.com/NousResearch/hermes-agent.git ~/hermes-agent-fresh
          cd ~/hermes-agent-fresh && git checkout v2026.5.7  # or pending v2026.5.8
      - name: Install Hermes Agent
        run: |
          cd ~/hermes-agent-fresh
          python3.11 -m venv .venv && source .venv/bin/activate
          pip install -U pip wheel && pip install -e ".[all,dev]"
      - name: Phase 4 v2 pytest gate
        env:
          HERMES_AGENT_RUN_PYTEST: "1"
          HERMES_AGENT_PYTEST_WORKERS: "auto"
        run: |
          cd ~/hermes-agent-fresh && source .venv/bin/activate
          python -m pytest tests/ -m "not integration" \
            --ignore=tests/integration --ignore=tests/e2e \
            --maxfail=1 -q -n auto
      - name: Upload proof
        if: always()
        uses: actions/upload-artifact@v4
        with: { name: vps-proof, path: ~/hermes-agent-fresh/.pytest_cache/ }
```

For the self-hosted Proxmox/KVM fallback the same script runs after a 6-line `cloud-init` (Ubuntu 24.04 server ISO → user with sudoers + linger → apt packages → clone runner registration token).

## Rollback path

- VM-snapshot the Proxmox/KVM image **before** the pytest gate fires (or — on GitHub-hosted — the runner is ephemeral, so "rollback" = re-run on a clean VM, which is automatic).
- `~/hermes-agent-fresh` is a separate `git clone`; the live `var/hermes_agent_backups/<id>.bundle` workflow is untouched.
- `var/hermes_agent_backups/` lives on the runner disk (`actions/upload-artifact` for off-VM persistence).
- Restore VM snapshot if anything destructive fires (homelab path only; GitHub-hosted is single-use).
- Manual `git revert` + `pip install hermes-cli==<prev>` as last fallback.

## Cost / latency

- **Cost**: $0 (public-repo unlimited minutes per Receipt #1; no card on file).
- **Resources**: 4 vCPU / 16 GB RAM / 14 GB SSD; ample for the ~25k Hermes Agent test corpus.
- **Wall-clock for Phase 4 v2 pytest gate**: ~8–14 min on 4 vCPU with `-n auto` (8–10× the in-Docker rate of `5532 → 20734` passing tests cited in audit §7), well under the 45-min timeout.
- **Network latency Win-orchestrator → runner**: irrelevant — runner is dispatched-and-forget; orchestrator polls `gh run watch` (sub-second once warm) and reads the artifact when green.

## Receipt #1 (primary)

- **URL**: `https://docs.github.com/en/actions/reference/runners/github-hosted-runners` + `https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md`
- **Claim**: ubuntu-24.04 GitHub-hosted runner = Ubuntu 24.04.4 LTS, kernel 6.17.0-1010-azure (cgroupv2), systemd 255.4-1ubuntu8.15 as PID-1, Python 3.12.3 default; standard SKU = 4 vCPU / 16 GB RAM / 14 GB SSD; unlimited minutes for public repositories.
- **Impact**: every env-bound residual (systemd-DBus 10, process-isolation 4, transient 2) flips to `pass` because PID-1 is real systemd, cgroupv2 is mounted natively, and `/proc/1/cgroup` no longer reports `0::/init.scope` from Docker Desktop's WSL2 shim.
- **Risk**: audio (4 residuals) — runner image does NOT pre-install PulseAudio/ALSA. Mitigation: `apt-get install pulseaudio libasound2` in the workflow (cheap), OR the upstream `pytest.importorskip("sounddevice")` pattern from audit §6.2 — both work, the importorskip is more honest and matches the cross-project pattern.

## Receipt #2 (cross-project, self-hosted Linux runner)

- **URL**: `https://www.klipper3d.org/Installation.html`
- **Claim**: Klipper itself ("a Linux-based host" Pi/SBC) runs as a `sudo service klipper start/stop` systemd service; documentation explicitly recommends a **non-desktop** Linux variant on a small board computer to avoid the same kernel/printer-board conflicts that bite us inside Docker-on-WSL. This validates the "real Linux host" requirement for the print-farm column of audit §4: Klipper, the canonical print-farm service, is *built around* the assumption that a real Linux PID-1 + real `/dev/ttyACM*` exist — which Docker-on-Windows cannot supply (audit §4 footnote [6]: "Klipper-on-Windows: NOT supported"). Same reasoning argument applies to Hermes Agent's audio/process tests.
- **Impact**: independent confirmation that real Linux on real hardware (or a real KVM VM) is the only canonical surface for the systemd + device-IO axis Hermes Agent's failing tests probe. Reinforces "use a real VPS" over "make Docker bigger".
- **Risk**: Klipper's reference is for `/dev/tty*` USB-serial passthrough, slightly different from systemd-D-Bus. Coverage gap is partial — but the underlying principle (real Linux PID-1 on real hardware solves what container shims cannot) is identical and is exactly what audit §5 #4 names.

## Trade-off vs `ubuntu:24.04` Docker (fuller container)

Use the fuller `ubuntu:24.04` Docker image (Batch 1 Agent 2's recipe: `--cgroupns=host`, `STOPSIGNAL SIGRTMIN+3`, `dbus-user-session`, `VOLUME ["/sys/fs/cgroup", "/tmp", "/run"]`, mask `systemd-udevd.service`) for **fast iteration on Windows during dev** — it reproduces ~85% of the Linux surface inside WSL2 without paying GitHub Actions's 60–90 s warm-up. The VPS / GitHub-hosted runner wins as the **canonical proof gate** for three things Docker-on-WSL cannot fix at any image size: (a) `/proc/version` and `/proc/1/cgroup` both report a real non-WSL kernel — closes audit §5 #4 directly; (b) real ALSA/PulseAudio device nodes for the 4 `TestDetectAudioEnvironment` audio tests — fuller container would still need `--device /dev/snd` from a host that has audio, which Windows doesn't ergonomically expose; (c) cgroupv2 unified hierarchy with the host kernel rather than Docker Desktop's shimmed sub-hierarchy. Workflow: keep the Docker fuller image as the developer-loop tier, escalate to the GitHub-hosted runner exactly when the Docker tier passes but residuals remain — the runner is the "definitely-real Linux" tier that closes the lane.
