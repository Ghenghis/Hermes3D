"""Hermes3D GUI API surface."""

from .app import create_gui_app

create_app = create_gui_app

__all__ = ["create_app", "create_gui_app"]
