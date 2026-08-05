"""Web-Pfad mit Git-Quellen (Phase P5 Stufe 4).

Beweist, dass Validierung und Mock-Rendering ein Kompositions-Kind aus einem
Git-Repo auflösen — dieselbe Registry-Fassade wie im CLI-Pfad, kein Sonderfall.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from speccify_web_backend.app import create_app
from speccify_web_backend.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git nicht im PATH")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        env={
            "PATH": os.environ.get("PATH", ""),
            "GIT_AUTHOR_NAME": "Speccify Test",
            "GIT_AUTHOR_EMAIL": "test@speccify.io",
            "GIT_COMMITTER_NAME": "Speccify Test",
            "GIT_COMMITTER_EMAIL": "test@speccify.io",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )


@pytest.fixture
def button_repo(tmp_path: Path) -> str:
    source = REPO_ROOT / "registry-fixtures" / "org" / "button" / "0.1.0" / "spec.speccify.yaml"
    repo = tmp_path / "button-repo"
    repo.mkdir()
    _git(repo, "init", "--quiet", "--initial-branch", "main")
    (repo / "spec.speccify.yaml").write_bytes(source.read_bytes())
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "button 0.1.0")
    _git(repo, "tag", "v0.1.0")
    return f"git+file://{repo}"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        project_root=REPO_ROOT,
        registry_path=REPO_ROOT / "registry-fixtures",
        cache_dir=REPO_ROOT / "tests" / "fixtures" / "llm-cache",
        git_cache_dir=tmp_path / "git-cache",
    )
    return TestClient(create_app(settings))


def _draft(button_repo: str) -> str:
    return (
        "schema_version: 1\n"
        "id: '@org/git-widget'\n"
        "version: 0.1.0\n"
        "kind: ui-component\n"
        "title: Git Widget\n"
        "summary: Kind kommt aus einem Git-Repo.\n"
        "api:\n"
        "  props: []\n"
        "composition:\n"
        "  uses:\n"
        f"    btn: '{button_repo}@^0.1'\n"
        "  tree:\n"
        "    - node: btn\n"
        "      props:\n"
        "        label: Los\n"
    )


def test_validate_resolves_a_git_child(client: TestClient, button_repo: str) -> None:
    response = client.post("/api/v1/validate", json={"spec_yaml": _draft(button_repo)})
    assert response.status_code == 200, response.text
    assert response.json() == {"ok": True, "issues": []}


def test_draft_mock_renders_a_git_child(client: TestClient, button_repo: str) -> None:
    response = client.post("/api/v1/mock/draft", json={"spec_yaml": _draft(button_repo)})
    assert response.status_code == 200, response.text
    files = response.json()["files"]
    # Der Mock heißt nach der deklarierten Id des Kindes, nicht nach der Quelle.
    assert sorted(files) == ["org/Button.mock.tsx", "org/GitWidget.mock.tsx"]
    assert 'import Button from "./Button.mock"' in files["org/GitWidget.mock.tsx"]


def test_unknown_git_child_is_reported_as_issue(client: TestClient, tmp_path: Path) -> None:
    draft = _draft(f"git+file://{tmp_path / 'gibtsnicht'}")
    body = client.post("/api/v1/validate", json={"spec_yaml": draft}).json()
    assert body["ok"] is False
    assert any(issue["source"] == "composition" for issue in body["issues"])


def test_spec_detail_by_source_carries_id_and_source(client: TestClient, button_repo: str) -> None:
    """Detail über die Quelle: `id` ist der deklarierte Name, `source` der Git-Ref."""
    response = client.get("/api/v1/spec", params={"source": button_repo})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == "@org/button"
    assert body["source"] == button_repo
    assert body["version"] == "0.1.0"
    assert [prop["name"] for prop in body["api"]["props"]][:1] == ["label"]


def test_spec_detail_by_source_404_for_unknown_repo(client: TestClient, tmp_path: Path) -> None:
    response = client.get("/api/v1/spec", params={"source": f"git+file://{tmp_path / 'weg'}"})
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "not_found"
