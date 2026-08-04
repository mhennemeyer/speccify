"""Tests für den `app:`-Block und die `navigate`-Verdrahtung (Phase P4, Stufe 1)."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from speccify_core import SchemaValidator, parse_app, parse_composition, validate_app


def _app_spec() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": "@org/demo-app",
        "version": "0.1.0",
        "kind": "app",
        "title": "Demo",
        "summary": "Zwei Screens, eine Navigation.",
        "app": {
            "routes": [
                {"path": "/", "node": "search", "title": "Suche"},
                {"path": "/kontakt", "node": "contact"},
            ],
            "theme": {"tokens": {"color_primary": "#0f766e"}},
            "env": [{"name": "api_base_url", "default": "http://localhost:8000"}],
        },
        "composition": {
            "uses": {
                "search": "@org/search-bar@^0.1",
                "contact": "@org/contact-form@^0.1",
            },
            "tree": [{"node": "search"}, {"node": "contact"}],
            "wiring": [{"when": "search.searched", "navigate": "/kontakt"}],
        },
    }


def test_parse_app_reads_routes_theme_and_env() -> None:
    app = parse_app(_app_spec())
    assert app is not None
    assert [route.path for route in app.routes] == ["/", "/kontakt"]
    assert app.start_route.node == "search"
    assert app.route_for("/kontakt") is not None
    assert app.route_for("/nope") is None
    assert app.theme_tokens == {"color_primary": "#0f766e"}
    assert app.env[0].name == "api_base_url"
    assert app.env[0].default == "http://localhost:8000"


def test_parse_app_none_for_component_specs() -> None:
    assert parse_app({"kind": "ui-component"}) is None


def test_parse_composition_reads_navigate() -> None:
    composition = parse_composition(_app_spec())
    assert composition is not None
    assert composition.wiring[0].navigate == "/kontakt"
    assert composition.wiring[0].set_ is None


def test_validate_app_accepts_the_reference_shape() -> None:
    assert validate_app(_app_spec()) == []


def test_validate_app_rejects_route_to_unknown_node() -> None:
    spec = copy.deepcopy(_app_spec())
    spec["app"]["routes"][1]["node"] = "ghost"
    issues = validate_app(spec)
    assert len(issues) == 1
    assert issues[0].path == "$.app.routes[1]"
    assert "kein Top-Level-Knoten" in issues[0].message


def test_validate_app_rejects_route_to_slot_child() -> None:
    """Screens sind Top-Level — ein Knoten in einem Slot ist keine Route."""
    spec = copy.deepcopy(_app_spec())
    spec["composition"]["tree"] = [{"node": "search", "slots": {"footer": [{"node": "contact"}]}}]
    issues = validate_app(spec)
    assert [issue.path for issue in issues] == ["$.app.routes[1]"]


def test_validate_app_rejects_duplicate_paths_and_env_names() -> None:
    spec = copy.deepcopy(_app_spec())
    spec["app"]["routes"][1]["path"] = "/"
    spec["app"]["env"].append({"name": "api_base_url"})
    messages = [issue.message for issue in validate_app(spec)]
    assert any("doppelt" in message and "/" in message for message in messages)
    assert any("Env-Name" in message for message in messages)


def test_validate_app_rejects_navigate_to_unknown_route() -> None:
    spec = copy.deepcopy(_app_spec())
    spec["composition"]["wiring"][0]["navigate"] = "/gibtsnicht"
    issues = validate_app(spec)
    assert [issue.path for issue in issues] == ["$.composition.wiring[0].navigate"]
    assert "nicht deklariert" in issues[0].message


def test_validate_app_rejects_navigate_outside_apps() -> None:
    spec = copy.deepcopy(_app_spec())
    spec["kind"] = "ui-component"
    del spec["app"]
    issues = validate_app(spec)
    assert [issue.path for issue in issues] == ["$.composition.wiring[0].navigate"]
    assert "nur in `kind: app`" in issues[0].message


def test_validate_app_rejects_app_block_on_component_kinds() -> None:
    spec = copy.deepcopy(_app_spec())
    spec["kind"] = "screen"
    messages = [issue.message for issue in validate_app(spec)]
    assert any("nur für `kind: app`" in message for message in messages)


def test_validate_app_requires_app_block_for_app_kind() -> None:
    spec = copy.deepcopy(_app_spec())
    del spec["app"]
    spec["composition"]["wiring"] = []
    messages = [issue.message for issue in validate_app(spec)]
    assert messages == ["`kind: app` braucht einen `app:`-Block mit `routes`."]


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda spec: spec["app"].__setitem__("routes", []), id="leere-routen"),
        pytest.param(
            lambda spec: spec["app"]["routes"][0].__setitem__("path", "kontakt"),
            id="pfad-ohne-slash",
        ),
        pytest.param(
            lambda spec: spec["app"].__setitem__("layout", "grid"), id="unbekannter-schluessel"
        ),
        pytest.param(
            lambda spec: spec["composition"]["wiring"][0].__setitem__("navigate", "/A"),
            id="grossbuchstabe-im-pfad",
        ),
    ],
)
def test_schema_rejects_broken_app_blocks(mutate) -> None:
    spec = copy.deepcopy(_app_spec())
    mutate(spec)
    assert list(SchemaValidator().iter_issues(spec)) != []


def test_schema_accepts_the_reference_shape() -> None:
    assert list(SchemaValidator().iter_issues(_app_spec())) == []
