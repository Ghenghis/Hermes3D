"""Hermes3D-OS Lite — Contract Kit v5 reference implementation.

This package is the runnable backbone behind 00-CONTRACT/MASTER_CONTRACT.md.
Each subpackage corresponds to one section of the agent pipeline:

    hermes3d.core.validation : Truth Gate (real, runnable)
    hermes3d.core.design     : parametric desk organizer (real, runnable)
    hermes3d.core.proof      : HMAC-signed proof envelopes (real, runnable)
    hermes3d.core.visual     : 6-view evidence renderer (real, runnable)
    hermes3d.core.slicer     : PrusaSlicer/OrcaSlicer CLI wrapper (real)
    hermes3d.core.modeling   : Blender MCP server (SPEC-only — see file)
    hermes3d.core.agents     : orchestrator state machine + DryRun (real),
                               LangGraph (spec-only)

KIT_MANIFEST.json at the kit root tags every file as runnable / spec /
scaffold so consumers never have to guess.
"""
__version__ = "5.0.0"
