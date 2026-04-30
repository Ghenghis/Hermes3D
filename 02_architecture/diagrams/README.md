# Architecture Diagrams

Mermaid sources for the Hermes3D-OS Lite architecture. Three diagrams:

| File | Type | What it shows |
|---|---|---|
| `system-context.mmd` | C4-style context | User, Hermes3D-OS, fleet, slicers, LLMs, notifiers, skill store |
| `workflow-12node.mmd` | Sequence | The 12-node print workflow end to end |
| `dispatcher-decision.mmd` | Flowchart | The dispatcher's 8-strategy printer selection |

## Rendering to SVG

Any Markdown viewer that supports Mermaid (GitHub, GitLab, VSCode with the
Mermaid extension, Obsidian, etc.) renders these inline -- no build step
required.

To produce static SVGs (e.g. for offline docs or print):

```bash
# One-off, no install needed:
npx -p @mermaid-js/mermaid-cli mmdc -i system-context.mmd     -o system-context.svg
npx -p @mermaid-js/mermaid-cli mmdc -i workflow-12node.mmd    -o workflow-12node.svg
npx -p @mermaid-js/mermaid-cli mmdc -i dispatcher-decision.mmd -o dispatcher-decision.svg
```

You can also render to PNG/PDF by changing the output extension. The
canonical authoritative architecture document remains `02_architecture/ARCHITECTURE.md`;
these diagrams are visual companions to that text.
