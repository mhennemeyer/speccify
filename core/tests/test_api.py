"""Tests für den formalen API-Vertrag (`speccify_core.api`, Spec-Schema v1)."""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core import LocalRegistry, TypeRef, Version, component_api, types_compatible

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "registry-fixtures"


def _parsed(spec_id: str, version: str = "0.1.0") -> dict:
    registry = LocalRegistry(FIXTURES)
    return registry.fetch(spec_id, Version.parse(version)).parsed()


def test_button_api_props_events_slots() -> None:
    api = component_api(_parsed("@org/button"))
    label = api.prop("label")
    assert label is not None
    assert label.required is True
    assert label.type.kind == "string"
    variant = api.prop("variant")
    assert variant is not None
    assert variant.type.kind == "enum"
    assert variant.type.enum_values == ("primary", "secondary", "ghost")
    assert variant.has_default and variant.default == "primary"
    assert [e.name for e in api.events] == ["pressed", "long_pressed"]
    slot = api.slot("icon_leading")
    assert slot is not None and slot.optional is True


def test_event_payload_types_are_parsed() -> None:
    api = component_api(_parsed("@org/text-input"))
    changed = api.event("changed")
    assert changed is not None
    assert changed.payload_field("value") == TypeRef(raw="string", kind="string")
    assert changed.payload_field("nope") is None


def test_logic_fixtures_are_parsed() -> None:
    api = component_api(_parsed("@org/http-api-client"))
    names = [f.name for f in api.fixtures]
    assert names == ["get_ok", "server_error"]
    get_ok = api.fixtures[0]
    assert get_ok.data["status"] == 200


def test_map_to_is_parsed_as_alias_prop_pair() -> None:
    api = component_api(_parsed("@org/search-bar"))
    placeholder = api.prop("placeholder")
    assert placeholder is not None
    assert placeholder.map_to == ("query_input", "placeholder")


@pytest.mark.parametrize(
    ("source", "target", "expected"),
    [
        ("string", "string", True),
        ("integer", "number", True),
        ("number", "integer", False),
        ("enum[a, b]", "enum[a, b, c]", True),
        ("enum[a, d]", "enum[a, b, c]", False),
        ("object{x: string}", "object{x: string}", True),
        ("object{x: string}", "object{y: string}", False),
    ],
)
def test_types_compatible(source: str, target: str, expected: bool) -> None:
    assert types_compatible(TypeRef.parse(source), TypeRef.parse(target)) is expected
