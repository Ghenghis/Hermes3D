"""Shared helpers for proof-event provenance (Wave 2 P2-6).

Every persisted ``proof_events`` row should carry the *active Hermes
Agent version* and *upstream tag* at write time. Without this, post-hoc
forensic queries cannot distinguish events emitted under v0.12
(``v2026.4.30``) from events emitted under v0.13 (``v2026.5.7``,
"Tenacity Release") — a gap that becomes load-bearing once an operator
flips ``HERMES_AGENT_CHECKOUT`` mid-process (per-call resolver, PR #155).

Why merge fields at the helper level (not at every call site):
- ``_append_proof_event`` is the single sink for ``INSERT INTO
  proof_events`` writes in the API layer (3 modules, identical
  ``(event_type, source_agent, payload)`` signature). Augmenting the
  helper once means every existing call site inherits version tagging
  for free, and no caller has to remember to thread version metadata
  through the dict it builds.
- Frozen dataclass lookup (``active_version()``) is a tuple scan of two
  records + one ``Path.resolve(strict=False)`` call. Safe to invoke
  inside the event-write hot path: no I/O, no allocations beyond the
  resolved Path; identical cost to ``hermes_agent_checkout()`` already
  on the path.

Backward compatibility:
- Older rows written before this PR have payloads without
  ``version_label`` / ``upstream_tag`` / ``checkout_path``. Readers
  MUST use ``payload.get("version_label", "unknown")`` semantics so a
  query against the historical ledger does not crash.

Provenance / standards basis:
- NIST SP 800-92 §4 ("Log Generation and Storage Architecture",
  https://csrc.nist.gov/publications/detail/sp/800-92/final): logs
  should record sufficient provenance to attribute each event to a
  specific software version, so that subsequent forensic review can
  distinguish behavior across upgrades.
- OpenTelemetry semantic conventions for resource attributes
  (https://opentelemetry.io/docs/specs/semconv/resource/#service): the
  ``service.version`` resource attribute is the canonical place to
  record the deployed version of a software component. We mirror that
  shape into the proof-event payload (``version_label`` ~
  ``service.version``) so future OTel exporters can lift the field
  without remapping.
"""

from __future__ import annotations

from typing import Any

from hermes3d.services.agent_checkout import hermes_agent_checkout
from hermes3d.services.agent_version_registry import active_version


def proof_version_fields() -> dict[str, str]:
    """Return ``version_label`` / ``upstream_tag`` / ``checkout_path``
    fields describing the currently-active Hermes Agent.

    The function is intentionally side-effect free: it does not touch
    the filesystem beyond what ``active_version()`` already does (a
    ``Path.resolve(strict=False)`` per known version). Callers can
    invoke it on every proof-event write without measurable overhead.

    Behavior:

    - When ``HERMES_AGENT_CHECKOUT`` resolves to a known version
      (v0.12 or v0.13 per the registry), the fields are filled from
      that frozen dataclass record.
    - When the operator has pointed the env at an unknown path
      (custom fork, forensic clone), ``version_label`` and
      ``upstream_tag`` fall back to ``"unknown"`` while
      ``checkout_path`` always carries the literal active path. This
      preserves the audit trail even when the version itself cannot be
      attributed.

    Secret hygiene: the registry only carries paths + tags + boolean
    feature flags by design (P2-1 contract). No credentials, tokens,
    or environment values other than the checkout path are exposed
    here. The ``checkout_path`` value comes from
    ``hermes_agent_checkout()`` which already participates in the
    project's standard redaction surface; if it leaks, the leak is
    already present elsewhere in the audit log.
    """
    v = active_version()
    if v is not None:
        return {
            "version_label": v.label,
            "upstream_tag": v.upstream_tag,
            "checkout_path": str(v.checkout_path),
        }
    return {
        "version_label": "unknown",
        "upstream_tag": "unknown",
        "checkout_path": str(hermes_agent_checkout()),
    }


def attach_version_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a NEW dict equal to ``payload`` plus the version fields.

    Existing keys in ``payload`` win over the version fields if they
    collide (defensive: a caller who explicitly set ``version_label``
    in a synthetic event has the final say). New dict so the input
    dict is never mutated — important for callers who pass the same
    dict to multiple sinks.
    """
    merged = {**proof_version_fields(), **payload}
    return merged


__all__ = ["proof_version_fields", "attach_version_fields"]
