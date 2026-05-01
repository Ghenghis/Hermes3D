"""Structured error model for the registry validator.

Errors are emitted as `ValidationError` records with an `ErrorCode` enum so
downstream tooling (CI gates, dashboards, dry-run editors) can match on stable
codes rather than parsing free-form strings.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Literal


class ErrorCode(str, Enum):
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_TYPE = "INVALID_TYPE"
    INVALID_URL_SHAPE = "INVALID_URL_SHAPE"
    MISSING_LICENSE = "MISSING_LICENSE"
    INVALID_LICENSE = "INVALID_LICENSE"
    MISSING_DOCK_CAPABILITY = "MISSING_DOCK_CAPABILITY"
    MISSING_EXTERNAL_LAUNCH_CAPABILITY = "MISSING_EXTERNAL_LAUNCH_CAPABILITY"
    EMPTY_CAPABILITIES = "EMPTY_CAPABILITIES"
    UNKNOWN_TYPE = "UNKNOWN_TYPE"
    EMPTY_TESTED_VERSIONS = "EMPTY_TESTED_VERSIONS"
    INVALID_VERSION_POLICY = "INVALID_VERSION_POLICY"


Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class ValidationError:
    tool_id: str
    code: ErrorCode
    message: str
    severity: Severity = "error"

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["code"] = self.code.value
        return d
