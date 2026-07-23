"""Stub-Codegen: rendert eine Spec deterministisch nach Markdown.

Phase 1a: Platzhalter, der die Codegen-Pipeline und das Lockfile-Output-Hashing
durchspielt, ohne ein echtes Ziel-Framework zu erzeugen. Das echte React-Codegen
folgt in Phase 1b.

Determinismus:
- Keine Datums-/Zufallswerte im Output.
- `template_set` + `template_version` werden im Output und im Lockfile gepinnt.
- Das Jinja-Environment hat `keep_trailing_newline=True` und `trim_blocks=False`,
  damit identische Inputs zu byte-identischem Output führen.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from speccify_core.api import component_api, events_as_prompt_items, props_as_prompt_items
from speccify_core.registry import Spec

TEMPLATE_SET: str = "phase-1a-stub"
# 0.2.0: Kontext liest den formalen `api:`-Block (Spec-Schema v1, P2).
TEMPLATE_VERSION: str = "0.2.0"

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_TEMPLATE_NAME = "stub.md.j2"


def _make_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
        autoescape=False,
    )


def _normalise_items(raw: Any, fields: tuple[str, ...]) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    items: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        item: dict[str, str] = {}
        for field in fields:
            value = entry.get(field, "")
            if isinstance(value, list):
                item[field] = ", ".join(str(v) for v in value)
            elif value is None:
                item[field] = ""
            else:
                item[field] = str(value)
        items.append(item)
    return items


def _normalise_uses(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if isinstance(item, (str, int, float))]


def _build_context(spec: Spec, target: str) -> dict[str, Any]:
    parsed = spec.parsed()
    return {
        "target": target,
        "spec_id": spec.spec_id,
        "spec_version": str(spec.version),
        "template_set": TEMPLATE_SET,
        "template_version": TEMPLATE_VERSION,
        "title": str(parsed.get("title", spec.spec_id)),
        "summary": str(parsed.get("summary", "")).strip(),
        "kind": str(parsed.get("kind", "")),
        "inputs": props_as_prompt_items(parsed),
        "outputs": [{"name": o.name, "type": o.type.raw} for o in component_api(parsed).outputs],
        "events": events_as_prompt_items(parsed),
        "acceptance": _normalise_items(parsed.get("acceptance"), ("given", "when", "then")),
        "uses": _normalise_uses(parsed.get("uses")),
    }


def render(spec: Spec, target: str) -> str:
    """Rendert eine Spec deterministisch zu Markdown-Text."""
    env = _make_environment()
    template = env.get_template(_TEMPLATE_NAME)
    return template.render(_build_context(spec, target))


def render_to_files(spec: Spec, target: str) -> dict[str, bytes]:
    """Rendert eine Spec und gibt `{relativer_pfad: bytes}` zurück.

    Pfad-Konvention: `<scope>/<name>.md` aus der Spec-Id `@<scope>/<name>`.
    """
    text = render(spec, target)
    rel_path = _output_path(spec.spec_id)
    return {rel_path: text.encode("utf-8")}


def _output_path(spec_id: str) -> str:
    if not spec_id.startswith("@") or "/" not in spec_id:
        raise ValueError(
            f"Spec-Id '{spec_id}' nicht im Format '@scope/name' — Stub-Codegen "
            f"unterstützt in Phase 1a nur scoped IDs."
        )
    scope, name = spec_id[1:].split("/", 1)
    return f"{scope}/{name}.md"
