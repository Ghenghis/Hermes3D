# Codex Memory: Modeling Ownership + Final Audit Directive

Date: 2026-05-12
Owner going forward: Codex

## Ownership

Claude is no longer available to code this project. Treat Hermes3D completion as Codex-owned work from this point forward.

Do not frame next actions as "ask Claude" or "prompt Claude." If a follow-up is needed, Codex should either do the work directly or create a Codex branch/PR.

## Gen3D / Modeling Reality

LM Studio is not the 3D modeling runtime. LM Studio is only a local/private LLM runtime for agent planning, chat, review, or code assistance.

The Gen3D/modeling stack needs real model runtimes and weights. Depending on the provider, this may include:

- `.safetensors` model weights
- checkpoints / `.ckpt`
- ONNX models
- PyTorch / CUDA packages
- ComfyUI core and custom nodes
- rembg / background-removal models
- TripoSR weights and runtime
- Hunyuan3D / TRELLIS weights and runtime
- provider-specific configs and cache paths

Never mark Gen3D as ready because LM Studio is ready. Gen3D is ready only when a real provider can create a model artifact and the artifact is visible through backend and UI proof.

## Final Massive Audit Rule

Reserve one final massive audit for project-complete verification only.

That final audit may use 20-24 agents and should be extremely deep, multi-layered, and E2E. Do not spend that audit while the project is still in active build/fix mode.

Until then, use at most 4-6 agents for scoped implementation or verification work.

## Current Completion Posture

The project is not 95% E2E. Treat the practical completion estimate as roughly 55-65% until the remaining product gaps are proven:

- real Gen3D/image-to-3D provider installed and usable
- background removal works for non-transparent logo inputs
- Design -> STL is broader than one narrow template
- model -> slicer -> G-code -> files/artifacts is proven after latest changes
- 60-app proof behavior is run and persisted
- Files/Artifacts/reconciler/lineage stay consistent
- UI refresh is verified after PR #266 lands
- Hermes Agents are useful beyond claim/status, or honestly blocked

## Immediate Codex Priority

After PR #267 docs-only handoff settles, Codex should avoid more audit-only PRs and move into product fixes.

The next product PR should be a real Gen3D/background-removal setup PR:

1. Verify GPU VRAM with `nvidia-smi`.
2. Inspect current Python/CUDA/Torch package constraints.
3. Determine the smallest working image-to-3D path for RTX 3090 Ti.
4. Install/setup rembg/background removal for white-background logo images.
5. Install/setup TripoSR or the smallest viable Hunyuan3D path.
6. Update provider readiness so `/api/gen3d/providers` reflects real usability.
7. Prove one model artifact through backend, files/artifacts, and UI.

No printer hardware. No fake pass. No route-only green.
