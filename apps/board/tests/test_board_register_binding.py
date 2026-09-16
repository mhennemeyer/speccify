import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from speccify_board.app import create_app
from speccify_board.config import ConfigError, RepoConfig, parse_config
from speccify_board.sources import Source, SourceError
from test_board_service import SPEC_A, SPEC_B, make_register


def put(root: Path, text: str = SPEC_A) -> Path:
    file = root / ".agent/specs/001-shared/SPEC.md"
    file.parent.mkdir(parents=True)
    file.write_text(text)
    return file


def test_root_and_child_exact_write_target_and_stale_revision(tmp_path):
    root = tmp_path / "workspace"
    a, b, c = put(root), put(root / "api", SPEC_B), put(root / "web")
    config = parse_config(f"repos:\n- name: team\n  path: {root}\n")
    with TestClient(create_app(config, tmp_path / "data", background=False)) as client:
        rows = client.get("/api/board.json").json()["specs"]
        assert {row["repo"] for row in rows} == {"team", "team/api", "team/web"}
        api = next(row for row in rows if row["repo"] == "team/api")
        payload = {"station": "Done", "expected_revision": api["revision"]}
        assert (
            client.post("/api/r/team/api/specs/001-shared/station", json=payload).status_code == 200
        )
        assert a.read_text() == SPEC_A and c.read_text() == SPEC_A
        assert "station: Done" in b.read_text()
        before = b.read_bytes()
        assert (
            client.post("/api/r/team/api/specs/001-shared/station", json=payload).status_code == 409
        )
        assert b.read_bytes() == before
        assert (
            client.post("/api/r/team/unknown/specs/001-shared/station", json=payload).status_code
            == 409
        )
    # Even an empty root register must not hide children.
    a.unlink()
    source = Source(config.repos[0], tmp_path / "data", "User", "user@example.invalid")
    assert len(source.refresh().specs) == 2
    with pytest.raises(SourceError, match="Mehrdeutige"):
        source.move_station("001-shared", "Done")
    with pytest.raises(SourceError, match="Ungültige"):
        source.move_station("../outside", "Done")


def test_same_manifest_two_machines_and_remote_register(tmp_path):
    manifest = {
        "version": 1,
        "id": "team",
        "name": "Shared team",
        "sources": [{"id": "alpha", "name": "Alpha"}, {"id": "beta", "name": "Beta"}],
        "repositories": [{"id": "code", "name": "Code"}],
        "default_source": "alpha",
    }
    (tmp_path / "workspace-registers.json").write_text(json.dumps(manifest))
    remote = make_register(tmp_path / "remotes", "beta", {"001-shared": SPEC_B})
    snapshots = []
    for machine in ("one", "two"):
        checkout = tmp_path / machine / "different-local-name"
        put(checkout)
        config = parse_config(
            "manifest: workspace-registers.json\nbindings:\n"
            f"  alpha:\n    path: {checkout}\n  beta:\n    url: {remote}\n",
            base_dir=tmp_path,
        )
        with TestClient(
            create_app(config, tmp_path / f"data-{machine}", background=False)
        ) as client:
            rows = client.get("/api/board.json").json()["specs"]
            snapshots.append({(row["repo"], row["id"], row["revision"]) for row in rows})
            assert len(rows) == 2
            assert "data-revision=" in client.get("/").text
    assert snapshots[0] == snapshots[1]
    with pytest.raises(ConfigError, match="genau"):
        parse_config("manifest: workspace-registers.json\nbindings: {}", base_dir=tmp_path)


def test_refresh_preserves_uncommitted_register_and_other_sources(tmp_path):
    remote = make_register(tmp_path / "remotes", "app", {"001-shared": SPEC_A})
    source = Source(
        RepoConfig("app", url=str(remote)), tmp_path / "data", "User", "user@example.invalid"
    )
    assert not source.refresh().error
    file = source.clone_dir / "001-shared/SPEC.md"
    draft = SPEC_A + "\nUnsent work\n"
    file.write_text(draft)
    assert "Ungesicherte" in source.refresh().error
    assert file.read_text() == draft
    with pytest.raises(SourceError, match="Ungesicherte"):
        source.move_station("001-shared", "Done")
    assert file.read_text() == draft


def test_linked_spec_is_not_a_write_target(tmp_path):
    outside = put(tmp_path / "outside")
    base = tmp_path / "project/.agent/specs"
    base.mkdir(parents=True)
    (base / "001-shared").symlink_to(outside.parent, target_is_directory=True)
    source = Source(
        RepoConfig("local", path=tmp_path / "project"),
        tmp_path / "data",
        "User",
        "user@example.invalid",
    )
    assert source.refresh().specs == []
    with pytest.raises(SourceError):
        source.move_station("001-shared", "Done")
    assert outside.read_text() == SPEC_A
