"""Formaler API-Vertrag einer Spec (Spec-Schema v1, Phase P2).

Parst den `api:`-Block einer Spec in ein typisiertes Modell. Das Modell ist die
Grundlage für den deterministischen Mock-Codegen, die Verdrahtungs-Typprüfung
in `composition.py` und die Prompt-Kontexte der LLM-Codegen-Adapter.

Typ-Ausdrücke sind Strings mit kanonischem Kern (`string`, `integer`, `number`,
`boolean`, `enum[a, b]`); alles andere (z. B. `object{...}`, `array[...]`)
bleibt als `other` erhalten — Mocks behandeln solche Werte als opaque.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

__all__ = [
    "ApiError",
    "ComponentApi",
    "EventDef",
    "Fixture",
    "Output",
    "Prop",
    "Slot",
    "TypeRef",
    "component_api",
    "infer_literal_type",
    "literal_assignable",
    "types_compatible",
]

_ENUM_PATTERN = re.compile(r"^enum\[(?P<values>[^\]]*)\]$")
_SCALARS = {"string", "integer", "number", "boolean"}


class ApiError(ValueError):
    """Der `api:`-Block ist strukturell nicht interpretierbar."""


@dataclass(frozen=True)
class TypeRef:
    """Geparster Typ-Ausdruck. `kind` ist einer der kanonischen Kerne oder `other`."""

    raw: str
    kind: str  # "string" | "integer" | "number" | "boolean" | "enum" | "other"
    enum_values: tuple[str, ...] = ()

    @classmethod
    def parse(cls, raw: str) -> TypeRef:
        text = str(raw).strip()
        if text in _SCALARS:
            return cls(raw=text, kind=text)
        enum_match = _ENUM_PATTERN.match(text)
        if enum_match:
            values = tuple(v.strip() for v in enum_match.group("values").split(",") if v.strip())
            if not values:
                raise ApiError(f"Leeres enum in Typ-Ausdruck '{raw}'.")
            return cls(raw=text, kind="enum", enum_values=values)
        return cls(raw=text, kind="other")


def types_compatible(source: TypeRef, target: TypeRef) -> bool:
    """Darf ein Wert vom Typ `source` in einen Slot vom Typ `target` fließen?

    Bewusst minimal (P2): exakte Kind-Matches, `integer` → `number`-Widening,
    Enum-Teilmengen. `other`-Typen matchen nur bei identischem Raw-String.
    """
    if source.kind == "other" or target.kind == "other":
        return source.raw == target.raw
    if source.kind == "enum" and target.kind == "enum":
        return set(source.enum_values) <= set(target.enum_values)
    if source.kind == target.kind:
        return True
    return source.kind == "integer" and target.kind == "number"


def infer_literal_type(value: Any) -> TypeRef | None:
    """TypeRef für ein YAML-Literal (Verdrahtungs-/Tree-Prop-Werte). None für Mappings/Listen."""
    if isinstance(value, bool):
        return TypeRef(raw="boolean", kind="boolean")
    if isinstance(value, int):
        return TypeRef(raw="integer", kind="integer")
    if isinstance(value, float):
        return TypeRef(raw="number", kind="number")
    if isinstance(value, str):
        return TypeRef(raw="string", kind="string")
    return None


def literal_assignable(value: Any, target: TypeRef) -> bool:
    """Darf ein YAML-Literal einem Ziel-Typ zugewiesen werden?

    Wert-bewusst: String-Literale sind Enum-Zielen zuweisbar, wenn der Wert
    Mitglied der Enum ist. Nicht-inferierbare Literale (Mappings/Listen) werden
    durchgewinkt (opaque, P2-minimal).
    """
    literal_type = infer_literal_type(value)
    if literal_type is None:
        return True
    if target.kind == "enum":
        return isinstance(value, str) and value in target.enum_values
    return types_compatible(literal_type, target)


@dataclass(frozen=True)
class Prop:
    name: str
    type: TypeRef
    required: bool = False
    default: Any = None
    has_default: bool = False
    description: str = ""
    constraints: tuple[str, ...] = ()
    map_to: tuple[str, str] | None = None  # (alias, prop) — explizites Forwarding (D3)


@dataclass(frozen=True)
class Output:
    name: str
    type: TypeRef
    description: str = ""


@dataclass(frozen=True)
class EventDef:
    name: str
    payload: tuple[tuple[str, TypeRef], ...] = ()
    description: str = ""

    def payload_field(self, name: str) -> TypeRef | None:
        for field_name, type_ref in self.payload:
            if field_name == name:
                return type_ref
        return None


@dataclass(frozen=True)
class Slot:
    name: str
    optional: bool = True
    description: str = ""


@dataclass(frozen=True)
class Fixture:
    name: str
    data: Any = None
    description: str = ""


@dataclass(frozen=True)
class ComponentApi:
    """Der vollständige API-Vertrag einer Spec."""

    props: tuple[Prop, ...] = ()
    outputs: tuple[Output, ...] = ()
    events: tuple[EventDef, ...] = ()
    slots: tuple[Slot, ...] = ()
    fixtures: tuple[Fixture, ...] = ()

    def prop(self, name: str) -> Prop | None:
        return next((p for p in self.props if p.name == name), None)

    def event(self, name: str) -> EventDef | None:
        return next((e for e in self.events if e.name == name), None)

    def slot(self, name: str) -> Slot | None:
        return next((s for s in self.slots if s.name == name), None)


def _parse_map_to(raw: Any) -> tuple[str, str] | None:
    if raw is None:
        return None
    parts = str(raw).split(".")
    if len(parts) != 2 or not all(parts):
        raise ApiError(f"Ungültiges map_to '{raw}': erwartet '<alias>.<prop>'.")
    return (parts[0], parts[1])


def _parse_props(raw: Any) -> tuple[Prop, ...]:
    props: list[Prop] = []
    for entry in raw or []:
        if not isinstance(entry, dict):
            raise ApiError(f"Prop-Eintrag muss ein Mapping sein, ist: {entry!r}")
        constraints_raw = entry.get("constraints") or []
        props.append(
            Prop(
                name=str(entry["name"]),
                type=TypeRef.parse(entry["type"]),
                required=bool(entry.get("required", False)),
                default=entry.get("default"),
                has_default="default" in entry,
                description=str(entry.get("description", "")),
                constraints=tuple(str(c) for c in constraints_raw),
                map_to=_parse_map_to(entry.get("map_to")),
            )
        )
    return tuple(props)


def _parse_events(raw: Any) -> tuple[EventDef, ...]:
    events: list[EventDef] = []
    for entry in raw or []:
        if not isinstance(entry, dict):
            raise ApiError(f"Event-Eintrag muss ein Mapping sein, ist: {entry!r}")
        payload_raw = entry.get("payload") or {}
        if not isinstance(payload_raw, dict):
            raise ApiError(f"Event-Payload von '{entry.get('name')}' muss ein Mapping sein.")
        payload = tuple(
            (str(field_name), TypeRef.parse(type_raw))
            for field_name, type_raw in payload_raw.items()
        )
        events.append(
            EventDef(
                name=str(entry["name"]),
                payload=payload,
                description=str(entry.get("description", "")),
            )
        )
    return tuple(events)


def component_api(parsed: dict[str, Any]) -> ComponentApi:
    """Parst den `api:`-Block eines geparsten Spec-Mappings (leer == leerer Vertrag)."""
    api_raw = parsed.get("api") or {}
    if not isinstance(api_raw, dict):
        raise ApiError("`api:` muss ein Mapping sein.")
    return ComponentApi(
        props=_parse_props(api_raw.get("props")),
        outputs=tuple(
            Output(
                name=str(e["name"]),
                type=TypeRef.parse(e["type"]),
                description=str(e.get("description", "")),
            )
            for e in api_raw.get("outputs") or []
        ),
        events=_parse_events(api_raw.get("events")),
        slots=tuple(
            Slot(
                name=str(e["name"]),
                optional=bool(e.get("optional", True)),
                description=str(e.get("description", "")),
            )
            for e in api_raw.get("slots") or []
        ),
        fixtures=tuple(
            Fixture(
                name=str(e["name"]),
                data=e.get("data"),
                description=str(e.get("description", "")),
            )
            for e in api_raw.get("fixtures") or []
        ),
    )


# --- Prompt-Kontext-Helfer (LLM-Codegen-Adapter) -----------------------------


def _constraint_summary(prop: Prop) -> str:
    """Kompakter Constraint-String für Prompts: required/default + freie Hints."""
    parts: list[str] = []
    if prop.required:
        parts.append("required")
    if prop.has_default:
        parts.append(f"default={prop.default}")
    parts.extend(prop.constraints)
    return ", ".join(parts)


def props_as_prompt_items(parsed: dict[str, Any]) -> list[dict[str, str]]:
    """`api.props` in das Prompt-Kontext-Format der LLM-Adapter (name/type/constraints)."""
    return [
        {"name": p.name, "type": p.type.raw, "constraints": _constraint_summary(p)}
        for p in component_api(parsed).props
    ]


def events_as_prompt_items(parsed: dict[str, Any]) -> list[dict[str, str]]:
    """`api.events` in das Prompt-Kontext-Format der LLM-Adapter (name/payload)."""
    items: list[dict[str, str]] = []
    for event in component_api(parsed).events:
        payload = ", ".join(f"{name}: {ref.raw}" for name, ref in event.payload)
        items.append({"name": event.name, "payload": payload})
    return items
