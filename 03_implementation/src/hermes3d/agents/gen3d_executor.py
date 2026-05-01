"""Simulated Gen3D executor for Phase 3.2."""

from __future__ import annotations

import json
from pathlib import Path

from hermes3d.orchestration import (
    CapabilityToken,
    Err,
    Gen3DRequest,
    Gen3DResult,
    OfflineSupervisor,
    SimulatedModelArtifact,
)
from hermes3d.orchestration.supervisor import stable_sha

GEN3D_TOOL = "gen3d.generate"
ARTIFACT_ROOT = Path("var") / "orchestration" / "artifacts"


class SimulatedGen3DExecutor:
    """Produces deterministic local stub artifacts for gen3d.generate only."""

    def __init__(self, *, supervisor: OfflineSupervisor) -> None:
        self.supervisor = supervisor

    def generate(self, request: Gen3DRequest, *, token: CapabilityToken | None) -> Gen3DResult:
        if request.tool != GEN3D_TOOL:
            return Gen3DResult(
                run_id=request.run_id,
                agent_id=request.agent_id,
                node_id=request.node_id,
                tool=request.tool,
                result=Err("method_not_allowed", "Gen3D executor only accepts gen3d.generate"),
                token_id=None if token is None else token.token_id,
            )
        return self.supervisor.dispatch_gen3d(request, token=token, handler=self._generate)

    def _generate(self, request: Gen3DRequest) -> SimulatedModelArtifact:
        artifact_sha = stable_sha({"prompt": request.prompt, "seed": request.seed})
        artifact_path = _artifact_path(artifact_sha)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact = SimulatedModelArtifact(
            artifact_id=artifact_sha,
            sha256=artifact_sha,
            prompt=request.prompt,
            seed=request.seed,
            metadata={
                "tool": GEN3D_TOOL,
                "artifact_path": str(Path("var") / "orchestration" / "artifacts" / f"{artifact_sha}.json"),
            },
        )
        artifact_path.write_text(
            json.dumps(
                {
                    "artifact_id": artifact.artifact_id,
                    "prompt": artifact.prompt,
                    "seed": artifact.seed,
                    "sha256": artifact.sha256,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        return artifact


def _artifact_path(artifact_sha: str) -> Path:
    root = ARTIFACT_ROOT.resolve()
    candidate = (root / f"{artifact_sha}.json").resolve()
    if candidate.parent != root:
        raise ValueError("artifact path escaped orchestration artifact root")
    return candidate
