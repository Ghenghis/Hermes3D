$ErrorActionPreference = "Stop"
Write-Host "[v4.1] registry validation"
python scripts/validate_registry.py config/external_repos_registry.yaml
Write-Host "[v4.1] required docs check"
if (!(Test-Path "01_requirements/EXECUTION_HARDENING_REQUIREMENTS.md")) { throw "missing execution requirements" }
if (!(Test-Path "02_architecture/SECURE_REMOTE_GPU_WORKER_ARCHITECTURE.md")) { throw "missing worker architecture" }
if (!(Test-Path "05_truth_proof/SECURITY_AND_SAFETY_POLICY.md")) { throw "missing security policy" }
if (!(Test-Path "06_release/FINAL_NO_MERGE_RULES.md")) { throw "missing no-merge rules" }
Write-Host "[v4.1] PASS"
