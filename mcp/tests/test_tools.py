"""Tests for the MCP tools — thin adapters, so the checks stay behavioural."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from speccify_mcp.tools import (
    run_lock,
    run_pull,
    run_skill_asset,
    run_skill_get,
    run_skill_list,
    run_verify,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN = "@speccify/macos-notarize-tauri"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project with its own copy of the skill library."""
    shutil.copytree(REPO_ROOT / "skills", tmp_path / "skills")
    (tmp_path / "speccify.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    return tmp_path


def test_skill_list_describes_the_library(project: Path) -> None:
    """Shallow on purpose: name, description, axes — not the bodies."""
    result = run_skill_list(project)
    assert result.ok, result.message
    entries = {entry["id"]: entry for entry in result.playbooks}
    assert MAIN in entries
    assert "tauri" in entries[MAIN]["stack"]
    assert "notarization" in entries[MAIN]["description"].lower()
    assert "body" not in entries[MAIN], "listing must not carry the instructions"


def test_skill_get_carries_the_body_and_its_sources(project: Path) -> None:
    """`get` is for a skill that is *not* installed — so it leads with the body."""
    result = run_skill_get(project, reference=MAIN)
    assert result.ok, result.message
    skill = result.playbook

    assert "hardened runtime" in skill["body"]
    assert [step["number"] for step in skill["steps"]] == [1, 2, 3, 4, 5]
    assert all(source["retrieved"] == "2026-08-06" for source in skill["sources"])
    assert skill["files"] == [
        "tools/verify-signatures/TOOL.md",
        "tools/verify-signatures/reference.sh",
    ]


def test_unknown_reference_is_structured(project: Path) -> None:
    result = run_skill_get(project, reference="@org/nope")
    assert not result.ok
    assert result.code == "not_found"


def test_lock_pull_verify_round_trip(project: Path) -> None:
    (project / "speccify.yaml").write_text(
        f"schema_version: 1\ndependencies:\n  '{MAIN}': ^1.0\n",
        encoding="utf-8",
    )
    locked = run_lock(project)
    assert locked.ok, locked.message
    assert len(locked.entries) == 2

    pulled = run_pull(project, out_dir=Path("out"))
    assert pulled.ok, pulled.message
    assert any("verify-signatures/reference.sh" in path for path in pulled.files)

    verified = run_verify(project)
    assert verified.ok, verified.problems


def test_expand_returns_the_to_do_list(project: Path) -> None:
    from speccify_mcp.tools import run_expand

    (project / "speccify.yaml").write_text(
        f"schema_version: 1\ndependencies:\n  '{MAIN}': ^1.0\n", encoding="utf-8"
    )
    assert run_lock(project).ok
    result = run_expand(project, platform="macos")
    assert result.ok, result.message
    names = {s["name"]: s for s in result.skills}
    assert names["apple-developer-id-cert"]["used_by"] == "macos-notarize-tauri"
    assert result.tools_to_implement == ["verify-signatures"]
    assert (project / ".agent" / "skills" / "macos-notarize-tauri" / "SKILL.md").is_file()


def test_verify_reports_drift_as_a_result(project: Path) -> None:
    (project / "speccify.yaml").write_text(
        f"schema_version: 1\ndependencies:\n  '{MAIN}': ^1.0\n",
        encoding="utf-8",
    )
    run_lock(project)
    playbook = project / "skills" / "macos-notarize-tauri" / "SKILL.md"
    playbook.write_text(playbook.read_text(encoding="utf-8") + "\n# touched\n", encoding="utf-8")
    verified = run_verify(project)
    assert not verified.ok
    assert any("bundle hash drift" in problem for problem in verified.problems)


def test_playbook_asset_returns_the_script(project: Path) -> None:
    from speccify_mcp.tools import run_skill_asset

    result = run_skill_asset(project, reference=MAIN, path="tools/verify-signatures/reference.sh")
    assert result.ok, result.message
    assert result.encoding == "utf-8"
    assert "codesign --verify" in result.content


def test_playbook_asset_lists_what_is_available(project: Path) -> None:
    from speccify_mcp.tools import run_skill_asset

    result = run_skill_asset(project, reference=MAIN, path="assets/nope")
    assert not result.ok
    assert "reference.sh" in result.message


def test_tool_get_returns_the_contract(project: Path) -> None:
    """An agent implements against this — schemas, effects, examples — not against a script."""
    from speccify_mcp.tools import run_tool_get

    whole = run_skill_get(project, reference=MAIN)
    assert [t["name"] for t in whole.playbook["tools"]] == ["verify-signatures"]
    assert "inputs" not in whole.playbook["tools"][0], "skill_get stays shallow"

    result = run_tool_get(project, reference=MAIN, tool="verify-signatures")
    assert result.ok, result.message
    tool = result.tool
    assert tool["inputs"]["required"] == ["bundle"]
    assert "codesign" in tool["requires"]
    assert tool["examples"][0]["output"]["ok"] is True
    assert tool["files"] == ["reference.sh"]

    missing = run_tool_get(project, reference=MAIN, tool="nope")
    assert not missing.ok and "verify-signatures" in missing.message


def test_playbook_check_reports_health(project: Path) -> None:
    from speccify_mcp.tools import run_skill_check

    result = run_skill_check(project, reference=MAIN)
    assert result.ok, result.findings
    assert result.findings == []


def test_an_agent_can_find_and_read_a_skill_over_mcp(project: Path) -> None:
    """The path that matters, pinned so it cannot drift.

    list -> pick by stack -> get (body included) -> follow the child it builds
    on -> read a bundled file. No step tool: an installed skill is read from
    disk, and every tool definition costs context in every session.
    """
    listed = run_skill_list(project)
    assert listed.ok
    chosen = next(entry for entry in listed.playbooks if "tauri" in entry["stack"])

    whole = run_skill_get(project, reference=chosen["id"])
    assert whole.ok
    assert whole.playbook["body"].strip(), "the body is what the agent follows"

    # It builds on another skill, and that one resolves too.
    (child,) = whole.playbook["uses"]
    resolved = run_skill_get(project, reference=child)
    assert resolved.ok, resolved.message

    asset = run_skill_asset(
        project, reference=chosen["id"], path="tools/verify-signatures/reference.sh"
    )
    assert asset.ok and "codesign" in (asset.content or "")


def test_tool_check_reports_per_example_as_a_result(project: Path) -> None:
    from speccify_mcp.tools import run_expand, run_tool_check

    (project / "speccify.yaml").write_text(
        f"schema_version: 1\ndependencies:\n  '{MAIN}': ^1.0\n", encoding="utf-8"
    )
    assert run_lock(project).ok
    assert run_expand(project, platform="macos").ok

    nothing = run_tool_check(project, platform="macos")
    assert nothing.ok
    assert nothing.tools[0]["status"] == "not-implemented"

    tool_dir = project / ".agent" / "tools" / "verify-signatures"
    (tool_dir / "TOOL.md").write_text(
        (tool_dir / "TOOL.md").read_text().replace("requires: codesign\n", "")
    )
    (tool_dir / "macos.py").write_text(
        'import json, sys\nprint(json.dumps({"ok": True, "checked": [], "offenders": []}))\n'
    )
    result = run_tool_check(project, names=["verify-signatures"], platform="macos")
    assert not result.ok
    tool = result.tools[0]
    assert tool["status"] == "failed"
    assert tool["cases"][0]["title"] == "every binary signed by the expected identity"
    assert "$.checked: expected 3 item(s), got 0" in tool["cases"][0]["detail"]

    missing = run_tool_check(project, names=["nope"])
    assert not missing.ok
    assert missing.code == "tool_check_failed"


# --- Quellen einbinden: source_list → add → expand (P1 des 4Notice-Plans) --------


def _git(repo: Path, *args: str) -> None:
    import os
    import subprocess

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
def skills_repo(tmp_path: Path) -> str:
    """Ein Skills-Repo wie `speccify-first-test`: Bundles unter skills/<name>/."""
    repo = tmp_path / "first-test"
    repo.mkdir()
    _git(repo, "init", "--quiet", "--initial-branch", "main")
    for name, version in (("notarize", "1.0.0"), ("cert", "1.0.0"), ("notarize", "1.0.1")):
        target = repo / "skills" / name
        target.mkdir(parents=True, exist_ok=True)
        (target / "SKILL.md").write_text(
            "---\n"
            f"name: {name}\n"
            f"description: {name} {version} — from a git source. Use when testing.\n"
            "metadata:\n"
            f'  speccify.version: "{version}"\n'
            "  speccify.scope: test\n"
            "---\n\n## 1 — Step\n\nDo it.\n",
            encoding="utf-8",
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "--quiet", "-m", f"{name} {version}")
        _git(repo, "tag", f"skills/{name}/v{version}")
    return f"git+file://{repo}"


def test_source_list_describes_a_repo(skills_repo: str, tmp_path: Path, monkeypatch) -> None:
    from speccify_mcp.tools import run_source_list

    monkeypatch.setenv("HOME", str(tmp_path))  # Git-Cache nicht im echten Home
    result = run_source_list(skills_repo)
    assert result.ok, result.message
    by_path = {s["path"]: s for s in result.skills}
    assert set(by_path) == {"skills/cert", "skills/notarize"}
    assert by_path["skills/notarize"]["latest"] == "1.0.1"
    assert by_path["skills/notarize"]["versions"] == ["1.0.0", "1.0.1"]
    assert by_path["skills/notarize"]["id"] == f"{skills_repo}#skills/notarize"
    assert by_path["skills/cert"]["name"] == "cert"


def test_source_list_rejects_non_git() -> None:
    from speccify_mcp.tools import run_source_list

    result = run_source_list("@speccify/whatever")
    assert not result.ok and result.code == "not_a_git_source"


def test_add_from_a_git_source_then_expand(skills_repo: str, tmp_path: Path, monkeypatch) -> None:
    from speccify_mcp.tools import run_add, run_expand

    monkeypatch.setenv("HOME", str(tmp_path))
    project = tmp_path / "project"
    project.mkdir()
    (project / "speccify.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    reference = f"{skills_repo}#skills/notarize"

    added = run_add(project, reference=reference)
    assert added.ok, added.message
    assert added.range == "^1.0"
    assert reference in (project / "speccify.yaml").read_text(encoding="utf-8")
    assert (project / "speccify.lock").is_file()

    expanded = run_expand(project, references=[reference], platform="macos")
    assert expanded.ok, expanded.message
    assert (project / ".agent" / "skills" / "notarize" / "SKILL.md").is_file()


def test_add_reports_unknown_reference(tmp_path: Path) -> None:
    from speccify_mcp.tools import run_add

    project = tmp_path / "project"
    project.mkdir()
    (project / "speccify.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    result = run_add(project, reference="@nobody/nothing")
    assert not result.ok and result.code == "add_failed"


# --- Multi-Modus: ungebundener Server verlangt `project` -------------------------


def test_unbound_server_requires_project(tmp_path: Path) -> None:
    import asyncio

    from speccify_mcp.server import ServerConfig, build_server

    server = build_server(ServerConfig(project_root=None))

    async def call(name: str, args: dict) -> dict:
        result = await server.call_tool(name, args)
        # FastMCP liefert (content, structured) oder nur content
        structured = result[1] if isinstance(result, tuple) else None
        if isinstance(structured, dict):
            return structured
        import json

        return json.loads(result[0][0].text)

    missing = asyncio.run(call("verify", {}))
    assert not missing["ok"] and missing["code"] == "project_required"

    bogus = asyncio.run(call("verify", {"project": "relative/path"}))
    assert bogus["code"] == "project_not_found"

    (tmp_path / "speccify.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    real = asyncio.run(call("skill_list", {"project": str(tmp_path)}))
    assert "code" in real and real.get("code") != "project_required"


# --- tool_run: ein Tool mit freier Eingabe (D7) ---------------------------------


def test_tool_run_feeds_stdin_and_returns_json(tmp_path: Path) -> None:
    from speccify_mcp.tools import run_tool_run

    tool_dir = tmp_path / ".agent" / "tools" / "echo-upper"
    tool_dir.mkdir(parents=True)
    (tool_dir / "TOOL.md").write_text(
        "---\nname: echo-upper\ndescription: Uppercases `text`.\n"
        "inputs: {type: object, properties: {text: {type: string}}}\n"
        "outputs: {type: object, properties: {ok: {type: boolean}, text: {type: string}}}\n"
        '---\n\n## Examples\n\n### a\ninput: {"text": "a"}\noutput: {"ok": true, "text": "A"}\n',
        encoding="utf-8",
    )
    (tool_dir / "macos.py").write_text(
        "import json,sys\nd=json.load(sys.stdin)\n"
        "print(json.dumps({'ok': True, 'text': d['text'].upper()}))\n",
        encoding="utf-8",
    )
    (tool_dir / "linux.py").write_text((tool_dir / "macos.py").read_text(), encoding="utf-8")

    result = run_tool_run(tmp_path, name="echo-upper", input_value={"text": "hi"})
    assert result.ok, result.message
    assert result.result["output"] == {"ok": True, "text": "HI"}
    assert result.result["exit_code"] == 0

    missing = run_tool_run(tmp_path, name="echo-upper", input_value={}, platform="windows")
    assert not missing.ok and missing.code == "run_failed"
    assert "windows" in missing.message

    unknown = run_tool_run(tmp_path, name="nope", input_value={})
    assert unknown.code == "not_found"
    assert run_tool_run(tmp_path, name="../x", input_value={}).code == "bad_name"
