"""Hermes3D-OS Lite launcher (Gradio).

Tabs in this launcher:

    1. Truth Gate Validator      — REAL: drop an STL, get a Truth Gate report.
    2. Generate Desk Organizer   — REAL: build the parametric organizer + its
                                   signed proof envelope + 6-view renders.
    3. Pipeline (Dry-Run)        — REAL: walks the orchestrator state machine
                                   without any LLMs.
    4. Full Autonomous Pipeline  — DISABLED in this kit; clearly labelled.
                                   Enables itself once the installer has
                                   provisioned Blender + ComfyUI + LLM keys.

Per the contract (§3.1): nothing in this launcher is a fake button. Every
visible control either does real work or is conspicuously disabled with an
explanation. There is no "Coming Soon".
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from hermes3d.core.agents import DryRunOrchestrator, OrchestratorState
from hermes3d.core.design import OrganizerSpec, export_organizer
from hermes3d.core.proof import write_proof
from hermes3d.core.validation import TruthGateConfig, run_truth_gate
from hermes3d.core.visual import render_all_views

LOG = logging.getLogger(__name__)


def _validate_stl(stl_path: str | None) -> tuple[str, str]:
    """Tab 1 handler: run Truth Gate on an uploaded STL."""
    if not stl_path:
        return "No file uploaded.", ""
    p = Path(stl_path)
    if not p.is_file():
        return f"File not found: {p}", ""
    report = run_truth_gate(p, TruthGateConfig())
    summary_lines = [
        f"**Mesh**: `{p.name}`  ({p.stat().st_size} bytes)",
        f"**Overall**: `{report.overall_status.value.upper()}`",
        "",
        "| Check | Status | Measured | Threshold |",
        "| --- | --- | --- | --- |",
    ]
    for c in report.checks:
        summary_lines.append(
            f"| {c.name} | `{c.status.value}` | "
            f"`{json.dumps(c.measured)}` | `{json.dumps(c.threshold)}` |"
        )
    return "\n".join(summary_lines), json.dumps(report.to_dict(), indent=2)


def _generate_organizer(
    width_mm: float, depth_mm: float, height_mm: float,
    tray_count: int, pen_count: int, pen_diameter_mm: float,
    phone_slot: bool, phone_slot_angle_deg: float,
    cable_passthrough: bool,
    output_dir: str | None,
) -> tuple[str, str | None, str | None]:
    """Tab 2 handler: build organizer, validate, render, sign proof.

    Returns (markdown_summary, stl_path_for_download, proof_path_for_download).
    """
    spec = OrganizerSpec(
        width_mm=float(width_mm), depth_mm=float(depth_mm), height_mm=float(height_mm),
        tray_count=int(tray_count),
        pen_count=int(pen_count),
        pen_diameter_mm=float(pen_diameter_mm),
        phone_slot=bool(phone_slot),
        phone_slot_angle_deg=float(phone_slot_angle_deg),
        cable_passthrough=bool(cable_passthrough),
    )
    out_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="hermes3d_"))
    out_dir.mkdir(parents=True, exist_ok=True)
    stl_path = out_dir / f"organizer_{spec.signature()}.stl"
    export_organizer(spec, stl_path)
    rendered = render_all_views(stl_path, out_dir / "renders",
                                name_prefix=f"organizer_{spec.signature()}")
    proof_path = out_dir / f"organizer_{spec.signature()}.proof.json"
    write_proof(
        mesh_path=stl_path,
        output_path=proof_path,
        generator_name="desk_organizer",
        generator_version="1.0.0",
        generator_signature=spec.signature(),
        visual_evidence_paths=[(name, p) for name, p in rendered],
    )
    md = (
        f"### Organizer generated\n\n"
        f"- **STL**: `{stl_path}` ({stl_path.stat().st_size} bytes)\n"
        f"- **Spec signature**: `{spec.signature()}`\n"
        f"- **Renders**: {len(rendered)} canonical views in "
        f"`{out_dir / 'renders'}`\n"
        f"- **Signed proof envelope**: `{proof_path}` "
        f"({proof_path.stat().st_size} bytes)\n"
    )
    return md, str(stl_path), str(proof_path)


def _run_dry_pipeline(text_prompt: str) -> str:
    """Tab 3 handler: walk the orchestrator state machine."""
    state = OrchestratorState(text_prompt=text_prompt or "(empty)")
    final = DryRunOrchestrator().run(state)
    lines = [
        f"**Job**: `{final.job_id}`",
        f"**Final stage**: `{final.stage.value}`",
        f"**Repair attempts**: {final.repair_attempts}",
        f"**History**: {' → '.join(s.value for s, _ in final.history)} → {final.stage.value}",
    ]
    if final.error:
        lines.append(f"**Error**: `{final.error}`")
    return "\n".join(lines)


def build_app():  # type: ignore[no-untyped-def]
    """Construct the Gradio Blocks app. Importing gradio at call-time keeps
    the package usable in environments without gradio installed."""
    try:
        import gradio as gr
    except ImportError as exc:
        raise RuntimeError(
            "gradio is not installed. Install with `pip install gradio` or "
            "run scripts/run-dev.ps1 (the dev script installs requirements)."
        ) from exc

    with gr.Blocks(title="Hermes3D-OS Lite") as app:
        gr.Markdown(
            "# Hermes3D-OS Lite — Contract Kit v5\n"
            "Live, working tabs are green. Tabs that require provisioning "
            "(Blender / ComfyUI / LLM keys) are disabled and labelled."
        )

        with gr.Tab("✅ Truth Gate Validator"):
            stl_in = gr.File(label="Upload STL", file_types=[".stl"], type="filepath")
            run_btn = gr.Button("Run Truth Gate", variant="primary")
            md_out = gr.Markdown()
            json_out = gr.Code(label="Full report (JSON)", language="json")
            run_btn.click(_validate_stl, inputs=stl_in, outputs=[md_out, json_out])

        with gr.Tab("✅ Generate Desk Organizer"):
            with gr.Row():
                width = gr.Slider(80, 220, value=180, step=5, label="Width (mm)")
                depth = gr.Slider(60, 220, value=100, step=5, label="Depth (mm)")
                height = gr.Slider(35, 90, value=55, step=5, label="Height (mm)")
            with gr.Row():
                trays = gr.Slider(1, 6, value=3, step=1, label="Tray count")
                pens = gr.Slider(0, 8, value=4, step=1, label="Pen count")
                pen_dia = gr.Slider(8, 16, value=12, step=0.5, label="Pen ⌀ (mm)")
            with gr.Row():
                slot = gr.Checkbox(value=True, label="Phone slot")
                slot_angle = gr.Slider(0, 12, value=8, step=1, label="Phone slot tilt (°)")
                cable = gr.Checkbox(value=True, label="Cable passthrough")
            outdir = gr.Textbox(value="", label="Output directory (blank = temp)")
            gen_btn = gr.Button("Generate + Validate + Sign", variant="primary")
            md = gr.Markdown()
            stl_dl = gr.File(label="STL")
            proof_dl = gr.File(label="Proof envelope")
            gen_btn.click(
                _generate_organizer,
                inputs=[width, depth, height, trays, pens, pen_dia,
                        slot, slot_angle, cable, outdir],
                outputs=[md, stl_dl, proof_dl],
            )

        with gr.Tab("✅ Pipeline (Dry-Run)"):
            prompt = gr.Textbox(label="Text prompt", value="a small desk bracket")
            dry_btn = gr.Button("Walk state machine", variant="primary")
            dry_md = gr.Markdown()
            dry_btn.click(_run_dry_pipeline, inputs=prompt, outputs=dry_md)

        with gr.Tab("⛔ Full Autonomous Pipeline (disabled)"):
            gr.Markdown(
                "This tab is **disabled** in the kit-only build.\n\n"
                "It enables itself automatically once "
                "`05-INSTALLER/install.ps1` has provisioned Blender 4.2+, "
                "ComfyUI with TRELLIS.2 / Hunyuan3D-2.1, and an LLM API key. "
                "See `07-DOCS/AI_PROGRAMMER_GUIDE.md` §'Implementing the "
                "modeling MCP' and §'Implementing the orchestrator'."
            )
    return app


def main() -> None:
    """Module entrypoint: ``python -m hermes3d.app.launcher`` or via run.bat."""
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = build_app()
    host = os.environ.get("HERMES3D_HOST", "127.0.0.1")
    port = int(os.environ.get("HERMES3D_PORT", "7860"))
    app.launch(server_name=host, server_port=port, show_api=False)


if __name__ == "__main__":
    main()
