"""Unit tests for ``speccify_cli._credentials``."""

from __future__ import annotations

import os
import stat

import pytest
from speccify_cli import _credentials


@pytest.fixture(autouse=True)
def _isolated_config_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SPECCIFY_CONFIG_HOME", str(tmp_path / "speccify"))
    yield tmp_path


def test_normalize_registry_url_drops_path_and_trailing_slash() -> None:
    assert (
        _credentials.normalize_registry_url("http://localhost:8001/api/") == "http://localhost:8001"
    )
    assert (
        _credentials.normalize_registry_url("https://registry.example.com")
        == "https://registry.example.com"
    )


def test_save_creates_file_with_0600_and_round_trips() -> None:
    cred = _credentials.Credential(
        registry="http://localhost:8001",
        token="speccify_abcdef",
        username="marc",
    )
    path = _credentials.save(cred)

    assert path.exists()
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600

    loaded = _credentials.get("http://localhost:8001/")
    assert loaded is not None
    assert loaded.token == "speccify_abcdef"
    assert loaded.username == "marc"


def test_save_preserves_other_hosts() -> None:
    _credentials.save(_credentials.Credential(registry="http://a", token="speccify_aaa"))
    _credentials.save(_credentials.Credential(registry="http://b", token="speccify_bbb"))

    all_creds = _credentials.load_all()
    assert set(all_creds) == {"http://a", "http://b"}
    assert all_creds["http://a"].token == "speccify_aaa"
    assert all_creds["http://b"].token == "speccify_bbb"


def test_check_permissions_raises_on_world_readable(tmp_path) -> None:
    path = _credentials.save(_credentials.Credential(registry="http://x", token="speccify_x"))
    os.chmod(path, 0o644)
    with pytest.raises(PermissionError):
        _credentials.check_permissions(path)


def test_get_returns_none_when_no_match() -> None:
    _credentials.save(_credentials.Credential(registry="http://a", token="speccify_aaa"))
    assert _credentials.get("http://nope") is None
