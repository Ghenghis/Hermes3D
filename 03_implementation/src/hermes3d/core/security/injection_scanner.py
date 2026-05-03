"""In-house prompt-injection scanner aligned to OWASP LLM-01:2025.

Public API:
    from hermes3d.core.security import InjectionScanner, ScanResult, Finding

Design summary (see ADR-016):
    - Pattern files are YAML (data, not code) so the ruleset can ship
      without code changes; one file per source (OWASP, in-house).
    - Patterns are compiled once at scanner construction and cached on
      the instance.
    - Severity escalation:
          one critical (high) hit              -> result severity = "high"
          two or more medium hits              -> result severity = "medium"
          else                                 -> max(per-rule severity, "low" if any)
          no findings                          -> "clean"
    - Redaction: every match is replaced with `[REDACTED-<rule_id>]`
      in `text_redacted`, suitable for safe logging.
    - Fail-closed threshold is configurable via `fail_threshold`. The
      scanner does NOT raise — callers decide what to do with the
      ScanResult. The threshold is reflected on `ScanResult.fail_closed`.

Performance notes:
    - All regexes are bounded (no nested unbounded `.*` loops).
    - On Linux a SIGALRM-based per-pattern timeout can be enabled via
      `match_timeout_seconds`; on Windows (no SIGALRM) the timeout is
      ignored (documented limitation; bounded patterns mitigate the risk).

This module is in-house; it is NOT a port of any third-party scanner.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

import yaml

SeverityLevel = Literal["clean", "low", "medium", "high"]

_SEVERITY_RANK: dict[str, int] = {"clean": 0, "low": 1, "medium": 2, "high": 3}
_VALID_RULE_SEVERITIES: frozenset[str] = frozenset({"low", "medium", "high"})

_DEFAULT_PATTERN_DIR = Path(__file__).parent / "patterns"
_DEFAULT_PATTERN_FILES: tuple[str, ...] = ("owasp_llm01.yaml", "curated_inhouse.yaml")


class InjectionScannerError(ValueError):
    """Raised when the ruleset is malformed."""


@dataclass(frozen=True)
class Finding:
    """A single rule hit inside a scanned text.

    Attributes:
        rule_id: Stable identifier from the pattern file (e.g. ``LLM01-IGN-PREV``).
        severity: Per-rule severity (``low`` | ``medium`` | ``high``).
        match_excerpt: Up to 80 chars of the matched text (truncated with ellipsis).
        position: Zero-based character offset of the match start.
        description: Human-readable rule rationale from the pattern file.
    """

    rule_id: str
    severity: str
    match_excerpt: str
    position: int
    description: str


@dataclass
class ScanResult:
    """Aggregate result of scanning a text or dict.

    Attributes:
        severity: ``clean`` | ``low`` | ``medium`` | ``high`` per the
            severity-escalation rules above.
        findings: One ``Finding`` per matched rule occurrence.
        text_redacted: Input with each match replaced by
            ``[REDACTED-<rule_id>]``.
        fail_closed: True iff `severity` >= configured `fail_threshold`.
    """

    severity: SeverityLevel
    findings: list[Finding] = field(default_factory=list)
    text_redacted: str = ""
    fail_closed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "fail_closed": self.fail_closed,
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity,
                    "match_excerpt": f.match_excerpt,
                    "position": f.position,
                    "description": f.description,
                }
                for f in self.findings
            ],
            "text_redacted": self.text_redacted,
        }


@dataclass(frozen=True)
class _CompiledRule:
    rule_id: str
    severity: str
    pattern: re.Pattern[str]
    description: str


def _truncate_excerpt(matched: str, max_len: int = 80) -> str:
    """Truncate match to <= max_len chars, replacing newlines for log safety."""
    cleaned = matched.replace("\n", "\\n").replace("\r", "\\r")
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3] + "..."


def _load_ruleset(paths: Iterable[Path]) -> list[_CompiledRule]:
    """Load and compile all rules from the given YAML files."""
    compiled: list[_CompiledRule] = []
    seen_ids: set[str] = set()

    for path in paths:
        if not path.is_file():
            raise InjectionScannerError(f"Pattern file not found: {path}")
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise InjectionScannerError(f"Invalid YAML in {path}: {exc}") from exc

        if not isinstance(data, dict) or "rules" not in data:
            raise InjectionScannerError(f"{path}: missing top-level 'rules' key")

        rules = data["rules"]
        if not isinstance(rules, list) or not rules:
            raise InjectionScannerError(f"{path}: 'rules' must be a non-empty list")

        for idx, raw in enumerate(rules):
            if not isinstance(raw, dict):
                raise InjectionScannerError(f"{path}[{idx}]: rule must be a mapping")

            rule_id = raw.get("id")
            severity = raw.get("severity")
            regex = raw.get("regex")
            description = raw.get("description", "")

            if not isinstance(rule_id, str) or not rule_id:
                raise InjectionScannerError(f"{path}[{idx}]: missing 'id'")
            if rule_id in seen_ids:
                raise InjectionScannerError(f"{path}: duplicate rule id {rule_id!r}")
            if severity not in _VALID_RULE_SEVERITIES:
                raise InjectionScannerError(
                    f"{path}[{rule_id}]: severity must be low|medium|high (got {severity!r})"
                )
            if not isinstance(regex, str) or not regex:
                raise InjectionScannerError(f"{path}[{rule_id}]: missing 'regex'")
            if not isinstance(description, str):
                raise InjectionScannerError(f"{path}[{rule_id}]: 'description' must be a string")

            try:
                pattern = re.compile(regex, flags=re.IGNORECASE)
            except re.error as exc:
                raise InjectionScannerError(f"{path}[{rule_id}]: invalid regex: {exc}") from exc

            compiled.append(
                _CompiledRule(
                    rule_id=rule_id,
                    severity=severity,
                    pattern=pattern,
                    description=description,
                )
            )
            seen_ids.add(rule_id)

    return compiled


def _aggregate_severity(findings: list[Finding]) -> SeverityLevel:
    """Apply the documented severity-escalation rules."""
    if not findings:
        return "clean"

    high_count = sum(1 for f in findings if f.severity == "high")
    medium_count = sum(1 for f in findings if f.severity == "medium")

    if high_count >= 1:
        return "high"
    if medium_count >= 2:
        return "medium"

    # Per-rule severity dominates from here.
    rank = max(_SEVERITY_RANK[f.severity] for f in findings)
    if rank >= _SEVERITY_RANK["medium"]:
        return "medium"
    return "low"


class InjectionScanner:
    """Regex-driven prompt-injection scanner.

    Args:
        ruleset_paths: Optional iterable of YAML pattern files. If omitted,
            both bundled rulesets (OWASP LLM-01 + Hermes3D in-house) load.
        fail_threshold: Severity at or above which `ScanResult.fail_closed`
            is True. Default ``"high"``. Use ``"medium"`` for stricter
            policies, ``"low"`` for the strictest (any finding fails).
        match_timeout_seconds: On POSIX (signal.SIGALRM available) each
            pattern match is bounded by this timeout. On Windows the
            argument is accepted but ignored (no SIGALRM); bounded regex
            patterns are the primary defence. None disables the timer.
    """

    def __init__(
        self,
        ruleset_paths: Iterable[Path | str] | None = None,
        *,
        fail_threshold: SeverityLevel = "high",
        match_timeout_seconds: float | None = None,
    ) -> None:
        if fail_threshold not in {"low", "medium", "high"}:
            raise ValueError(
                f"fail_threshold must be one of low|medium|high (got {fail_threshold!r})"
            )

        if ruleset_paths is None:
            paths = [_DEFAULT_PATTERN_DIR / name for name in _DEFAULT_PATTERN_FILES]
        else:
            paths = [Path(p) for p in ruleset_paths]
            if not paths:
                raise InjectionScannerError("ruleset_paths must be non-empty if provided")

        self._rules: tuple[_CompiledRule, ...] = tuple(_load_ruleset(paths))
        self._fail_threshold: SeverityLevel = fail_threshold
        self._fail_threshold_rank: int = _SEVERITY_RANK[fail_threshold]
        self._match_timeout_seconds: float | None = match_timeout_seconds
        # Capability flag: SIGALRM is POSIX-only.
        self._can_timeout: bool = (
            match_timeout_seconds is not None and sys.platform != "win32" and _has_sigalrm()
        )

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    @property
    def rule_ids(self) -> tuple[str, ...]:
        return tuple(r.rule_id for r in self._rules)

    def scan(self, text: str) -> ScanResult:
        """Scan a single text blob.

        Returns a `ScanResult` with all findings (one per match), the
        aggregate severity, and a redacted copy of the input.
        """
        if not isinstance(text, str):
            raise TypeError(f"scan() requires str, got {type(text).__name__}")

        findings: list[Finding] = []
        # Map from (rule_id, span_start, span_end) -> rule_id, used for
        # deterministic redaction even when multiple rules overlap.
        spans: list[tuple[int, int, str]] = []

        for rule in self._rules:
            for match in self._iter_matches(rule, text):
                start, end = match.span()
                excerpt = _truncate_excerpt(match.group(0))
                findings.append(
                    Finding(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        match_excerpt=excerpt,
                        position=start,
                        description=rule.description,
                    )
                )
                spans.append((start, end, rule.rule_id))

        severity = _aggregate_severity(findings)
        redacted = _apply_redaction(text, spans)
        fail_closed = _SEVERITY_RANK[severity] >= self._fail_threshold_rank

        return ScanResult(
            severity=severity,
            findings=findings,
            text_redacted=redacted,
            fail_closed=fail_closed,
        )

    def scan_dict(
        self,
        data: dict[str, Any],
        fields: list[str] | None = None,
    ) -> ScanResult:
        """Scan selected string fields of a dict.

        If ``fields`` is None, every string-valued field at the top level is
        scanned. Nested dict values are NOT recursed into automatically —
        callers should flatten their data first or pass explicit dotted
        paths in a future revision (out of scope for v1).

        Returns one merged ScanResult. The redacted text is returned as a
        ``\\n``-joined concatenation prefixed by field name, suitable for
        logging context. Callers that need per-field results can iterate
        their fields and call `scan()` directly.
        """
        if not isinstance(data, dict):
            raise TypeError(f"scan_dict() requires dict, got {type(data).__name__}")

        if fields is None:
            target_fields = [k for k, v in data.items() if isinstance(v, str)]
        else:
            target_fields = list(fields)

        all_findings: list[Finding] = []
        redacted_parts: list[str] = []

        for fname in target_fields:
            value = data.get(fname)
            if not isinstance(value, str):
                continue
            sub = self.scan(value)
            all_findings.extend(sub.findings)
            redacted_parts.append(f"{fname}: {sub.text_redacted}")

        severity = _aggregate_severity(all_findings)
        fail_closed = _SEVERITY_RANK[severity] >= self._fail_threshold_rank

        return ScanResult(
            severity=severity,
            findings=all_findings,
            text_redacted="\n".join(redacted_parts),
            fail_closed=fail_closed,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _iter_matches(self, rule: _CompiledRule, text: str) -> Iterable[re.Match[str]]:
        """Yield matches with optional per-pattern timeout (POSIX only)."""
        if self._can_timeout:
            # POSIX path: wrap finditer in SIGALRM bound.
            yield from _iter_matches_with_timeout(
                rule.pattern,
                text,
                self._match_timeout_seconds,  # type: ignore[arg-type]
            )
        else:
            yield from rule.pattern.finditer(text)


# ---------------------------------------------------------------------- #
# POSIX-only timeout support
# ---------------------------------------------------------------------- #


def _has_sigalrm() -> bool:
    try:
        import signal

        return hasattr(signal, "SIGALRM")
    except Exception:  # pragma: no cover - defensive
        return False


def _iter_matches_with_timeout(
    pattern: re.Pattern[str],
    text: str,
    timeout_seconds: float,
) -> Iterable[re.Match[str]]:  # pragma: no cover - POSIX-only
    """Run ``pattern.finditer`` under a SIGALRM bound.

    On timeout we abort iteration and return whatever matches were already
    accumulated. This is best-effort — Python's ``re`` engine is not fully
    interruptible from C, but for the bounded patterns shipped in our
    rulesets this is sufficient defence-in-depth.
    """
    import signal

    matches: list[re.Match[str]] = []

    class _Timeout(Exception):
        pass

    def _handler(signum: int, frame: object) -> None:  # noqa: ARG001
        raise _Timeout()

    old_handler = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        for m in pattern.finditer(text):
            matches.append(m)
    except _Timeout:
        # Aborted — return partial matches.
        pass
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
    yield from matches


# ---------------------------------------------------------------------- #
# Redaction
# ---------------------------------------------------------------------- #


def _apply_redaction(text: str, spans: list[tuple[int, int, str]]) -> str:
    """Replace every span with ``[REDACTED-<rule_id>]``.

    Overlapping spans are merged by position so the redaction tag for the
    first matching rule is used and overlapping later spans are dropped.
    """
    if not spans:
        return text

    # Sort by start, then by widest match first so wider rules win on tie.
    sorted_spans = sorted(spans, key=lambda s: (s[0], -(s[1] - s[0])))

    out: list[str] = []
    cursor = 0
    for start, end, rule_id in sorted_spans:
        if start < cursor:
            # Overlap: skip this span — the earlier one already covered it.
            continue
        out.append(text[cursor:start])
        out.append(f"[REDACTED-{rule_id}]")
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


# ---------------------------------------------------------------------- #
# CLI shim — supports ``python -m hermes3d.core.security.injection_scanner``
#
# Python emits a benign ``RuntimeWarning`` from runpy here because the
# package ``__init__`` re-exports symbols from this module (so the module
# is already in ``sys.modules`` before runpy executes it as ``__main__``).
# The warning does not affect correctness; the cleaner alternative
# invocation is ``python -m hermes3d.core.security`` which uses the
# package-level ``__main__.py`` shim.
# ---------------------------------------------------------------------- #


if __name__ == "__main__":  # pragma: no cover - CLI bootstrap
    from hermes3d.core.security.cli import main as _cli_main

    raise SystemExit(_cli_main())
