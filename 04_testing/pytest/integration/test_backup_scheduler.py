from __future__ import annotations

import time
from pathlib import Path


def test_backup_scheduler_creates_archives_and_prunes_to_retain_count(tmp_path: Path) -> None:
    from hermes3d.core.farm.print_history import PrintHistory
    from hermes3d.core.farm.spool_tracker import SpoolTracker
    from hermes3d.core.memory import SkillStore
    from hermes3d.core.notifications import Notifier
    from hermes3d.core.supervisor.daemon import BackupPolicy, PrintSupervisor, SupervisorPolicy

    state_dir = tmp_path / "var"
    state_dir.mkdir()
    (state_dir / "queue.json").write_text('{"jobs":[]}\n', encoding="utf-8")
    spools = SpoolTracker(state_dir / "spools.json")
    spools.add(
        material="PLA", color="black", color_hex="#000000", vendor="test", initial_grams=1000
    )
    target_dir = tmp_path / "backups"

    supervisor = PrintSupervisor(
        history=PrintHistory(state_dir / "history.jsonl"),
        spools=spools,
        skills=SkillStore(state_dir / "skills.json"),
        notifier=Notifier(discord_url=None, slack_url=None, generic_url=None),
        policy=SupervisorPolicy(poll_interval_s=0.05),
        state_dir=state_dir,
        backup_policy=BackupPolicy(
            enabled=True,
            interval_minutes=0.05,
            retain_count=1,
            target_dir=target_dir,
        ),
        printer_ids=(),
    )

    seen: set[str] = set()
    supervisor.start()
    try:
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            current = {path.name for path in target_dir.glob("*.tar.gz")}
            seen.update(current)
            if len(seen) >= 2 and len(current) == 1:
                break
            time.sleep(0.1)
    finally:
        supervisor.stop(timeout=2.0)

    current = sorted(target_dir.glob("*.tar.gz"))
    assert len(seen) >= 2
    assert len(current) == 1
