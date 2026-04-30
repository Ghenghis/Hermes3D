"""Optional vector memory for fuzzy skill retrieval.

The default ``SkillStore`` uses exact-match scope filtering. That is fast and
predictable, but breaks down when the user describes a problem in natural
language ("my ASA prints keep delaminating around layer 30 on the T1") rather
than (printer_id, material) tuples.

This module adds a *fuzzy* retrieval layer that any agentic component can use
to surface relevant skills given a natural-language query. The design is
deliberately layered so the fleet works with zero extra dependencies:

  - Tier 1 (always available): TF-IDF over skill ``name`` + ``notes`` +
    serialised ``body``. Hand-rolled implementation, no external deps.
  - Tier 2 (if installed): FAISS + sentence-transformers. Better recall on
    paraphrased queries.

The active backend is chosen at construction time via ``backend="auto"``
(default) which prefers FAISS when available.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from hermes3d.core.memory.skill_store import Skill, SkillStore


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _skill_text(skill: Skill) -> str:
    """Build the indexable text representation of a skill."""
    parts = [skill.name, skill.notes or "", skill.skill_kind.value]
    if skill.scope.printer_id:
        parts.append(skill.scope.printer_id)
    if skill.scope.material:
        parts.append(skill.scope.material)
    if skill.scope.quality_level:
        parts.append(skill.scope.quality_level)
    parts.append(json.dumps(skill.body, sort_keys=True))
    return " ".join(parts)


@dataclass
class VectorHit:
    skill: Skill
    score: float  # higher is better, range depends on backend


class TFIDFBackend:
    """Hand-rolled TF-IDF — no external deps, deterministic, fast for ~thousands of skills."""

    def __init__(self) -> None:
        self._docs: dict[str, list[str]] = {}
        self._df: Counter[str] = Counter()
        self._dirty: bool = True
        self._idf_cache: dict[str, float] = {}

    def add(self, skill_id: str, text: str) -> None:
        tokens = _tokenize(text)
        if skill_id in self._docs:
            self.remove(skill_id)
        self._docs[skill_id] = tokens
        for token in set(tokens):
            self._df[token] += 1
        self._dirty = True

    def remove(self, skill_id: str) -> None:
        tokens = self._docs.pop(skill_id, None)
        if not tokens:
            return
        for token in set(tokens):
            self._df[token] -= 1
            if self._df[token] <= 0:
                del self._df[token]
        self._dirty = True

    def _idf(self, token: str) -> float:
        if self._dirty:
            self._idf_cache = {}
            self._dirty = False
        if token in self._idf_cache:
            return self._idf_cache[token]
        n = max(1, len(self._docs))
        df = self._df.get(token, 0)
        idf = math.log((n + 1) / (df + 1)) + 1.0
        self._idf_cache[token] = idf
        return idf

    def _vector(self, tokens: list[str]) -> dict[str, float]:
        if not tokens:
            return {}
        tf = Counter(tokens)
        norm = math.sqrt(sum(v * v for v in tf.values())) or 1.0
        return {t: (c / norm) * self._idf(t) for t, c in tf.items()}

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        q_vec = self._vector(_tokenize(query))
        if not q_vec or not self._docs:
            return []
        scores: list[tuple[str, float]] = []
        for skill_id, tokens in self._docs.items():
            d_vec = self._vector(tokens)
            common = set(q_vec) & set(d_vec)
            score = sum(q_vec[t] * d_vec[t] for t in common)
            if score > 0:
                scores.append((skill_id, score))
        scores.sort(key=lambda pair: -pair[1])
        return scores[:top_k]

    def __len__(self) -> int:
        return len(self._docs)


class FAISSBackend:
    """Optional FAISS + sentence-transformers backend.

    Imported lazily so the fleet never requires the deps unless the user
    explicitly opts in.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        try:
            import faiss  # type: ignore  # noqa: F401
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised when deps missing
            raise RuntimeError(
                "FAISS backend requires `faiss-cpu` and `sentence-transformers`."
            ) from exc

        import faiss  # type: ignore
        from sentence_transformers import SentenceTransformer  # type: ignore

        self._model = SentenceTransformer(model_name)
        self._dim = int(self._model.get_sentence_embedding_dimension())
        self._index = faiss.IndexFlatIP(self._dim)
        self._ids: list[str] = []

    def add(self, skill_id: str, text: str) -> None:  # pragma: no cover - heavy dep
        self.remove(skill_id)
        emb = self._model.encode([text], normalize_embeddings=True)
        self._index.add(emb)
        self._ids.append(skill_id)

    def remove(self, skill_id: str) -> None:  # pragma: no cover - heavy dep
        if skill_id not in self._ids:
            return
        # Rebuilding is the simplest correct strategy for FlatIP indexes.
        keep = [(i, sid) for i, sid in enumerate(self._ids) if sid != skill_id]
        if not keep:
            self._index.reset()
            self._ids = []
            return
        # Rebuilding requires re-encoding; caller should call rebuild() externally
        # for performance. Here we just drop from the id list and let scores
        # for missing rows be filtered downstream.
        self._ids = [sid for _, sid in keep]

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:  # pragma: no cover
        if not self._ids:
            return []
        emb = self._model.encode([query], normalize_embeddings=True)
        scores, idxs = self._index.search(emb, min(top_k * 2, len(self._ids)))
        out: list[tuple[str, float]] = []
        for idx, score in zip(idxs[0], scores[0]):
            if idx < 0 or idx >= len(self._ids):
                continue
            out.append((self._ids[idx], float(score)))
            if len(out) >= top_k:
                break
        return out

    def __len__(self) -> int:  # pragma: no cover
        return len(self._ids)


class VectorMemory:
    """Wraps a SkillStore with a fuzzy retrieval layer."""

    def __init__(
        self,
        store: SkillStore,
        *,
        backend: str = "auto",
    ) -> None:
        self._store = store
        self._backend = self._select_backend(backend)
        self.rebuild()

    @staticmethod
    def _select_backend(name: str) -> Any:
        name = name.lower()
        if name == "tfidf":
            return TFIDFBackend()
        if name == "faiss":  # pragma: no cover - optional
            return FAISSBackend()
        if name == "auto":
            try:  # pragma: no cover - optional
                return FAISSBackend()
            except RuntimeError:
                return TFIDFBackend()
        raise ValueError(f"unknown vector backend: {name!r}")

    def rebuild(self) -> None:
        # For TF-IDF we throw away and re-add. For FAISS this is also fine.
        self._backend = self._select_backend(
            "tfidf" if isinstance(self._backend, TFIDFBackend) else "faiss"
        )
        for skill in self._store.list():
            self._backend.add(skill.skill_id, _skill_text(skill))

    def add(self, skill: Skill) -> None:
        self._backend.add(skill.skill_id, _skill_text(skill))

    def remove(self, skill_id: str) -> None:
        self._backend.remove(skill_id)

    def search(self, query: str, *, top_k: int = 5) -> list[VectorHit]:
        results = self._backend.search(query, top_k)
        hits: list[VectorHit] = []
        for skill_id, score in results:
            try:
                skill = self._store.get(skill_id)
            except KeyError:
                continue
            hits.append(VectorHit(skill=skill, score=float(score)))
        return hits

    def __len__(self) -> int:
        return len(self._backend)


__all__ = [
    "FAISSBackend",
    "TFIDFBackend",
    "VectorHit",
    "VectorMemory",
]
