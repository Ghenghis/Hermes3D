"""SQLite append-only orchestration event ledger."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from .types import Verdict


@dataclass(frozen=True)
class LedgerEvent:
    ts_utc: str
    run_id: str
    agent_id: str
    tool: str
    inputs_sha: str
    outputs_sha: str
    verdict: Verdict
    message: str


class OrchestrationLedger:
    """Append-only event log for offline orchestration decisions."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def append(self, event: LedgerEvent) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (
                    ts_utc,
                    run_id,
                    agent_id,
                    tool,
                    inputs_sha,
                    outputs_sha,
                    verdict,
                    message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.ts_utc,
                    event.run_id,
                    event.agent_id,
                    event.tool,
                    event.inputs_sha,
                    event.outputs_sha,
                    event.verdict,
                    event.message,
                ),
            )
            return int(cursor.lastrowid)

    def events(self, run_id: str | None = None) -> tuple[LedgerEvent, ...]:
        query = """
            SELECT
                ts_utc,
                run_id,
                agent_id,
                tool,
                inputs_sha,
                outputs_sha,
                verdict,
                message
            FROM events
        """
        params: tuple[str, ...] = ()
        if run_id is not None:
            query += " WHERE run_id = ?"
            params = (run_id,)
        query += " ORDER BY rowid ASC"

        with self._connect() as conn:
            rows = list(conn.execute(query, params))

        return tuple(LedgerEvent(*row) for row in rows)

    def stable_sha(self, run_id: str | None = None) -> str:
        event_dicts = [asdict(event) for event in self.events(run_id)]
        payload = _canonical_json(event_dicts).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    ts_utc TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    inputs_sha TEXT NOT NULL,
                    outputs_sha TEXT NOT NULL,
                    verdict TEXT NOT NULL CHECK (verdict IN ('pass', 'fail', 'skip')),
                    message TEXT NOT NULL
                )
                """
            )


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
