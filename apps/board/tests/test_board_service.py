"""The Web-Board over real Git: two register clones, a local folder, writes
that land on the register branch, catch-up after a rejected push, per-repo
errors and basic auth (Spec 032)."""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from speccify_board.app import create_app
from speccify_board.config import ConfigError, parse_config
from speccify_board.sources import _replace_station, _toggle_task


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    assert result.returncode == 0, f"git {' '.join(args)}: {result.stderr}"
    return result.stdout.strip()


def make_register(base: Path, name: str, specs: dict[str, str]) -> Path:
    """A bare remote whose `specs` branch holds `<slug>/SPEC.md` files."""
    bare = base / f"{name}.git"
    bare.mkdir(parents=True)
    git(bare, "init", "-q", "--bare", "-b", "specs")
    work = base / f"{name}-seed"
    work.mkdir()
    git(work, "init", "-q", "-b", "specs")
    git(work, "config", "user.name", "seed")
    git(work, "config", "user.email", "seed@example.invalid")
    (work / ".gitattributes").write_text("*.jsonl merge=union\n", encoding="utf-8")
    for slug, text in specs.items():
        (work / slug).mkdir()
        (work / slug / "SPEC.md").write_text(text, encoding="utf-8")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "seed")
    git(work, "remote", "add", "origin", str(bare))
    git(work, "push", "-q", "-u", "origin", "specs")
    return bare


SPEC_A = (
    "---\nstation: Doing\norder: 1\nowner: Anna <anna@example.invalid>\n---\n"
    "# App-Login\n\n- [x] eins\n- [ ] zwei\n"
)
SPEC_B = "---\nstation: Backlog\norder: 2\n---\n# Portal-Suche\n\n- [ ] suchen\n"


@pytest.fixture
def team(tmp_path: Path) -> dict[str, Path]:
    app_bare = make_register(tmp_path / "remotes", "app", {"001-login": SPEC_A})
    portal_bare = make_register(tmp_path / "remotes", "portal", {"002-suche": SPEC_B})
    local = tmp_path / "local-project" / ".agent" / "specs" / "003-lokal"
    local.mkdir(parents=True)
    (local / "SPEC.md").write_text(
        "---\nstation: Done\n---\n# Lokal\n\n- [x] fertig\n", encoding="utf-8"
    )
    return {"app": app_bare, "portal": portal_bare, "local": tmp_path / "local-project"}


def config_for(team: dict[str, Path], extra: str = "") -> str:
    return f"""
title: Team Alpha
refresh_seconds: 5
author: Web-Board <board@example.invalid>
repos:
  - name: app
    url: {team["app"]}
  - name: portal
    url: {team["portal"]}
  - name: lokal
    path: {team["local"]}
{extra}
"""


def client_for(tmp_path: Path, config_text: str, password: str | None = None) -> TestClient:
    config = parse_config(config_text, base_dir=tmp_path)
    app = create_app(config, tmp_path / "data", password=password, background=False)
    return TestClient(app)


def test_config_parsing_and_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_TOKEN", "s3cret")
    config = parse_config(
        "title: X\nrefresh_seconds: 1\nrepos:\n  - name: a\n"
        "    url: https://x:${GIT_TOKEN}@host/a.git\n  - name: b\n    path: ./proj\n",
        base_dir=tmp_path,
    )
    assert config.refresh_seconds == 5, "Untergrenze"
    assert config.repos[0].url == "https://x:s3cret@host/a.git"
    assert config.repos[1].path == (tmp_path / "proj").resolve()
    assert config.author_name == "Speccify Board"
    for bad in (
        "repos:\n  - url: x\n",
        "repos:\n  - name: a\n",
        "repos:\n  - name: a\n    url: x\n    path: y\n",
        "repos:\n  - name: a\n    url: x\n  - name: a\n    url: y\n",
        "repos:\n  - name: 'a b'\n    url: x\n",
    ):
        with pytest.raises(ConfigError):
            parse_config(bad)


def test_edit_helpers_keep_bytes_stable() -> None:
    text = (
        "---\r\nstation: Backlog\r\norder: 1\r\n---\r\n# T\r\n\r\n"
        "- [ ] a\r\n```\r\n- [ ] no\r\n```\r\n- [x] b\r\n"
    )
    moved, old = _replace_station(text, "Doing")
    assert old == "Backlog" and moved == text.replace("station: Backlog", "station: Doing")
    toggled, label = _toggle_task(text, 1, False)
    assert label == "b" and toggled == text.replace("- [x] b", "- [ ] b")
    toggled, label = _toggle_task(text, 0, True)
    assert label == "a" and toggled == text.replace("- [ ] a", "- [x] a")


def test_board_reads_clones_and_local_folder(tmp_path: Path, team: dict[str, Path]) -> None:
    with client_for(tmp_path, config_for(team)) as client:
        page = client.get("/").text
        assert "Team Alpha · Team-Board" in page
        assert "App-Login" in page and "Portal-Suche" in page and "Lokal" in page
        assert 'id="repo"' in page and 'class="badge repo">portal' in page
        assert 'class="edit"' in page
        one = client.get("/r/portal/").text
        assert "Portal-Suche" in one and "App-Login" not in one
        assert client.get("/r/nope/").status_code == 404
        data = client.get("/api/board.json").json()
        assert data["summary"]["repos"]["app"] == {
            "specs": 1,
            "doing": 1,
            "tasks_done": 1,
            "tasks_total": 2,
        }
        assert {r["name"]: r["kind"] for r in data["repos"]} == {
            "app": "git",
            "portal": "git",
            "lokal": "path",
        }
        assert all(r["error"] is None for r in data["repos"])
        assert client.get("/healthz").json()["ok"] is True


def test_refresh_picks_up_remote_commits(tmp_path: Path, team: dict[str, Path]) -> None:
    with client_for(tmp_path, config_for(team)) as client:
        assert "Zweite Spec" not in client.get("/").text
        clone = tmp_path / "colleague"
        git(tmp_path, "clone", "-q", "--branch", "specs", str(team["app"]), "colleague")
        git(clone, "config", "user.name", "ben")
        git(clone, "config", "user.email", "ben@example.invalid")
        (clone / "004-zweite").mkdir()
        (clone / "004-zweite" / "SPEC.md").write_text(
            "---\nstation: Backlog\n---\n# Zweite Spec\n", encoding="utf-8"
        )
        git(clone, "add", "-A")
        git(clone, "commit", "-q", "-m", "spec(004-zweite): neu")
        git(clone, "push", "-q", "origin", "specs")
        assert "Zweite Spec" not in client.get("/").text, "noch nicht aufgefrischt"
        status = client.post("/api/refresh").json()["repos"]
        assert next(r for r in status if r["name"] == "app")["commit"] == git(
            clone, "rev-parse", "--short", "HEAD"
        )
        assert "Zweite Spec" in client.get("/").text


def test_writes_land_on_the_register_and_catch_up_after_rejection(
    tmp_path: Path, team: dict[str, Path]
) -> None:
    with client_for(tmp_path, config_for(team)) as client:
        response = client.post("/api/r/app/specs/001-login/station", json={"station": "Done"})
        assert response.status_code == 200, response.text
        check = tmp_path / "check"
        git(tmp_path, "clone", "-q", "--branch", "specs", str(team["app"]), "check")
        text = (check / "001-login" / "SPEC.md").read_text(encoding="utf-8")
        assert text.startswith(
            "---\nstation: Done\norder: 1\nowner: Anna <anna@example.invalid>\n---\n"
        ), text
        history = (check / "001-login" / "history.jsonl").read_text(encoding="utf-8")
        assert '"actor": "board"' in history and "Doing -> Done" in history
        assert git(check, "log", "-1", "--format=%an <%ae>") == "Web-Board <board@example.invalid>"
        assert (
            git(check, "log", "-1", "--format=%s") == "spec(001-login): Doing -> Done (Web-Board)"
        )
        assert "<option selected>Done</option>" in client.get("/r/app/").text

        # A colleague pushes in between: the board's next push is rejected, catches up, retries.
        git(check, "config", "user.name", "ben")
        git(check, "config", "user.email", "ben@example.invalid")
        (check / "005-neu").mkdir()
        (check / "005-neu" / "SPEC.md").write_text(
            "---\nstation: Backlog\n---\n# Neu\n", encoding="utf-8"
        )
        git(check, "add", "-A")
        git(check, "commit", "-q", "-m", "spec(005-neu): neu")
        git(check, "push", "-q", "origin", "specs")
        response = client.post("/api/r/app/specs/001-login/tasks/1", json={"done": True})
        assert response.status_code == 200, response.text
        git(check, "pull", "-q", "--rebase", "origin", "specs")
        assert "- [x] zwei" in (check / "001-login" / "SPEC.md").read_text(encoding="utf-8")
        assert (check / "005-neu" / "SPEC.md").is_file(), "fremder Commit erhalten"
        assert (
            git(check, "log", "--format=%s", "-3")
            .splitlines()[0]
            .startswith("spec(001-login): Task 2 erledigt")
        )

        # Local folders are written in place; unknown specs and stations are errors.
        response = client.post("/api/r/lokal/specs/003-lokal/tasks/0", json={"done": False})
        assert response.status_code == 200
        assert "- [ ] fertig" in (
            team["local"] / ".agent" / "specs" / "003-lokal" / "SPEC.md"
        ).read_text(encoding="utf-8")
        assert (
            client.post("/api/r/app/specs/999-x/station", json={"station": "Doing"}).status_code
            == 409
        )
        assert (
            client.post("/api/r/app/specs/001-login/station", json={"station": "Later"}).status_code
            == 409
        )
        assert (
            client.post(
                "/api/r/nope/specs/001-login/station", json={"station": "Doing"}
            ).status_code
            == 404
        )


def test_broken_repo_is_reported_and_others_keep_working(
    tmp_path: Path, team: dict[str, Path]
) -> None:
    extra = f"  - name: kaputt\n    url: {tmp_path / 'remotes' / 'missing.git'}\n"
    with client_for(tmp_path, config_for(team, extra)) as client:
        page = client.get("/").text
        assert "App-Login" in page and "kaputt:" in page
        health = client.get("/healthz").json()
        assert health["ok"] is False
        assert next(r for r in health["repos"] if r["name"] == "kaputt")["error"]


def test_workspace_folder_binds_every_project(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    for child in ("alpha", "beta"):
        folder = workspace / child / ".agent" / "specs" / f"001-{child}"
        folder.mkdir(parents=True)
        (folder / "SPEC.md").write_text(
            f"---\nstation: Doing\n---\n# {child.title()}\n\n- [ ] x\n", encoding="utf-8"
        )
    (workspace / "notes").mkdir()
    with client_for(tmp_path, f"repos:\n  - name: ws\n    path: {workspace}\n") as client:
        page = client.get("/").text
        assert "Alpha" in page and "Beta" in page
        assert 'class="badge repo">ws/alpha' in page
        response = client.post("/api/r/ws/alpha/specs/001-alpha/tasks/0", json={"done": True})
        assert response.status_code == 200, response.text
        assert "- [x] x" in (
            workspace / "alpha" / ".agent" / "specs" / "001-alpha" / "SPEC.md"
        ).read_text(encoding="utf-8")


def test_basic_auth_guards_pages_and_api(tmp_path: Path, team: dict[str, Path]) -> None:
    with client_for(tmp_path, config_for(team), password="geheim") as client:
        assert client.get("/").status_code == 401
        assert client.get("/api/board.json").status_code == 401
        assert client.get("/healthz").status_code == 200, "Health bleibt offen"
        token = base64.b64encode(b"board:geheim").decode()
        assert client.get("/", headers={"Authorization": f"Basic {token}"}).status_code == 200
        wrong = base64.b64encode(b"board:falsch").decode()
        assert client.get("/", headers={"Authorization": f"Basic {wrong}"}).status_code == 401
