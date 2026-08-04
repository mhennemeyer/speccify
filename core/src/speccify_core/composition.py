"""Komposition aus Unterkomponenten (Spec-Schema v1, Phase P2).

Parst den `composition:`-Block und prüft die Verdrahtung typgestützt gegen die
`api:`-Blöcke der Kinder (Entscheidung D3: kein automatisches Durchreichen —
Prop-Forwarding nur über explizites `map_to`, Event-Re-Export nur über
`wiring.emit`).

Wert-Quellen in der Verdrahtung (`wiring[].to` / `wiring[].with.*`):
- ``payload.<field>`` — Feld aus dem Payload des auslösenden Events,
- ``props.<alias>.<prop>`` — aktueller Prop-Wert eines Kindes,
- YAML-Literal (string/number/boolean/null).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from speccify_core.api import (
    ComponentApi,
    TypeRef,
    component_api,
    literal_assignable,
    types_compatible,
)

__all__ = [
    "Composition",
    "CompositionIssue",
    "CompositionResolutionError",
    "TreeNode",
    "WiringRule",
    "parse_child_ref",
    "parse_composition",
    "resolve_composition_children",
    "validate_composition",
]


class CompositionResolutionError(RuntimeError):
    """Kompositions-Kinder konnten nicht gegen die Registry aufgelöst werden."""


@dataclass(frozen=True)
class TreeNode:
    alias: str
    props: dict[str, Any] = field(default_factory=dict)
    slots: dict[str, tuple[TreeNode, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class WiringRule:
    when: tuple[str, str]  # (alias, event)
    emit: str | None = None
    with_: dict[str, Any] = field(default_factory=dict)
    set_: tuple[str, str] | None = None  # (alias, prop)
    to: Any = None
    navigate: str | None = None  # Route-Pfad; nur `kind: app` (P4, Entscheidung D11)


@dataclass(frozen=True)
class Composition:
    uses: dict[str, str]  # alias → Spec-Referenz (mit optionalem Range-Suffix)
    tree: tuple[TreeNode, ...]
    wiring: tuple[WiringRule, ...]


@dataclass(frozen=True)
class CompositionIssue:
    """Ein Befund der Kompositions-Validierung, adressierbar über einen JSON-Pfad."""

    path: str
    message: str

    def format(self) -> str:
        return f"{self.path}: {self.message}"


def _parse_tree_node(raw: dict[str, Any]) -> TreeNode:
    slots_raw = raw.get("slots") or {}
    slots = {
        str(slot_name): tuple(_parse_tree_node(child) for child in children or [])
        for slot_name, children in slots_raw.items()
    }
    return TreeNode(
        alias=str(raw["node"]),
        props=dict(raw.get("props") or {}),
        slots=slots,
    )


def _split_ref(raw: str, expected: str) -> tuple[str, str]:
    parts = str(raw).split(".")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"Ungültige {expected}-Referenz '{raw}': erwartet '<alias>.<name>'.")
    return (parts[0], parts[1])


def parse_composition(parsed: dict[str, Any]) -> Composition | None:
    """Parst `composition:` aus einem Spec-Mapping; None wenn nicht vorhanden."""
    raw = parsed.get("composition")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("`composition:` muss ein Mapping sein.")
    uses = {str(alias): str(ref) for alias, ref in (raw.get("uses") or {}).items()}
    tree = tuple(_parse_tree_node(node) for node in raw.get("tree") or [])
    wiring: list[WiringRule] = []
    for entry in raw.get("wiring") or []:
        wiring.append(
            WiringRule(
                when=_split_ref(entry["when"], "when"),
                emit=str(entry["emit"]) if "emit" in entry else None,
                with_=dict(entry.get("with") or {}),
                set_=_split_ref(entry["set"], "set") if "set" in entry else None,
                to=entry.get("to"),
                navigate=str(entry["navigate"]) if "navigate" in entry else None,
            )
        )
    return Composition(uses=uses, tree=tree, wiring=tuple(wiring))


# --- Kind-Auflösung gegen eine Registry ---------------------------------------


def parse_child_ref(ref: str) -> tuple[str, str]:
    """`@org/button@^0.1` → (`@org/button`, `^0.1`); Range optional."""
    if not ref.startswith("@"):
        raise CompositionResolutionError(
            f"Kompositions-Referenz '{ref}' ist nicht scoped (@scope/name) — "
            f"nur Registry-auflösbare IDs sind auflösbar."
        )
    body = ref[1:]
    if "@" in body:
        id_part, range_raw = body.split("@", 1)
        return f"@{id_part}", range_raw
    return ref, ""


def resolve_composition_children(composition: Composition, registry) -> dict[str, Any]:
    """Löst jeden `composition.uses`-Alias auf eine konkrete Spec auf (MVS-Minimum).

    Rückgabe: `{alias: Spec}`. `registry` erfüllt das `Registry`-Protocol aus
    `speccify_core.registry` (kein direkter Import, um Zyklen zu vermeiden).
    """
    from speccify_core.resolver import Range

    children: dict[str, Any] = {}
    for alias, ref in composition.uses.items():
        child_id, range_raw = parse_child_ref(ref)
        parsed_range = Range.parse(range_raw) if range_raw else None
        versions = registry.list_versions(child_id)
        chosen = next(
            (v for v in versions if parsed_range is None or parsed_range.contains(v)),
            None,
        )
        if chosen is None:
            available = ", ".join(str(v) for v in versions) or "keine"
            raise CompositionResolutionError(
                f"Keine Version von {child_id} erfüllt '{range_raw}' (verfügbar: {available})."
            )
        children[alias] = registry.fetch(child_id, chosen)
    return children


# --- Validierung --------------------------------------------------------------


def _iter_tree(nodes: tuple[TreeNode, ...], path: str):
    for index, node in enumerate(nodes):
        node_path = f"{path}[{index}]"
        yield node_path, node
        for slot_name, children in node.slots.items():
            yield from _iter_tree(children, f"{node_path}.slots.{slot_name}")


def _is_reference(source: Any) -> bool:
    return isinstance(source, str) and (
        source.startswith("payload.") or source.startswith("props.")
    )


def _reference_type(
    source: str,
    *,
    trigger_payload: Mapping[str, TypeRef],
    children: Mapping[str, ComponentApi],
    path: str,
    issues: list[CompositionIssue],
) -> TypeRef | None:
    """Bestimmt den Typ einer Referenz-Quelle; meldet unauflösbare Referenzen als Issue."""
    if source.startswith("payload."):
        field_name = source[len("payload.") :]
        type_ref = trigger_payload.get(field_name)
        if type_ref is None:
            issues.append(
                CompositionIssue(
                    path, f"Payload-Feld '{field_name}' existiert nicht am auslösenden Event."
                )
            )
        return type_ref
    parts = source.split(".")
    if len(parts) != 3:
        issues.append(
            CompositionIssue(path, f"Ungültige Quelle '{source}': erwartet 'props.<alias>.<prop>'.")
        )
        return None
    _, alias, prop_name = parts
    child = children.get(alias)
    if child is None:
        issues.append(CompositionIssue(path, f"Unbekannter Knoten '{alias}' in '{source}'."))
        return None
    prop = child.prop(prop_name)
    if prop is None:
        issues.append(
            CompositionIssue(path, f"Kind '{alias}' hat keine Prop '{prop_name}' ('{source}').")
        )
        return None
    return prop.type


def _check_assignment(
    source: Any,
    target: TypeRef,
    *,
    trigger_payload: Mapping[str, TypeRef],
    children: Mapping[str, ComponentApi],
    path: str,
    target_desc: str,
    issues: list[CompositionIssue],
) -> None:
    """Prüft, ob eine Wert-Quelle (Referenz oder Literal) in den Ziel-Typ passt."""
    if _is_reference(source):
        source_type = _reference_type(
            source,
            trigger_payload=trigger_payload,
            children=children,
            path=path,
            issues=issues,
        )
        if source_type is not None and not types_compatible(source_type, target):
            issues.append(
                CompositionIssue(
                    path,
                    f"Quelle ({source_type.raw}) passt nicht zu {target_desc} '{target.raw}'.",
                )
            )
    elif not literal_assignable(source, target):
        issues.append(
            CompositionIssue(
                path,
                f"Wert {source!r} passt nicht zu {target_desc} '{target.raw}'.",
            )
        )


def validate_composition(
    parsed: dict[str, Any],
    children: Mapping[str, ComponentApi],
) -> list[CompositionIssue]:
    """Prüft `composition:` + `api.props[].map_to` gegen die Kind-APIs.

    `children` mappt jeden Alias aus `composition.uses` auf den aufgelösten
    API-Vertrag des Kindes (Auflösung übernimmt der Aufrufer, z. B. über eine
    Registry — dieses Modul bleibt registry-frei).
    """
    issues: list[CompositionIssue] = []
    composition = parse_composition(parsed)
    own_api = component_api(parsed)

    if composition is None:
        return issues

    # --- uses ↔ children-Abdeckung -------------------------------------------
    for alias in composition.uses:
        if alias not in children:
            issues.append(
                CompositionIssue(
                    "$.composition.uses", f"Kein API-Vertrag für Alias '{alias}' übergeben."
                )
            )
    used_aliases = {node.alias for _, node in _iter_tree(composition.tree, "$.composition.tree")}
    for alias in composition.uses:
        if alias not in used_aliases:
            issues.append(
                CompositionIssue(
                    "$.composition.tree", f"Alias '{alias}' aus uses kommt im tree nicht vor."
                )
            )

    # --- tree: Aliase + statische Props --------------------------------------
    for node_path, node in _iter_tree(composition.tree, "$.composition.tree"):
        if node.alias not in composition.uses:
            issues.append(
                CompositionIssue(
                    node_path, f"Knoten '{node.alias}' ist nicht in composition.uses deklariert."
                )
            )
            continue
        child = children.get(node.alias)
        if child is None:
            continue
        for prop_name, value in node.props.items():
            prop = child.prop(prop_name)
            if prop is None:
                issues.append(
                    CompositionIssue(
                        f"{node_path}.props.{prop_name}",
                        f"Kind '{node.alias}' hat keine Prop '{prop_name}'.",
                    )
                )
                continue
            if not literal_assignable(value, prop.type):
                issues.append(
                    CompositionIssue(
                        f"{node_path}.props.{prop_name}",
                        f"Wert {value!r} passt nicht zu Prop-Typ '{prop.type.raw}'.",
                    )
                )
        for slot_name in node.slots:
            if child.slot(slot_name) is None:
                issues.append(
                    CompositionIssue(
                        f"{node_path}.slots.{slot_name}",
                        f"Kind '{node.alias}' hat keinen Slot '{slot_name}'.",
                    )
                )

    # --- api.props[].map_to (explizites Forwarding, D3) -----------------------
    for prop in own_api.props:
        if prop.map_to is None:
            continue
        alias, target_name = prop.map_to
        prop_path = f"$.api.props[{prop.name}].map_to"
        child = children.get(alias)
        if alias not in composition.uses or child is None:
            issues.append(CompositionIssue(prop_path, f"Unbekannter Knoten '{alias}'."))
            continue
        target = child.prop(target_name)
        if target is None:
            issues.append(
                CompositionIssue(prop_path, f"Kind '{alias}' hat keine Prop '{target_name}'.")
            )
            continue
        if not types_compatible(prop.type, target.type):
            issues.append(
                CompositionIssue(
                    prop_path,
                    f"Typ '{prop.type.raw}' passt nicht zu "
                    f"'{alias}.{target_name}' ('{target.type.raw}').",
                )
            )

    # --- wiring ---------------------------------------------------------------
    for index, rule in enumerate(composition.wiring):
        rule_path = f"$.composition.wiring[{index}]"
        alias, event_name = rule.when
        child = children.get(alias)
        if alias not in composition.uses or child is None:
            issues.append(CompositionIssue(f"{rule_path}.when", f"Unbekannter Knoten '{alias}'."))
            continue
        trigger = child.event(event_name)
        if trigger is None:
            issues.append(
                CompositionIssue(
                    f"{rule_path}.when", f"Kind '{alias}' hat kein Event '{event_name}'."
                )
            )
            continue
        trigger_payload = dict(trigger.payload)

        if rule.emit is not None:
            own_event = own_api.event(rule.emit)
            if own_event is None:
                issues.append(
                    CompositionIssue(
                        f"{rule_path}.emit",
                        f"Eigenes Event '{rule.emit}' existiert nicht in api.events.",
                    )
                )
                continue
            expected_fields = {name for name, _ in own_event.payload}
            provided_fields = set(rule.with_.keys())
            for missing in sorted(expected_fields - provided_fields):
                issues.append(
                    CompositionIssue(
                        f"{rule_path}.with",
                        f"Payload-Feld '{missing}' von '{rule.emit}' fehlt im Mapping.",
                    )
                )
            for extra in sorted(provided_fields - expected_fields):
                issues.append(
                    CompositionIssue(
                        f"{rule_path}.with.{extra}",
                        f"'{rule.emit}' hat kein Payload-Feld '{extra}'.",
                    )
                )
            for field_name, source in rule.with_.items():
                target_type = own_event.payload_field(field_name)
                if target_type is None:
                    continue
                _check_assignment(
                    source,
                    target_type,
                    trigger_payload=trigger_payload,
                    children=children,
                    path=f"{rule_path}.with.{field_name}",
                    target_desc="Payload-Typ",
                    issues=issues,
                )

        if rule.set_ is not None:
            target_alias, target_prop_name = rule.set_
            target_child = children.get(target_alias)
            if target_alias not in composition.uses or target_child is None:
                issues.append(
                    CompositionIssue(f"{rule_path}.set", f"Unbekannter Knoten '{target_alias}'.")
                )
                continue
            target_prop = target_child.prop(target_prop_name)
            if target_prop is None:
                issues.append(
                    CompositionIssue(
                        f"{rule_path}.set",
                        f"Kind '{target_alias}' hat keine Prop '{target_prop_name}'.",
                    )
                )
                continue
            _check_assignment(
                rule.to,
                target_prop.type,
                trigger_payload=trigger_payload,
                children=children,
                path=f"{rule_path}.to",
                target_desc="Prop-Typ",
                issues=issues,
            )

    return issues
