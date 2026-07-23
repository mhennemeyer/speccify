"""Tests für den `composition:`-Block + Verdrahtungs-Typprüfung (Phase P2)."""

from __future__ import annotations

import copy
from pathlib import Path

from speccify_core import (
    ComponentApi,
    LocalRegistry,
    Version,
    component_api,
    parse_composition,
    validate_composition,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "registry-fixtures"


def _parsed(spec_id: str, version: str = "0.1.0") -> dict:
    registry = LocalRegistry(FIXTURES)
    return registry.fetch(spec_id, Version.parse(version)).parsed()


def _search_bar_children() -> dict[str, ComponentApi]:
    return {
        "query_input": component_api(_parsed("@org/text-input")),
        "go_button": component_api(_parsed("@org/button")),
    }


def test_parse_composition_none_for_leaf_specs() -> None:
    assert parse_composition(_parsed("@org/button")) is None


def test_parse_composition_search_bar_structure() -> None:
    composition = parse_composition(_parsed("@org/search-bar"))
    assert composition is not None
    assert set(composition.uses) == {"query_input", "go_button"}
    assert [node.alias for node in composition.tree] == ["query_input", "go_button"]
    assert len(composition.wiring) == 3
    set_rule = composition.wiring[0]
    assert set_rule.when == ("query_input", "changed")
    assert set_rule.set_ == ("query_input", "value")
    assert set_rule.to == "payload.value"
    emit_rule = composition.wiring[2]
    assert emit_rule.emit == "submitted"
    assert emit_rule.with_ == {"query": "props.query_input.value"}


def test_search_bar_validates_clean() -> None:
    issues = validate_composition(_parsed("@org/search-bar"), _search_bar_children())
    assert issues == []


def test_unknown_tree_node_is_reported() -> None:
    parsed = copy.deepcopy(_parsed("@org/search-bar"))
    parsed["composition"]["tree"].append({"node": "ghost"})
    issues = validate_composition(parsed, _search_bar_children())
    assert any("ghost" in i.message and "uses" in i.message for i in issues)


def test_wrong_tree_prop_type_is_reported() -> None:
    parsed = copy.deepcopy(_parsed("@org/search-bar"))
    parsed["composition"]["tree"][1]["props"]["disabled"] = "yes"
    issues = validate_composition(parsed, _search_bar_children())
    assert any("disabled" in i.path and "boolean" in i.message for i in issues)


def test_unknown_trigger_event_is_reported() -> None:
    parsed = copy.deepcopy(_parsed("@org/search-bar"))
    parsed["composition"]["wiring"][1]["when"] = "query_input.exploded"
    issues = validate_composition(parsed, _search_bar_children())
    assert any("exploded" in i.message for i in issues)


def test_missing_emit_payload_field_is_reported() -> None:
    parsed = copy.deepcopy(_parsed("@org/search-bar"))
    del parsed["composition"]["wiring"][1]["with"]["query"]
    issues = validate_composition(parsed, _search_bar_children())
    assert any("query" in i.message and "fehlt" in i.message for i in issues)


def test_payload_source_type_mismatch_is_reported() -> None:
    parsed = copy.deepcopy(_parsed("@org/search-bar"))
    # Boolean-Literal → query (string) ist inkompatibel.
    parsed["composition"]["wiring"][2]["with"]["query"] = True
    issues = validate_composition(parsed, _search_bar_children())
    assert any("True" in i.message and "passt nicht" in i.message for i in issues)


def test_enum_member_literal_is_assignable() -> None:
    issues = validate_composition(_parsed("@org/search-bar"), _search_bar_children())
    # tree[1].props.variant = "primary" (String-Literal in enum) muss sauber sein.
    assert not any("variant" in i.path for i in issues)


def test_map_to_unknown_prop_is_reported() -> None:
    parsed = copy.deepcopy(_parsed("@org/search-bar"))
    parsed["api"]["props"][0]["map_to"] = "query_input.nope"
    issues = validate_composition(parsed, _search_bar_children())
    assert any("map_to" in i.path and "nope" in i.message for i in issues)


def test_set_target_prop_type_mismatch_is_reported() -> None:
    parsed = copy.deepcopy(_parsed("@org/search-bar"))
    parsed["composition"]["wiring"][0]["set"] = "query_input.disabled"
    issues = validate_composition(parsed, _search_bar_children())
    assert any(".to" in i.path and "boolean" in i.message for i in issues)
