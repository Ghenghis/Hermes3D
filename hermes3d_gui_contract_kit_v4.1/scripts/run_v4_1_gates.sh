#!/usr/bin/env bash
set -euo pipefail
echo "[v4.1] registry validation"
python scripts/validate_registry.py config/external_repos_registry.yaml
echo "[v4.1] required docs check"
test -f 01_requirements/EXECUTION_HARDENING_REQUIREMENTS.md
test -f 02_architecture/SECURE_REMOTE_GPU_WORKER_ARCHITECTURE.md
test -f 05_truth_proof/SECURITY_AND_SAFETY_POLICY.md
test -f 06_release/FINAL_NO_MERGE_RULES.md
echo "[v4.1] PASS"
