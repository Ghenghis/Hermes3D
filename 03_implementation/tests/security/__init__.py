"""Hermes3D security audit test suite (Lane 19, H3D-CLAUDE-SECURITY-MCP).

Covers:
    - OWASP LLM-01 prompt injection vectors via the in-house scanner
      (commit 0c9b6d9; module: hermes3d.core.security.injection_scanner).
    - Secret-redaction guarantees over services/local_state.py and
      services/module_runtime.py log paths (read-only AST/regex audit).
    - Path-traversal rejection on user-supplied paths flowing into
      services/code_history.py and api/routes/*.py (read-only).
    - MCP / tool boundary policy: enumerated tool surface, fail-closed
      threshold, secret storage convention (G:\\private\\.env).

Light coverage of LLM-02 (insecure output handling) and LLM-06 (sensitive
information disclosure) is included where scaffolding allows.

These tests are READ-ONLY against the source under audit. No source files
outside `03_implementation/tests/security/`,
`03_implementation/proof/security/`, and
`03_implementation/docs/security/` may be modified by this lane.
"""
