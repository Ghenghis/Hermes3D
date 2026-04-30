# Final No-Merge Rules

Do not merge if any are true: PR is UNSTABLE, Layer D UI E2E fails, Windows Desktop gate missing, Ubuntu VPS gate missing, worker registry not tested, dock/undock not tested, external tool versions not recorded, proof bundle not generated, evidence ledger missing, security policy violated, or any NotImplementedError remains in a promoted runtime path.

RC can only be cut from a GREEN develop/release branch. Final can only be cut after RC passes clean install, clean launch, proof bundle verification, and rollback drill.
