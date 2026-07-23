from __future__ import annotations

from speccify_core import SchemaValidator


def _minimal() -> dict:
    return {
        "schema_version": 1,
        "id": "spec://x",
        "version": "1.0.0",
        "kind": "ui-component",
        "title": "X",
        "summary": "y",
    }


def test_minimal_spec_is_valid() -> None:
    v = SchemaValidator()
    assert v.is_valid(_minimal())


def test_missing_required_field_reports_id() -> None:
    v = SchemaValidator()
    spec = _minimal()
    del spec["id"]
    issues = v.iter_issues(spec)
    assert issues
    assert any("'id'" in i.message for i in issues)


def test_invalid_id_pattern_fails() -> None:
    v = SchemaValidator()
    spec = _minimal()
    spec["id"] = "Not_A_Valid_ID"
    assert not v.is_valid(spec)


def test_invalid_semver_fails() -> None:
    v = SchemaValidator()
    spec = _minimal()
    spec["version"] = "1.0"
    issues = v.iter_issues(spec)
    assert any(i.path == "$.version" for i in issues)


def test_uses_pattern_accepts_range_suffix() -> None:
    v = SchemaValidator()
    spec = _minimal()
    spec["uses"] = ["spec://otp-input@^1.0", "@org/widget@~2.3"]
    assert v.is_valid(spec)
