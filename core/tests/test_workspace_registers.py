import json

import pytest
from speccify_core.workspace_registers import ManifestError, parse_manifest


def manifest() -> dict:
    return {
        "version": 1,
        "id": "team",
        "name": "Team",
        "sources": [{"id": "root", "name": "Root"}, {"id": "api", "name": "API"}],
        "repositories": [{"id": "api-code", "name": "API"}],
        "default_source": "root",
    }


def test_portable_contract():
    value = parse_manifest(json.dumps(manifest()))
    assert value.default_source == "root"
    assert [source.id for source in value.sources] == ["root", "api"]
    for patch in (
        {"version": True},
        {"version": 2},
        {"path": "/private/local"},
        {"default_source": []},
        {"default_source": "missing"},
        {"sources": [{"id": "x", "name": "A"}, {"id": "x", "name": "B"}]},
        {"sources": [{"id": "../outside", "name": "Bad"}]},
    ):
        with pytest.raises(ManifestError):
            parse_manifest(json.dumps(manifest() | patch))
