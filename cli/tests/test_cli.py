"""End-to-end tests for the CLI: init, add, lock, verify, pull, show, lint."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from speccify_cli.__main__ import app
from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
LIBRARY = REPO_ROOT / "skills"
MAIN = "@speccify/macos-notarize-tauri"
CHILD = "@speccify/apple-developer-id-cert"

runner = CliRunner()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    result = runner.invoke(app, ["init", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output
    return tmp_path


def _add(project: Path, reference: str = MAIN):
    return runner.invoke(
        app, ["add", reference, "--project", str(project), "--library", str(LIBRARY)]
    )


def test_init_writes_a_minimal_manifest(project: Path) -> None:
    manifest = yaml.safe_load((project / "speccify.yaml").read_text(encoding="utf-8"))
    assert manifest == {"schema_version": 1}


def test_init_ignores_the_cache_and_links_the_agent(project: Path) -> None:
    assert ".agent/speccify/cache/" in (project / ".gitignore").read_text().splitlines()
    assert (project / ".claude" / "skills").is_symlink()
    assert (project / ".agent" / "skills").is_dir()


def test_link_replaces_gits_symlink_husk(project: Path) -> None:
    # Git ohne Symlink-Support (Windows-Default) checkt `.claude/skills` als
    # Textdatei mit dem Zielpfad aus — link muss sie erkennen und ersetzen.
    link = project / ".claude" / "skills"
    link.unlink()
    link.write_text("../.agent/skills", encoding="utf-8")
    result = runner.invoke(app, ["link", "--project", str(project)])
    assert result.exit_code == 0, result.output
    assert link.is_symlink() or link.is_dir()


def test_link_refuses_a_foreign_file(project: Path) -> None:
    link = project / ".claude" / "skills"
    link.unlink()
    link.write_text("hier stand mal was anderes", encoding="utf-8")
    result = runner.invoke(app, ["link", "--project", str(project)])
    assert result.exit_code == 1
    assert "is a file" in result.output


def test_add_pins_the_playbook_and_its_child(project: Path) -> None:
    result = _add(project)
    assert result.exit_code == 0, result.output
    lockfile = yaml.safe_load((project / "speccify.lock").read_text(encoding="utf-8"))
    assert lockfile["schema_version"] == 1
    ids = [entry["id"] for entry in lockfile["playbooks"]]
    # The child comes along because a step delegates to it.
    assert ids == [CHILD, MAIN]
    assert all(entry["bundle_sha256"].startswith("sha256:") for entry in lockfile["playbooks"])


def test_verify_is_green_after_add(project: Path) -> None:
    _add(project)
    result = runner.invoke(app, ["verify", "--project", str(project), "--library", str(LIBRARY)])
    assert result.exit_code == 0, result.output
    assert "agree" in result.output


def test_verify_reports_bundle_drift(project: Path, tmp_path: Path) -> None:
    """A changed bundle must not pass verification."""
    library = tmp_path / "library"
    import shutil

    shutil.copytree(LIBRARY, library)
    assert (
        runner.invoke(
            app, ["add", MAIN, "--project", str(project), "--library", str(library)]
        ).exit_code
        == 0
    )
    skill = library / "macos-notarize-tauri" / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8") + "\n<!-- edited elsewhere -->\n", encoding="utf-8"
    )
    result = runner.invoke(app, ["verify", "--project", str(project), "--library", str(library)])
    assert result.exit_code == 1
    assert "bundle hash drift" in result.output


def test_pull_materialises_bundles_including_assets(project: Path) -> None:
    _add(project)
    out = project / "out"
    result = runner.invoke(
        app, ["pull", "--project", str(project), "--library", str(LIBRARY), "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    # Flat by name, not `<scope>/<name>`: `<skills-root>/<name>/SKILL.md` is
    # what an agent looks up, and pull writes where it will be found.
    assert (out / "macos-notarize-tauri" / "SKILL.md").is_file()
    assert (out / "macos-notarize-tauri" / "tools" / "verify-signatures" / "reference.sh").is_file()


def test_show_describes_a_skill_without_installing_it(tmp_path: Path) -> None:
    """`show` is for the moment before installing: what is this, do I want it?"""
    skills = REPO_ROOT / "skills"
    runner.invoke(app, ["init", "--project", str(tmp_path)])
    result = runner.invoke(
        app, ["show", MAIN, "--project", str(tmp_path), "--library", str(skills)]
    )
    assert result.exit_code == 0, result.output
    assert "5 step(s)" in result.output
    assert "builds on: @speccify/apple-developer-id-cert" in result.output
    assert "4 source(s)" in result.output


def test_show_as_json_carries_the_body(tmp_path: Path) -> None:
    skills = REPO_ROOT / "skills"
    runner.invoke(app, ["init", "--project", str(tmp_path)])
    result = runner.invoke(
        app,
        ["show", MAIN, "--json", "--project", str(tmp_path), "--library", str(skills)],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["id"] == MAIN
    assert "hardened runtime" in payload["body"]
    assert payload["uses"] == ["@speccify/apple-developer-id-cert@^1.0"]


def test_show_works_without_a_manifest_when_pointed_at_a_library(tmp_path: Path) -> None:
    """Reading a skill is not a project operation.

    Most skills live in some repository that is not a Speccify project. If
    `--library` names one, requiring a `speccify.yaml` next to it would stop an
    agent from reading anything it had not first `add`ed.
    """
    result = runner.invoke(
        app, ["show", MAIN, "--project", str(tmp_path), "--library", str(REPO_ROOT / "skills")]
    )
    assert result.exit_code == 0, result.output
    assert MAIN in result.output


def test_show_without_manifest_or_library_names_both_ways_out(tmp_path: Path) -> None:
    result = runner.invoke(app, ["show", MAIN, "--project", str(tmp_path)])
    assert result.exit_code == 1
    assert "speccify init" in result.output and "--library" in result.output


def test_lint_accepts_the_reference_library() -> None:
    """Everything shipped in this repo must always validate."""
    result = runner.invoke(app, ["lint", str(LIBRARY)])
    assert result.exit_code == 0, result.output
    assert "skill(s) validated" in result.output
    assert "fail" not in result.output


def test_lint_reports_a_broken_skill(tmp_path: Path) -> None:
    bundle = tmp_path / "Broken-Name"
    bundle.mkdir()
    (bundle / "SKILL.md").write_text(
        "---\nname: Broken-Name\ndescription: Something. Use when something.\n---\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["lint", str(bundle)])
    assert result.exit_code == 1
    assert "fail" in result.output


def test_check_is_clean_for_the_reference_library() -> None:
    result = runner.invoke(app, ["check", str(LIBRARY)])
    assert result.exit_code == 0, result.output
    assert "0 error(s), 0 warning(s)" in result.output


def test_check_warns_about_stale_sources() -> None:
    result = runner.invoke(app, ["check", str(LIBRARY), "--stale-days", "0"])
    assert result.exit_code == 0, result.output
    # Warnings do not fail the run — only errors do.
    assert "warning(s)" in result.output


def test_check_fails_on_a_reference_the_agent_cannot_read(tmp_path: Path) -> None:
    """A dangling pointer is an error, not a style note — the agent will try it."""
    bundle = tmp_path / "broken"
    bundle.mkdir()
    (bundle / "SKILL.md").write_text(
        "---\nname: broken\ndescription: Something. Use when something.\n---\n\n"
        "See [the details](DETAILS.md).\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["check", str(bundle)])
    assert result.exit_code == 1
    assert "DETAILS.md" in result.output


def test_lint_and_check_accept_the_shipped_skills() -> None:
    """The skills in `skills/` are the product; they must never be broken."""
    skills = REPO_ROOT / "skills"
    lint = runner.invoke(app, ["lint", str(skills)])
    assert lint.exit_code == 0, lint.output
    assert "skill(s) validated" in lint.output

    # Offline: specification, best practice and source age — no network.
    check = runner.invoke(app, ["check", str(skills)])
    assert check.exit_code == 0, check.output
    assert "0 error(s)" in check.output


def test_the_local_loop_works_on_skills(tmp_path: Path) -> None:
    """init -> add -> lock -> pull -> verify, against `skills/`.

    This is M1 in one test: a project declares a skill, the child it builds on
    is resolved transitively, and both land where Claude Code looks for them —
    flat, by name, with assets.
    """
    skills = REPO_ROOT / "skills"
    assert runner.invoke(app, ["init", "--project", str(tmp_path)]).exit_code == 0

    added = runner.invoke(app, ["add", MAIN, "--project", str(tmp_path), "--library", str(skills)])
    assert added.exit_code == 0, added.output

    out = tmp_path / ".claude" / "skills"
    pulled = runner.invoke(
        app, ["pull", "--project", str(tmp_path), "--library", str(skills), "--out", str(out)]
    )
    assert pulled.exit_code == 0, pulled.output

    # The parent and the child it delegates to, both by bare name.
    assert (out / "macos-notarize-tauri" / "SKILL.md").is_file()
    assert (out / "apple-developer-id-cert" / "SKILL.md").is_file()
    assert (out / "macos-notarize-tauri" / "tools" / "verify-signatures" / "reference.sh").is_file()

    verified = runner.invoke(app, ["verify", "--project", str(tmp_path), "--library", str(skills)])
    assert verified.exit_code == 0, verified.output


def test_expand_makes_normal_skills_under_agent(tmp_path: Path) -> None:
    """add -> lock -> expand -> link -> verify: the skill arrives as plain Markdown.

    Under `.agent/skills/` nothing Speccify-specific is left; the child it
    builds on is a sibling; the tool spec is project-wide under `.agent/tools/`
    and the agent is told to implement it for this platform.
    """
    skills = REPO_ROOT / "skills"
    assert runner.invoke(app, ["init", "--project", str(tmp_path)]).exit_code == 0
    assert _add(tmp_path).exit_code == 0

    expanded = runner.invoke(
        app,
        ["expand", "--project", str(tmp_path), "--library", str(skills), "--platform", "macos"],
    )
    assert expanded.exit_code == 0, expanded.output
    assert "created   .agent/skills/macos-notarize-tauri" in expanded.output
    assert "created   .agent/skills/apple-developer-id-cert (used by macos-notarize-tauri)" in (
        expanded.output
    )
    assert ".agent/tools/verify-signatures/macos.<ext>" in expanded.output

    skill = (tmp_path / ".agent" / "skills" / "macos-notarize-tauri" / "SKILL.md").read_text()
    assert "speccify." not in skill.split("---")[1], "metadata is stripped"
    assert "[apple-developer-id-cert](../apple-developer-id-cert/SKILL.md)" in skill
    assert "## In this project" in skill
    assert not (tmp_path / ".agent" / "skills" / "macos-notarize-tauri" / "tools").exists()
    assert (tmp_path / ".agent" / "tools" / "verify-signatures" / "TOOL.md").is_file()
    assert (tmp_path / ".agent" / "tools" / "verify-signatures" / "reference.sh").is_file()

    record = yaml.safe_load((tmp_path / ".agent" / "speccify" / "expansions.yaml").read_text())
    assert record["skills"]["macos-notarize-tauri"]["requested"] is True
    assert record["skills"]["apple-developer-id-cert"]["requested"] is False
    assert record["tools"]["verify-signatures"]["from"] == ["macos-notarize-tauri"]

    linked = runner.invoke(app, ["link", "--project", str(tmp_path)])
    assert linked.exit_code == 0, linked.output
    link = tmp_path / ".claude" / "skills"
    assert link.is_symlink()
    assert (link / "macos-notarize-tauri" / "SKILL.md").is_file()

    verified = runner.invoke(app, ["verify", "--project", str(tmp_path), "--library", str(skills)])
    assert verified.exit_code == 0, verified.output
    assert "verify-signatures' has no implementation" in verified.output


def test_expand_is_idempotent_and_keeps_implementations(tmp_path: Path) -> None:
    skills = REPO_ROOT / "skills"
    runner.invoke(app, ["init", "--project", str(tmp_path)])
    _add(tmp_path)
    args = ["expand", "--project", str(tmp_path), "--library", str(skills), "--platform", "macos"]
    assert runner.invoke(app, args).exit_code == 0

    tool_dir = tmp_path / ".agent" / "tools" / "verify-signatures"
    (tool_dir / "macos.sh").write_text("#!/bin/sh\necho mine\n")
    skill_file = tmp_path / ".agent" / "skills" / "macos-notarize-tauri" / "SKILL.md"
    skill_file.write_text(
        skill_file.read_text().replace(
            "## In this project\n", "## In this project\n\n- Team: ABC123\n"
        )
    )

    again = runner.invoke(app, args)
    assert again.exit_code == 0, again.output
    assert "unchanged .agent/skills/macos-notarize-tauri" in again.output
    assert "Tools to implement" not in again.output
    assert (tool_dir / "macos.sh").read_text() == "#!/bin/sh\necho mine\n"
    assert "- Team: ABC123" in skill_file.read_text()
    record = yaml.safe_load((tmp_path / ".agent" / "speccify" / "expansions.yaml").read_text())
    assert record["tools"]["verify-signatures"]["platforms"]["macos"]["status"] == "implemented"


def test_verify_reports_upstream_drift_against_the_expansion(tmp_path: Path) -> None:
    """Upstream changed after expand: verify says so and names the fix."""
    import shutil

    library = tmp_path / "library"
    shutil.copytree(REPO_ROOT / "skills", library)
    project = tmp_path / "project"
    runner.invoke(app, ["init", "--project", str(project)])
    assert (
        runner.invoke(
            app, ["add", MAIN, "--project", str(project), "--library", str(library)]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["expand", "--project", str(project), "--library", str(library)]
        ).exit_code
        == 0
    )

    # Upstream moves on (same version, new content) and the lock is refreshed.
    skill = library / "macos-notarize-tauri" / "SKILL.md"
    skill.write_text(skill.read_text() + "\n## 6 — New upstream step\n\nDo more.\n")
    assert (
        runner.invoke(app, ["lock", "--project", str(project), "--library", str(library)]).exit_code
        == 0
    )

    verified = runner.invoke(app, ["verify", "--project", str(project), "--library", str(library)])
    assert verified.exit_code == 1
    assert "changed since it was expanded" in verified.output
    assert "speccify expand" in verified.output


FAKE_VERIFY_SIGNATURES = """import json, sys
data = json.load(sys.stdin)
bundle = data["bundle"]
if bundle == "fixtures/Signed.app":
    out = {"ok": True, "checked": [".", "Contents/MacOS/Signed", "Contents/MacOS/helper"],
           "offenders": []}
elif bundle == "fixtures/Broken.app":
    out = {"ok": False, "checked": [".", "Contents/MacOS/Broken", "Contents/MacOS/helper"],
           "offenders": [{"path": "Contents/MacOS/helper",
                          "reason": "code object is not signed at all"}]}
else:
    out = {"ok": False, "checked": [".", "Contents/MacOS/AdHoc"],
           "offenders": [{"path": ".",
                          "reason": "signed by 'adhoc', expected 'Developer ID Application'"}]}
print(json.dumps(out))
sys.exit(0 if out["ok"] else 1)
"""


def _expanded_project(tmp_path: Path) -> Path:
    runner.invoke(app, ["init", "--project", str(tmp_path)])
    _add(tmp_path)
    args = ["expand", "--project", str(tmp_path), "--library", str(LIBRARY), "--platform", "macos"]
    assert runner.invoke(app, args).exit_code == 0
    return tmp_path


def _record(project: Path) -> dict:
    return yaml.safe_load((project / ".agent" / "speccify" / "expansions.yaml").read_text())


def test_tool_check_without_implementations_runs_nothing(tmp_path: Path) -> None:
    project = _expanded_project(tmp_path)
    result = runner.invoke(app, ["tool", "check", "--project", str(project), "--platform", "macos"])
    assert result.exit_code == 0, result.output
    assert "verify-signatures  not-implemented" in result.output
    assert "0 verified, 0 failed, 1 not run" in result.output


def test_tool_check_verifies_an_implementation_and_records_it(tmp_path: Path) -> None:
    """implemented -> verified: the examples pass, the record says so, verify is quiet."""
    project = _expanded_project(tmp_path)
    tool_dir = project / ".agent" / "tools" / "verify-signatures"
    (tool_dir / "macos.py").write_text(FAKE_VERIFY_SIGNATURES)
    # `codesign` is in `requires`; it is a macOS binary, which the runner insists on.
    (tool_dir / "TOOL.md").write_text(
        (tool_dir / "TOOL.md").read_text().replace("requires: codesign\n", "")
    )

    result = runner.invoke(app, ["tool", "check", "--project", str(project), "--platform", "macos"])
    assert result.exit_code == 0, result.output
    assert "ok   verify-signatures  3 example(s) pass (macos.py) -> verified for macos" in (
        result.output
    )
    macos = _record(project)["tools"]["verify-signatures"]["platforms"]["macos"]
    assert macos["status"] == "verified"
    assert macos["file"] == "macos.py"
    assert macos["checked"]

    verified = runner.invoke(app, ["verify", "--project", str(project), "--library", str(LIBRARY)])
    assert verified.exit_code == 0, verified.output
    assert "not yet checked" not in verified.output
    assert "no implementation" not in verified.output


def test_tool_check_failure_names_the_example_and_demotes_the_tool(tmp_path: Path) -> None:
    project = _expanded_project(tmp_path)
    tool_dir = project / ".agent" / "tools" / "verify-signatures"
    (tool_dir / "TOOL.md").write_text(
        (tool_dir / "TOOL.md").read_text().replace("requires: codesign\n", "")
    )
    (tool_dir / "macos.py").write_text(FAKE_VERIFY_SIGNATURES)
    args = ["tool", "check", "--project", str(project), "--platform", "macos"]
    assert runner.invoke(app, args).exit_code == 0

    # The implementation regresses: it stops reporting the helper.
    (tool_dir / "macos.py").write_text(
        FAKE_VERIFY_SIGNATURES.replace(
            '"offenders": [{"path": "Contents/MacOS/helper"',
            '"offenders": [{"path": "Contents/MacOS/other"',
        )
    )
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "x    verify-signatures  1 of 3 example(s) fail" in result.output
    assert "'one unsigned sidecar': $.offenders[0].path: expected" in result.output
    assert _record(project)["tools"]["verify-signatures"]["platforms"]["macos"]["status"] == (
        "implemented"
    )

    as_json = runner.invoke(app, [*args, "--json"])
    payload = json.loads(as_json.output)
    assert payload["ok"] is False
    failing = [c for c in payload["tools"][0]["cases"] if c["status"] == "failed"]
    assert failing[0]["actual"]["offenders"][0]["path"] == "Contents/MacOS/other"


def test_tool_check_names_an_unknown_tool(tmp_path: Path) -> None:
    project = _expanded_project(tmp_path)
    result = runner.invoke(app, ["tool", "check", "nope", "--project", str(project)])
    assert result.exit_code == 1
    assert ".agent/tools/nope/TOOL.md" in result.output


def test_a_changed_spec_takes_verified_away(tmp_path: Path) -> None:
    """Re-expand after upstream changed the contract: the old verification counts for nothing."""
    import shutil

    library = tmp_path / "library"

    shutil.copytree(LIBRARY, library)
    project = tmp_path / "project"
    project.mkdir()
    runner.invoke(app, ["init", "--project", str(project)])
    assert _add_from(project, library).exit_code == 0
    args = ["expand", "--project", str(project), "--library", str(library), "--platform", "macos"]
    assert runner.invoke(app, args).exit_code == 0
    tool_dir = project / ".agent" / "tools" / "verify-signatures"
    (tool_dir / "macos.py").write_text(FAKE_VERIFY_SIGNATURES)
    (tool_dir / "TOOL.md").write_text(
        (tool_dir / "TOOL.md").read_text().replace("requires: codesign\n", "")
    )
    checked = runner.invoke(
        app, ["tool", "check", "--project", str(project), "--platform", "macos"]
    )
    assert checked.exit_code == 0, checked.output
    assert _record(project)["tools"]["verify-signatures"]["platforms"]["macos"]["status"] == (
        "verified"
    )

    spec = library / "macos-notarize-tauri" / "tools" / "verify-signatures" / "TOOL.md"
    spec.write_text(
        spec.read_text()
        + '\n### a fourth case\ninput: {"bundle": "x"}\n'
        + 'output: {"ok": false, "checked": [], "offenders": []}\n'
    )
    assert (
        runner.invoke(app, ["lock", "--project", str(project), "--library", str(library)]).exit_code
        == 0
    )
    again = runner.invoke(app, args)
    assert again.exit_code == 0, again.output
    macos = _record(project)["tools"]["verify-signatures"]["platforms"]["macos"]
    assert macos["status"] == "implemented"
    assert "checked" not in macos
    assert (tool_dir / "macos.py").read_text() == FAKE_VERIFY_SIGNATURES


def _add_from(project: Path, library: Path, reference: str = MAIN):
    return runner.invoke(
        app, ["add", reference, "--project", str(project), "--library", str(library)]
    )


def test_expand_accepts_the_short_name_of_a_locked_skill(tmp_path: Path) -> None:
    """`speccify expand macos-notarize-tauri` reicht — das Lockfile kennt die Id."""
    from speccify_cli.commands.expand import _resolve_reference

    locked = {
        "@speccify/macos-notarize-tauri": object(),
        "git+https://example.test/kit#skills/cert": object(),
    }
    assert _resolve_reference("macos-notarize-tauri", locked) == "@speccify/macos-notarize-tauri"
    assert _resolve_reference("cert", locked) == "git+https://example.test/kit#skills/cert"
    assert (
        _resolve_reference("git+https://example.test/kit#skills/cert@^1.0", locked)
        == "git+https://example.test/kit#skills/cert"
    )
    with pytest.raises(Exception, match="not in the lockfile"):
        _resolve_reference("nope", locked)
    ambiguous = {**locked, "@other/cert": object()}
    with pytest.raises(Exception, match="ambiguous"):
        _resolve_reference("cert", ambiguous)


def test_tool_check_records_project_own_tools(tmp_path: Path) -> None:
    """Ein Tool, das nicht aus `expand` kam, bekommt trotzdem seinen Status im Nachweis."""
    from speccify_cli.commands.tool import run_tool_check
    from speccify_core.expansion import Expansions

    tool_dir = tmp_path / ".agent" / "tools" / "upper"
    tool_dir.mkdir(parents=True)
    (tool_dir / "TOOL.md").write_text(
        "---\nname: upper\ndescription: Uppercases.\n"
        "inputs: {type: object, properties: {t: {type: string}}}\n"
        "outputs: {type: object, properties: {ok: {type: boolean}, t: {type: string}}}\n"
        '---\n\n## Examples\n\n### a\ninput: {"t": "a"}\noutput: {"ok": true, "t": "A"}\n',
        encoding="utf-8",
    )
    (tool_dir / "macos.py").write_text(
        "import json,sys\nd=json.load(sys.stdin)\n"
        "print(json.dumps({'ok': True, 't': d['t'].upper()}))\n",
        encoding="utf-8",
    )
    (tool_dir / "linux.py").write_text((tool_dir / "macos.py").read_text(), encoding="utf-8")
    report = run_tool_check(tmp_path, ["upper"])
    assert report.ok
    record = Expansions.load(tmp_path / ".agent" / "speccify" / "expansions.yaml")
    assert record.tools["upper"].from_skills == ()
    assert record.tools["upper"].status(report.platform) == "verified"
