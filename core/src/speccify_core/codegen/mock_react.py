"""Deterministischer React-Mock-Codegen (Phase P2 Stage 3, kein LLM).

Erzeugt aus dem formalen `api:`-Block einer Spec eine lauffähige
Mock-Komponente (TSX): typisierte Props, Events als Callback-Props mit
klickbaren Event-Chips, Slots als ReactNode-Props. Composite-Specs
(`composition:`) rendern als Baum ihrer Kind-Mocks inklusive Verdrahtung
(`set` → React-State, `emit` → eigener Callback). `logic`-Kinds werden
fixture-basiert gemockt (Entscheidung D1).

Determinismus: reiner Funktions-Output aus Spec-Bytes + Kind-Spec-Bytes +
`MOCK_TEMPLATE_VERSION` — kein LLM, kein Netz, keine Zeit-/Zufallswerte.
Mock und LLM-Implementierung erfüllen denselben API-Vertrag (gleiche
Props/Callbacks) und sind per Import-Swap austauschbar.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from speccify_core.api import ComponentApi, EventDef, Prop, TypeRef, component_api
from speccify_core.composition import Composition, TreeNode, parse_composition
from speccify_core.registry import Registry, Spec, Version

MOCK_TEMPLATE_SET: str = "p2-mock-react"
MOCK_TEMPLATE_VERSION: str = "0.1.0"
TARGET: str = "react"


class MockCodegenError(RuntimeError):
    """Mock-Generierung ist fehlgeschlagen (Spec-Struktur, Auflösung)."""


class MockUnavailableError(MockCodegenError):
    """Für diese Spec ist kein Mock generierbar (z. B. logic ohne Fixtures)."""


@dataclass(frozen=True)
class MockRender:
    """Ergebnis eines Mock-Renders: `{relativer_pfad: bytes}` + Template-Pin."""

    files: dict[str, bytes]
    template_set: str
    template_version: str


# --- Namens- und Typ-Helfer ---------------------------------------------------


def _split_scoped_id(spec_id: str) -> tuple[str, str]:
    if not spec_id.startswith("@") or "/" not in spec_id:
        raise MockCodegenError(
            f"Spec-Id '{spec_id}' nicht im Format '@scope/name' — der Mock-Codegen "
            f"unterstützt nur scoped IDs (Registry-Layout)."
        )
    scope, name = spec_id[1:].split("/", 1)
    return scope, name


def _component_name(spec_id: str) -> str:
    """`@org/search-bar` → `SearchBar`."""
    _, name = _split_scoped_id(spec_id)
    return "".join(part.capitalize() for part in name.replace("_", "-").split("-") if part)


def _camel(snake: str) -> str:
    parts = [p for p in snake.split("_") if p]
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _event_prop_name(event_name: str) -> str:
    return "on" + "".join(p.capitalize() for p in event_name.split("_") if p)


def _ts_type(type_ref: TypeRef) -> str:
    if type_ref.kind == "string":
        return "string"
    if type_ref.kind in ("integer", "number"):
        return "number"
    if type_ref.kind == "boolean":
        return "boolean"
    if type_ref.kind == "enum":
        return " | ".join(json.dumps(v) for v in type_ref.enum_values)
    return "unknown"


def _ts_literal(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _type_default_literal(type_ref: TypeRef) -> str:
    if type_ref.kind == "string":
        return '""'
    if type_ref.kind in ("integer", "number"):
        return "0"
    if type_ref.kind == "boolean":
        return "false"
    if type_ref.kind == "enum":
        return json.dumps(type_ref.enum_values[0])
    return "undefined"


def _coerce_expr(expr: str, target: TypeRef) -> str:
    """Wrappt einen `unknown`-Ausdruck in eine Koerzion auf den Ziel-TS-Typ."""
    if target.kind == "string":
        return f'String({expr} ?? "")'
    if target.kind in ("integer", "number"):
        return f"Number({expr} ?? 0)"
    if target.kind == "boolean":
        return f"Boolean({expr} ?? false)"
    if target.kind == "enum":
        return f"(({expr}) ?? {_type_default_literal(target)}) as {_ts_type(target)}"
    return f"({expr}) as unknown"


# --- Props-Interface ----------------------------------------------------------


def _props_interface_lines(component: str, api: ComponentApi) -> list[str]:
    lines = [f"export interface {component}Props {{"]
    for prop in api.props:
        optional = "" if (prop.required and not prop.has_default) else "?"
        lines.append(f"  {_camel(prop.name)}{optional}: {_ts_type(prop.type)};")
    for slot in api.slots:
        lines.append(f"  {_camel(slot.name)}?: React.ReactNode;")
    for event in api.events:
        payload = _payload_ts(event)
        signature = f"(payload: {payload}) => void" if payload else "() => void"
        lines.append(f"  {_event_prop_name(event.name)}?: {signature};")
    lines.append("}")
    return lines


def _payload_ts(event: EventDef) -> str | None:
    if not event.payload:
        return None
    fields = "; ".join(f"{_camel(name)}: {_ts_type(ref)}" for name, ref in event.payload)
    return f"{{ {fields} }}"


# --- Gemeinsame Styles --------------------------------------------------------

_STYLE_LINES = [
    "const mockStyles = {",
    "  container: {",
    '    border: "1px dashed #94a3b8",',
    "    borderRadius: 8,",
    "    padding: 12,",
    '    fontFamily: "ui-monospace, monospace",',
    "    fontSize: 13,",
    '    display: "grid",',
    "    gap: 8,",
    "  },",
    '  header: { display: "flex", gap: 8, alignItems: "baseline" },',
    "  title: { fontWeight: 700 },",
    "  badge: {",
    '    background: "#e2e8f0",',
    "    borderRadius: 4,",
    '    padding: "1px 6px",',
    "    fontSize: 11,",
    "  },",
    '  props: { margin: 0, display: "grid", '
    + 'gridTemplateColumns: "max-content 1fr", gap: "2px 12px" },',
    '  propName: { color: "#64748b" },',
    '  events: { display: "flex", gap: 6, flexWrap: "wrap" as const },',
    "  eventChip: {",
    '    border: "1px solid #94a3b8",',
    "    borderRadius: 999,",
    '    background: "#f8fafc",',
    '    padding: "2px 10px",',
    '    cursor: "pointer",',
    "    fontSize: 12,",
    "  },",
    '  slot: { border: "1px dotted #cbd5e1", borderRadius: 6, padding: 8 },',
    "} as const;",
]


def _header_lines(spec: Spec) -> list[str]:
    return [
        "// AUTO-GENERATED by `speccify mock` — deterministischer Mock (kein LLM).",
        f"// Spec: {spec.spec_id}@{spec.version} · {MOCK_TEMPLATE_SET} v{MOCK_TEMPLATE_VERSION}",
        'import * as React from "react";',
    ]


# --- Leaf-Mock (ui-component / screen / workflow ohne composition) ------------


def _prop_value_expr(prop: Prop) -> str:
    base = f"props.{_camel(prop.name)}"
    if prop.has_default:
        return f"{base} ?? {_ts_literal(prop.default)}"
    return base


def _payload_synthesis_expr(event: EventDef, api: ComponentApi) -> str:
    """Payload-Objekt für einen Event-Chip: Felder aus gleichnamigen Props, sonst Typ-Default."""
    parts = []
    for field_name, type_ref in event.payload:
        prop = api.prop(field_name)
        if prop is not None:
            source = _coerce_expr(f"props.{_camel(prop.name)}", type_ref)
        else:
            source = _type_default_literal(type_ref)
        parts.append(f"{_camel(field_name)}: {source}")
    return "{ " + ", ".join(parts) + " }"


def _leaf_component_lines(spec: Spec, api: ComponentApi) -> list[str]:
    component = _component_name(spec.spec_id)
    lines: list[str] = []
    lines.append(
        f"export default function {component}(props: {component}Props): React.ReactElement {{"
    )
    lines.append("  return (")
    lines.append(f'    <div data-speccify-mock="{spec.spec_id}" style={{mockStyles.container}}>')
    lines.append("      <div style={mockStyles.header}>")
    lines.append(f"        <span style={{mockStyles.title}}>{component}</span>")
    lines.append("        <span style={mockStyles.badge}>mock</span>")
    lines.append("      </div>")
    if api.props:
        lines.append("      <dl style={mockStyles.props}>")
        for prop in api.props:
            lines.append(f"        <dt style={{mockStyles.propName}}>{prop.name}</dt>")
            lines.append(f"        <dd>{{String({_prop_value_expr(prop)})}}</dd>")
        lines.append("      </dl>")
    for slot in api.slots:
        camel = _camel(slot.name)
        lines.append(f"      {{props.{camel} !== undefined ? (")
        lines.append(f'        <div data-speccify-slot="{slot.name}" style={{mockStyles.slot}}>')
        lines.append(f"          {{props.{camel}}}")
        lines.append("        </div>")
        lines.append("      ) : null}")
    if api.events:
        lines.append("      <div style={mockStyles.events}>")
        for event in api.events:
            handler = _event_prop_name(event.name)
            if event.payload:
                payload_expr = _payload_synthesis_expr(event, api)
                on_click = f"() => props.{handler}?.({payload_expr})"
            else:
                on_click = f"() => props.{handler}?.()"
            lines.append(
                f'        <button type="button" style={{mockStyles.eventChip}} '
                f"onClick={{{on_click}}}>⚡ {event.name}</button>"
            )
        lines.append("      </div>")
    lines.append("    </div>")
    lines.append("  );")
    lines.append("}")
    return lines


# --- Composite-Mock -----------------------------------------------------------


def _import_path(own_id: str, child_id: str) -> str:
    own_scope, _ = _split_scoped_id(own_id)
    child_scope, _ = _split_scoped_id(child_id)
    child_component = _component_name(child_id)
    if own_scope == child_scope:
        return f"./{child_component}.mock"
    return f"../{child_scope}/{child_component}.mock"


def _mapped_entry_expr(prop: Prop) -> str:
    """`map_to`-Weiterleitung: eigener Prop-Wert (mit Default) für die Kind-Prop."""
    if prop.has_default:
        return f"props.{_camel(prop.name)} ?? {_ts_literal(prop.default)}"
    return f"props.{_camel(prop.name)}"


def _source_expr(source: Any, target: TypeRef) -> str:
    """Wert-Quelle einer Wiring-Regel als TS-Ausdruck (payload/props/Literal)."""
    if isinstance(source, str) and source.startswith("payload."):
        field = _camel(source[len("payload.") :])
        return _coerce_expr(f'(payload as Record<string, unknown>)["{field}"]', target)
    if isinstance(source, str) and source.startswith("props."):
        _, alias, prop_name = source.split(".")
        return _coerce_expr(f'nodeProp("{alias}", "{_camel(prop_name)}")', target)
    return _ts_literal(source)


def _composite_component_lines(
    spec: Spec,
    api: ComponentApi,
    composition: Composition,
    children: Mapping[str, Spec],
) -> list[str]:
    component = _component_name(spec.spec_id)
    child_apis = {alias: component_api(child.parsed()) for alias, child in children.items()}
    lines: list[str] = []

    # Statische Tree-Props (Deklarationsreihenfolge = Spec-Reihenfolge).
    lines.append("type NodeProps = Record<string, Record<string, unknown>>;")
    lines.append("")
    lines.append("const staticNodeProps: NodeProps = {")
    for _, node in _iter_tree(composition.tree):
        entries = ", ".join(
            f'"{_camel(name)}": {_ts_literal(value)}' for name, value in node.props.items()
        )
        lines.append(f'  "{node.alias}": {{ {entries} }},')
    lines.append("};")
    lines.append("")

    lines.append(
        f"export default function {component}(props: {component}Props): React.ReactElement {{{{"[
            :-2
        ]
        + "{"
    )
    lines.append("  const [wired, setWired] = React.useState<NodeProps>({});")
    lines.append("")

    # map_to-Weiterleitungen (D3: nur explizit).
    lines.append("  const mapped: NodeProps = {")
    mapped_by_alias: dict[str, list[str]] = {}
    for prop in api.props:
        if prop.map_to is None:
            continue
        alias, target_prop = prop.map_to
        mapped_by_alias.setdefault(alias, []).append(
            f'"{_camel(target_prop)}": {_mapped_entry_expr(prop)}'
        )
    for alias in composition.uses:
        entries = ", ".join(mapped_by_alias.get(alias, []))
        lines.append(f'    "{alias}": {{ {entries} }},')
    lines.append("  };")
    lines.append("")

    lines.append("  const nodeProp = (alias: string, prop: string): unknown =>")
    lines.append("    (wired[alias] ?? {})[prop] ??")
    lines.append("    (mapped[alias] ?? {})[prop] ??")
    lines.append("    (staticNodeProps[alias] ?? {})[prop];")
    lines.append("")
    lines.append("  const collectNodeProps = (alias: string): Record<string, unknown> => {")
    lines.append("    const merged: Record<string, unknown> =")
    lines.append("      { ...(staticNodeProps[alias] ?? {}) };")
    lines.append("    for (const [key, value] of Object.entries(mapped[alias] ?? {})) {")
    lines.append("      if (value !== undefined) merged[key] = value;")
    lines.append("    }")
    lines.append("    for (const [key, value] of Object.entries(wired[alias] ?? {})) {")
    lines.append("      if (value !== undefined) merged[key] = value;")
    lines.append("    }")
    lines.append("    return merged;")
    lines.append("  };")
    lines.append("")

    # Wiring-Dispatcher.
    lines.append("  const fire = (event: string, payload: unknown): void => {")
    lines.append("    void payload;")
    for rule in composition.wiring:
        alias, event_name = rule.when
        lines.append(f'    if (event === "{alias}.{event_name}") {{')
        if rule.set_ is not None:
            set_alias, set_prop = rule.set_
            target_prop = child_apis[set_alias].prop(set_prop) if set_alias in child_apis else None
            target_type = target_prop.type if target_prop else TypeRef(raw="unknown", kind="other")
            value_expr = _source_expr(rule.to, target_type)
            lines.append(
                f'      setWired((w) => ({{ ...w, "{set_alias}": '
                f'{{ ...(w["{set_alias}"] ?? {{}}), "{_camel(set_prop)}": {value_expr} }} }}));'
            )
        if rule.emit is not None:
            own_event = api.event(rule.emit)
            handler = _event_prop_name(rule.emit)
            if own_event is not None and own_event.payload:
                parts = []
                for field_name, type_ref in own_event.payload:
                    source = rule.with_.get(field_name)
                    parts.append(f"{_camel(field_name)}: {_source_expr(source, type_ref)}")
                lines.append(f"      props.{handler}?.({{ {', '.join(parts)} }});")
            else:
                lines.append(f"      props.{handler}?.();")
        lines.append("    }")
    lines.append("  };")
    lines.append("")

    # JSX-Baum.
    lines.append("  return (")
    lines.append(f'    <div data-speccify-mock="{spec.spec_id}" style={{mockStyles.container}}>')
    lines.append("      <div style={mockStyles.header}>")
    lines.append(f"        <span style={{mockStyles.title}}>{component}</span>")
    lines.append("        <span style={mockStyles.badge}>mock · composite</span>")
    lines.append("      </div>")
    for node in composition.tree:
        lines.extend(_composite_node_jsx(node, children, child_apis, indent="      "))
    lines.append("    </div>")
    lines.append("  );")
    lines.append("}")
    return lines


def _composite_node_jsx(
    node: TreeNode,
    children: Mapping[str, Spec],
    child_apis: Mapping[str, ComponentApi],
    *,
    indent: str,
) -> list[str]:
    child_spec = children[node.alias]
    child_component = _component_name(child_spec.spec_id)
    child_api = child_apis[node.alias]
    lines = [f"{indent}<{child_component}"]
    lines.append(
        f'{indent}  {{...(collectNodeProps("{node.alias}") as unknown as {child_component}Props)}}'
    )
    for event in child_api.events:
        handler = _event_prop_name(event.name)
        payload_ts = _payload_ts(event)
        if payload_ts:
            lines.append(f"{indent}  {handler}={{(payload: {payload_ts}) =>")
            lines.append(f'{indent}    fire("{node.alias}.{event.name}", payload)}}')
        else:
            lines.append(f'{indent}  {handler}={{() => fire("{node.alias}.{event.name}", {{}})}}')
    for slot_name, slot_children in node.slots.items():
        slot_lines: list[str] = []
        for slot_child in slot_children:
            slot_lines.extend(
                _composite_node_jsx(slot_child, children, child_apis, indent=indent + "    ")
            )
        lines.append(f"{indent}  {_camel(slot_name)}={{")
        lines.append(f"{indent}    <>")
        lines.extend(slot_lines)
        lines.append(f"{indent}    </>")
        lines.append(f"{indent}  }}")
    lines.append(f"{indent}/>")
    return lines


def _iter_tree(nodes: tuple[TreeNode, ...]):
    for node in nodes:
        yield "", node
        for slot_children in node.slots.values():
            yield from _iter_tree(slot_children)


# --- Logic-Mock (fixture-basiert, D1) ----------------------------------------


def _logic_mock_source(spec: Spec, api: ComponentApi) -> str:
    if not api.fixtures:
        raise MockUnavailableError(
            f"Spec {spec.spec_id}@{spec.version} (kind: logic) deklariert keine "
            f"`api.fixtures` — fixture-basierter Mock nicht generierbar (Entscheidung D1)."
        )
    lines = [
        "// AUTO-GENERATED by `speccify mock` — deterministischer Fixture-Mock (kein LLM).",
        f"// Spec: {spec.spec_id}@{spec.version} · {MOCK_TEMPLATE_SET} v{MOCK_TEMPLATE_VERSION}",
        "",
        "export const fixtures = {",
    ]
    for fixture in api.fixtures:
        data_json = json.dumps(fixture.data, ensure_ascii=False, sort_keys=True)
        lines.append(f'  "{fixture.name}": {data_json},')
    lines.append("} as const;")
    lines.append("")
    lines.append("export type FixtureName = keyof typeof fixtures;")
    lines.append("")
    lines.append("export function fixture(name: FixtureName): (typeof fixtures)[FixtureName] {")
    lines.append("  return fixtures[name];")
    lines.append("}")
    lines.append("")
    lines.append("export default fixtures;")
    return "\n".join(lines) + "\n"


# --- Öffentliche Render-API ---------------------------------------------------


def _output_path(spec_id: str, *, kind: str) -> str:
    scope, _ = _split_scoped_id(spec_id)
    extension = "ts" if kind == "logic" else "tsx"
    return f"{scope}/{_component_name(spec_id)}.mock.{extension}"


def render_mock_files(spec: Spec, children: Mapping[str, Spec] | None = None) -> dict[str, bytes]:
    """Rendert den Mock für genau eine Spec (Kind-Mocks werden importiert, nicht generiert)."""
    parsed = spec.parsed()
    kind = str(parsed.get("kind", ""))
    api = component_api(parsed)

    if kind == "logic":
        source = _logic_mock_source(spec, api)
        return {_output_path(spec.spec_id, kind=kind): source.encode("utf-8")}

    composition = parse_composition(parsed)
    component = _component_name(spec.spec_id)
    lines = _header_lines(spec)

    if composition is not None:
        resolved_children = dict(children or {})
        missing = [alias for alias in composition.uses if alias not in resolved_children]
        if missing:
            raise MockCodegenError(
                f"Composite {spec.spec_id}: Kind-Specs für Aliase {missing} nicht übergeben."
            )
        seen_imports: set[str] = set()
        for alias in composition.uses:
            child = resolved_children[alias]
            child_component = _component_name(child.spec_id)
            if child_component in seen_imports:
                continue
            seen_imports.add(child_component)
            path = _import_path(spec.spec_id, child.spec_id)
            lines.append(f'import {child_component} from "{path}";')
            lines.append(f'import type {{ {child_component}Props }} from "{path}";')
        lines.append("")
        lines.extend(_props_interface_lines(component, api))
        lines.append("")
        lines.extend(_STYLE_LINES)
        lines.append("")
        lines.extend(_composite_component_lines(spec, api, composition, resolved_children))
    else:
        lines.append("")
        lines.extend(_props_interface_lines(component, api))
        lines.append("")
        lines.extend(_STYLE_LINES)
        lines.append("")
        lines.extend(_leaf_component_lines(spec, api))

    source = "\n".join(lines) + "\n"
    return {_output_path(spec.spec_id, kind=kind): source.encode("utf-8")}


def _select_version(registry: Registry, spec_id: str, range_raw: str) -> Version:
    """MVS-Minimum: kleinste verfügbare Version, die die Range erfüllt."""
    from speccify_core.resolver import Range

    parsed_range = Range.parse(range_raw) if range_raw else None
    versions = registry.list_versions(spec_id)
    for version in versions:  # aufsteigend sortiert
        if parsed_range is None or parsed_range.contains(version):
            return version
    raise MockCodegenError(
        f"Keine Version von {spec_id} erfüllt '{range_raw}' "
        f"(verfügbar: {', '.join(str(v) for v in versions) or 'keine'})."
    )


def _parse_child_ref(ref: str) -> tuple[str, str]:
    """`@org/button@^0.1` → (`@org/button`, `^0.1`); Range optional."""
    if not ref.startswith("@"):
        raise MockCodegenError(
            f"Kompositions-Referenz '{ref}' ist nicht scoped (@scope/name) — "
            f"nur Registry-auflösbare IDs sind mockbar."
        )
    body = ref[1:]
    if "@" in body:
        id_part, range_raw = body.split("@", 1)
        return f"@{id_part}", range_raw
    return ref, ""


def render_mock_closure(spec: Spec, registry: Registry) -> MockRender:
    """Rendert eine Spec + alle transitiven Kompositions-Kinder als Mock-Dateien."""
    files: dict[str, bytes] = {}
    visited: set[str] = set()

    def _render(current: Spec) -> None:
        marker = f"{current.spec_id}@{current.version}"
        if marker in visited:
            return
        visited.add(marker)
        composition = parse_composition(current.parsed())
        children: dict[str, Spec] = {}
        if composition is not None:
            for alias, ref in composition.uses.items():
                child_id, range_raw = _parse_child_ref(ref)
                version = _select_version(registry, child_id, range_raw)
                children[alias] = registry.fetch(child_id, version)
        for child in children.values():
            _render(child)
        files.update(render_mock_files(current, children))

    _render(spec)
    return MockRender(
        files=files,
        template_set=MOCK_TEMPLATE_SET,
        template_version=MOCK_TEMPLATE_VERSION,
    )
