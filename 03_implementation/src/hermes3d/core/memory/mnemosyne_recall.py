"""Soft-import wrapper around the optional ``mnemosyne-memory`` package.

Status: runnable
Contract: 02_architecture/adr/ADR-014-mnemosyne-recall-layer.md

This is a *recall layer* — it surfaces hints from prior runs to bias
agentic decisions. It is **NOT** the source of truth for any decision.
The evidence ledger (``.hermes3d_orchestrator/evidence/ledger.ndjson``
and the ``var/proof-bundles/`` artefacts) remains canonical. If the
recall layer disagrees with the ledger, the ledger wins.

Design principles:
  - **Soft import.** Mnemosyne is an OPTIONAL extra. When the package
    is not installed every method on :class:`MnemosyneRecall` degrades
    to a safe no-op (returns ``None`` / ``[]`` / does nothing). The
    fleet keeps printing.
  - **No silent swallowing.** Failures are logged at WARNING with
    enough context to debug; we never re-raise.
  - **Pure-data hand-off to dispatcher.** Recall hints are pre-resolved
    upstream by the orchestrator and threaded into ``DispatchRequest``
    as immutable :class:`RecallHint` tuples. The dispatcher itself
    stays pure (no I/O, no DB reads in scoring).
  - **API verified against mnemosyne-memory v2.2 on PyPI** (2026-05-03).
    Module-level ``mnemosyne.remember(content, source, importance, ...)``
    and ``mnemosyne.recall(query, top_k=5, ...)``; class form is
    ``mnemosyne.core.memory.Mnemosyne(session_id, db_path, ...)``.
    The original audit notes referred to a non-existent
    ``MnemosyneStore`` class — the real class is just ``Mnemosyne``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LOG = logging.getLogger(__name__)


# Default DB location — co-located with the orchestrator's other state
# so backup tooling picks it up automatically.
DEFAULT_RECALL_DB = Path(".hermes3d_orchestrator") / "mnemosyne" / "recall.sqlite"


@dataclass(frozen=True)
class RecallHint:
    """An immutable hint resolved from the recall layer.

    Hints are produced by :meth:`MnemosyneRecall.recall` and threaded
    through the orchestrator into :class:`hermes3d.core.agents.dispatcher.DispatchRequest`
    as ``recall_hints``. The dispatcher reads them as plain data — no
    I/O, no DB calls in the scoring path.

    Fields mirror the ``recall()`` result dict from mnemosyne-memory
    plus an ``importance`` float so dispatcher scoring can scale by it.
    """

    memory_id: str
    content: str
    source: str
    importance: float = 0.5
    score: float = 0.0  # mnemosyne's ranking score (higher is better)


class MnemosyneRecall:
    """Soft-import wrapper around mnemosyne-memory.

    All methods degrade to safe no-ops when the package is unavailable
    or any operation raises. Construct via :func:`default_recall` for
    typical use; pass an explicit ``db_path`` for tests.
    """

    def __init__(
        self,
        db_path: Path | str | None = None,
        *,
        session_id: str = "hermes3d-orchestrator",
    ) -> None:
        self._db_path = Path(db_path) if db_path is not None else DEFAULT_RECALL_DB
        self._session_id = session_id
        self._impl: Any = None
        self._available: bool = False
        self._init_impl()

    # ------------------------------------------------------------------
    # Soft init — never raises
    # ------------------------------------------------------------------

    def _init_impl(self) -> None:
        """Attempt to construct the underlying ``Mnemosyne`` instance.

        Failure is logged at WARNING; the wrapper falls into degraded
        mode with ``self._available = False``.
        """
        try:
            from mnemosyne.core.memory import Mnemosyne  # type: ignore[import-not-found]
        except ImportError as exc:
            LOG.info(
                "mnemosyne-memory not installed; recall layer disabled "
                "(install with `pip install mnemosyne-memory`): %s",
                exc,
            )
            return
        except Exception as exc:  # pragma: no cover - extremely unusual
            LOG.warning(
                "Unexpected error importing mnemosyne (%s); recall disabled: %s",
                type(exc).__name__,
                exc,
            )
            return

        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._impl = Mnemosyne(session_id=self._session_id, db_path=self._db_path)
            self._available = True
            LOG.debug(
                "MnemosyneRecall ready (session=%s, db=%s)",
                self._session_id,
                self._db_path,
            )
        except Exception as exc:
            LOG.warning(
                "Mnemosyne init failed at %s (%s: %s); recall disabled",
                self._db_path,
                type(exc).__name__,
                exc,
            )
            self._impl = None
            self._available = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """``True`` iff a real Mnemosyne instance is wired up."""
        return self._available

    def remember(
        self,
        content: str,
        *,
        source: str = "hermes3d",
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """Store a memory. Returns the new memory id, or ``None`` if
        the recall layer is unavailable or the call fails."""
        if not self._available or self._impl is None:
            return None
        try:
            mem_id = self._impl.remember(
                content=content,
                source=source,
                importance=float(importance),
                metadata=metadata or {},
            )
            return str(mem_id) if mem_id is not None else None
        except Exception as exc:
            LOG.warning(
                "Mnemosyne.remember failed (%s: %s); skipping",
                type(exc).__name__,
                exc,
            )
            return None

    def recall(
        self,
        query: str,
        *,
        top_k: int = 5,
        source: str | None = None,
    ) -> tuple[RecallHint, ...]:
        """Search recall memory. Always returns a tuple — empty when
        the layer is unavailable, the query is blank, or any error
        occurs. Callers must NOT depend on the order or count beyond
        ``top_k``; recall is a soft hint, not a contract."""
        if not self._available or self._impl is None:
            return ()
        if not query or not query.strip():
            return ()
        try:
            results = self._impl.recall(
                query,
                top_k=int(top_k),
                source=source,
            )
        except Exception as exc:
            LOG.warning(
                "Mnemosyne.recall failed (%s: %s); returning empty hint set",
                type(exc).__name__,
                exc,
            )
            return ()

        hints: list[RecallHint] = []
        for row in results or []:
            try:
                # mnemosyne returns dicts with at least: id, content, source.
                # Some rows include 'importance' and a synthetic 'score'.
                memory_id = str(row.get("id") or row.get("memory_id") or "")
                content = str(row.get("content", ""))
                src = str(row.get("source", source or "unknown"))
                importance = float(row.get("importance", 0.5) or 0.5)
                score = float(row.get("score", 0.0) or 0.0)
                if not memory_id or not content:
                    continue
                hints.append(
                    RecallHint(
                        memory_id=memory_id,
                        content=content,
                        source=src,
                        importance=importance,
                        score=score,
                    )
                )
            except (TypeError, ValueError) as exc:
                LOG.warning("Skipping malformed recall row %r: %s", row, exc)
                continue
        return tuple(hints)

    def forget(self, item_id: str) -> bool:
        """Delete a memory by id. Returns ``True`` on success, ``False``
        when the layer is unavailable or the call fails."""
        if not self._available or self._impl is None:
            return False
        if not item_id:
            return False
        try:
            return bool(self._impl.forget(item_id))
        except Exception as exc:
            LOG.warning(
                "Mnemosyne.forget(%s) failed (%s: %s)",
                item_id,
                type(exc).__name__,
                exc,
            )
            return False


# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------


def default_recall(db_path: Path | str | None = None) -> MnemosyneRecall:
    """Construct a :class:`MnemosyneRecall` with the project default DB
    path. Always succeeds — the returned wrapper is just degraded if
    Mnemosyne is unavailable. Tests should pass an explicit ``db_path``
    (typically a tmp_path) to avoid touching project state."""
    return MnemosyneRecall(db_path=db_path)


__all__ = [
    "DEFAULT_RECALL_DB",
    "MnemosyneRecall",
    "RecallHint",
    "default_recall",
]
