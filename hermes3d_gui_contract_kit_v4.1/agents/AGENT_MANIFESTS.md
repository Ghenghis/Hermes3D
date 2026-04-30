# Agent Manifests

## Architect
Inputs: contract kit, repo state. Outputs: ADRs, task graph. Gates: no scope conflict.

## UIBuilder
Inputs: screenshot visual contract, tab specs. Outputs: React/Tailwind UI. Gates: screenshot tests green.

## AdapterBuilder
Inputs: external repo registry. Outputs: adapter skeletons + tests. Gates: detect/read-only tests green.

## SafetyAuditor
Inputs: adapter code. Outputs: dangerous action policy tests. Gates: no unconfirmed printer commands.

## BlenderMCPAgent
Inputs: provider registry. Outputs: Blender MCP provider manager. Gates: screenshot + 3MF smoke green.

## SlicerAgent
Inputs: FLSUN/Prusa/Orca/Cura registry entries. Outputs: slicer adapters. Gates: dry-run slice proof.

## PrinterControlAgent
Inputs: Moonraker/OctoPrint/Printrun config. Outputs: read-only status + gated write controls. Gates: denial tests pass.

## QA
Inputs: build. Outputs: full gate report. Gates: all required green.

## Repair
Inputs: failed gate logs. Outputs: patch branch. Gates: failing test becomes green.

## Releaser
Inputs: green QA + proof bundle. Outputs: release branch/tag. Gates: signed bundle validates.
