# LEDGER.md — append-only archive of resolved/expired STREAM messages

> Both sides are forbidden from deleting or rewriting entries here.
> The Layer S — STREAM hygiene gate enforces append-only via diff check.
> SCRIBE moves messages here from CLAUDE_INBOX/CODEX_INBOX after they reach
> `resolved` or `expired` and are >6h old.

---

## 2026-05-03 — bootstrap

```text
2026-05-03T11:30:00Z  STREAM/ initialized in both repos by Claude SCRIBE
2026-05-03T11:30:00Z  PROTOCOL.md v1 written, mirrored to HermesProof
2026-05-03T11:30:00Z  STATE.md initial snapshot
2026-05-03T11:30:00Z  GATE_GAP_QUEUE.md seeded (18 items: 6 P0, 8 P1, 4 P2)
2026-05-03T11:30:00Z  ENHANCEMENT_QUEUE.md seeded (9 items: 3 P0, 4 P1, 2 P2)
2026-05-03T11:30:00Z  CODEX_INBOX bootstrapped with 5 opening messages (boot-stream-v1, 3 TASK_CLAIMED, 1 QUESTION)
2026-05-03T11:30:00Z  CLAUDE_INBOX initialized empty (Codex's first ACK arrives next cycle)
```

---
