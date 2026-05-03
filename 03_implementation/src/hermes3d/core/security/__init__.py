"""Hermes3D security utilities.

Public API:
    from hermes3d.core.security import InjectionScanner, ScanResult, Finding

The injection scanner is an in-house, regex-driven prompt-injection detector
aligned to the OWASP LLM-01:2025 pattern catalogue plus a curated Hermes3D-
specific ruleset (3D-printing G-code injection, HermesProof lock manipulation).

This module is NOT a port of any third-party scanner; patterns and code are
authored in-house. See ADR-016 for the full rationale.
"""

from hermes3d.core.security.injection_scanner import (
    Finding,
    InjectionScanner,
    ScanResult,
    SeverityLevel,
)

__all__ = [
    "Finding",
    "InjectionScanner",
    "ScanResult",
    "SeverityLevel",
]
