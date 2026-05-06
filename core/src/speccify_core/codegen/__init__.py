"""Codegen-Pipeline für Speccify.

Phase 1a: nur ein deterministisches Stub-Target. `speccify_core.codegen.stub` rendert
eine Spec nach Markdown — als Platzhalter für das echte React-Codegen in Phase 1b.
"""

from speccify_core.codegen.stub import (
    TEMPLATE_SET,
    TEMPLATE_VERSION,
    render,
    render_to_files,
)

__all__ = [
    "TEMPLATE_SET",
    "TEMPLATE_VERSION",
    "render",
    "render_to_files",
]
