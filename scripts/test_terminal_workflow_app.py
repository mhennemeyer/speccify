"""Opt-in Spec 012 tests against the bundled app; reuse speccify-qa's adapter.

Run with SPECCIFY_QA_ROOT pointing at that checkout. No host/model invocation;
these cases exercise real workflow commands, watchers, windows and shell PTYs.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest
from create_terminal_fixture import create

SPEC = ".agent/specs/001-summary/SPEC.md"


@pytest.fixture
def app():
    qa_root = os.environ.get("SPECCIFY_QA_ROOT")
    if not qa_root or not (Path(qa_root) / "speccify_qa/bridge.py").is_file():
        pytest.skip("Set SPECCIFY_QA_ROOT to the speccify-qa checkout")
    sys.path.insert(0, qa_root)
    from speccify_qa.bridge import Bridge
    from speccify_qa.pages import App

    class PrivateBridge(Bridge):
        def __repr__(self):
            return f"PrivateBridge(url={self.url!r}, token=<redacted>)"

    bridge = PrivateBridge.from_env()
    if not bridge or not bridge.alive():
        pytest.skip("Start bundled Speccify with --qa-bridge=18769")
    return App(bridge)


@pytest.fixture
def projects(app, tmp_path):
    roots = [create(tmp_path / name) for name in ("terminal-a", "terminal-b")]
    keys = [f"speccify.project.agentCommand:{root}" for root in roots]
    try:
        for key in keys:
            app.bridge.eval("main", f"localStorage.setItem({json.dumps(key)}, ''); return true;")
        yield [app.open_project(root) for root in roots]
    finally:
        for root in roots:
            window = app.project_window(root)
            if window:
                app.close_window(window.label)
        for key in keys:
            app.bridge.eval("main", f"localStorage.removeItem({json.dumps(key)}); return true;")


def test_native_setup_watcher_questions_and_reopen(app, projects):
    window, other = projects
    root = window.root
    guidance = (root / ".agent/agent.md").read_text(encoding="utf-8")
    result = app.bridge.invoke(window.label, "project_workflow_install", {"project": str(root)})
    assert result["state"] == "current", result
    assert (root / ".agent/agent.md").read_text(encoding="utf-8").startswith(guidance.rstrip())
    result = app.bridge.invoke(window.label, "project_workflow_status", {"project": str(root)})
    assert result["state"] == "current", result

    spec = root / SPEC
    original = spec.read_text(encoding="utf-8")
    other_before = other.read_file(SPEC)
    changed = (
        original.replace("station: Backlog", "station: Doing").replace(
            "open_question: null", "open_question: Q1"
        )
        + "\n### Q1 · open · 2026-09-15T00:00:00Z\nChoose the fixture label: amber or teal?\n"
    )
    start = time.monotonic()
    spec.write_text(changed, encoding="utf-8")
    window.wait("return $$('[data-station=Doing] [data-spec-card]').length === 1;", timeout=10)
    print(f"watcher update: {time.monotonic() - start:.3f}s")
    assert other.read_file(SPEC) == other_before
    app.close_window(window.label)
    reopened = app.open_project(root)
    reopened.board.select(SPEC)
    dialog = reopened.board.open_handover()
    assert "open_question: Q1" in dialog.preview()
    assert "Choose the fixture label" in dialog.preview()
    dialog.close()

    answered = (
        changed.replace("open_question: Q1", "open_question: null")
        .replace("ready: false", "ready: true")
        .replace("- [ ]", "- [x]")
        .replace("## Decisions", "## Decisions\n\nD1: Fixture answer selects teal.")
        .replace("### Q1 · open", "### Q1 · answered")
    )
    answered += "\n### A1 · test-fixture · 2026-09-15T00:01:00Z\nteal\n"
    spec.write_text(answered, encoding="utf-8")
    reopened.wait(
        "return $$('[data-station=Doing] [data-spec-card]')"
        ".some(el => el.innerText.includes('4/4'));",
        timeout=10,
    )
    assert reopened.board.cards("Done") == []
    reopened.board.select(SPEC)
    dialog = reopened.board.open_handover()
    assert "ready: true" in dialog.preview()
    assert "D1: Fixture answer selects teal." in dialog.preview()
    assert "### A1 · test-fixture" in dialog.preview()
    dialog.close()


def start_shell(window):
    window.eval("byRole('button', 'Agent-Terminal starten').click(); return true;")
    window.terminal.wait_ready(timeout=30)


def key(window, *, interrupt=False):
    options = (
        {"key": "c", "code": "KeyC", "keyCode": 67, "ctrlKey": True, "bubbles": True}
        if interrupt
        else {"key": "Enter", "code": "Enter", "keyCode": 13, "bubbles": True}
    )
    window.eval(
        "document.querySelector('.xterm-helper-textarea').dispatchEvent("
        f"new KeyboardEvent('keydown', {json.dumps(options)})); return true;"
    )


def command(window, text):
    window.eval(
        "const event = new Event('paste', {bubbles:true, cancelable:true});"
        "Object.defineProperty(event, 'clipboardData', {value: {"
        f"getData: () => {json.dumps(text)} }} }});"
        "document.querySelector('.xterm-helper-textarea').dispatchEvent(event); return true;"
    )
    key(window)


def test_two_real_shells_route_input_and_handle_interrupt(app, projects):
    first, second = projects
    for window, prefix, value in zip(projects, ("A-", "B-"), ("ä-🌍", "ß-🌍"), strict=True):
        start_shell(window)
        command(window, f"printf '%s%s\\n' '{prefix}' '{value}'")
        window.terminal.wait_text(prefix + value, timeout=10)
    assert "B-ß-🌍" not in first.terminal.text()
    assert "A-ä-🌍" not in second.terminal.text()
    command(first, "sleep 30")
    first.terminal.wait_text("sleep 30")
    key(first, interrupt=True)
    command(first, "printf '%s%s\\n' 'interrupt-' 'complete'")
    first.terminal.wait_text("interrupt-complete", timeout=10)
    command(first, "exit")
    first.terminal.wait_text("Shell beendet", timeout=10)
    command(second, "printf '%s%s\\n' 'second-' 'still-live'")
    second.terminal.wait_text("second-still-live", timeout=10)
