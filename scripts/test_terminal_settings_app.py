"""Opt-in native checks for terminal settings, attention and Enter research.

Uses disposable projects and shell commands only; never writes host configuration.
Run with the same SPECCIFY_QA_ROOT and bundled app as test_terminal_workflow_app.py.
"""

import json
import time

from test_terminal_workflow_app import app as app
from test_terminal_workflow_app import command, key, start_shell
from test_terminal_workflow_app import projects as projects


def paste(window, text):
    window.eval(
        "const event = new Event('paste', {bubbles:true,cancelable:true});"
        "Object.defineProperty(event,'clipboardData',{value:{getData:()=>"
        + json.dumps(text)
        + "}}); document.querySelector('.xterm-helper-textarea').dispatchEvent(event); return true;"
    )


def test_native_terminal_preferences_attention_and_enter(app, projects):
    first, second = projects
    prefs = app.bridge.invoke(first.label, "terminal_preferences")
    try:
        app.bridge.invoke(
            first.label,
            "terminal_preferences_update",
            {
                "fontSize": 14,
                "popups": True,
                "systemNotifications": False,
            },
        )
        for window in projects:
            app.bridge.focus(window.label)
            window.eval(
                "window.__testTermEvents={};"
                "const handler=window.__TAURI_INTERNALS__.transformCallback(event=>{"
                "const {id,data}=event.payload;"
                "window.__testTermEvents[id]=(window.__testTermEvents[id]||'')+data;});"
                "await window.__TAURI_INTERNALS__.invoke('plugin:event|listen',"
                "{event:'term-out',target:{kind:'Any'},handler}); return true;"
            )
            start_shell(window)
        app.bridge.focus(first.label)
        command(first, "SPECCIFY_TEST_MARKER=kept; printf '%s%s\\n' 'native-' 'Grüße-🌍'")
        first.terminal.wait_text("native-Grüße-🌍")
        for theme, background in (("light", "#ffffff"), ("dark", "#0f172a")):
            first.eval(f"document.documentElement.dataset.theme='{theme}'; return true;")
            first.wait(
                f"return window.__speccifyQa.terminalAppearance().background === '{background}';"
            )
        old_cols = first.eval("return window.__speccifyQa.terminalAppearance().cols;")
        app.bridge.invoke(first.label, "terminal_preferences_update", {"fontSize": 24})
        for window in projects:
            window.wait("return window.__speccifyQa.terminalAppearance().fontSize === 24;")
        first.wait(f"return window.__speccifyQa.terminalAppearance().cols < {old_cols};")
        assert "native-Grüße-🌍" in first.terminal.text()
        command(first, "printf 'shell-state-%s\\n' \"$SPECCIFY_TEST_MARKER\"")
        first.terminal.wait_text("shell-state-kept")

        # Actual paste leaves both shell lines pending until an explicit CR.
        proof = first.root / "enter-proof.txt"
        paste(
            first, "printf '%s' 'first' > enter-proof.txt\nprintf '%s' '-second' >> enter-proof.txt"
        )
        time.sleep(0.7)
        assert not proof.exists(), "Pasting must not submit the shell command"
        terminal_id = first.eval(
            "return Object.entries(window.__testTermEvents).find("
            "([id,data])=>data.includes('native-Grüße-🌍'))?.[0];"
        )
        assert terminal_id
        app.bridge.invoke(first.label, "terminal_write", {"id": terminal_id, "data": "\r"})
        for _ in range(50):
            if proof.exists() and proof.read_text() == "first-second":
                break
            time.sleep(0.1)
        assert proof.read_text() == "first-second"

        # Print a terminal signal from a delayed command, then hide the pane.
        command(first, "sleep 1; printf '\\033]9;Test attention\\007'")
        first.eval(
            "document.querySelector('.terminal-surface').style.visibility='hidden'; return true;"
        )
        first.wait(
            "return !!document.querySelector('[aria-label=\"Terminal braucht Aufmerksamkeit\"]');"
        )
        assert second.eval(
            "return !document.querySelector('[aria-label=\"Terminal braucht Aufmerksamkeit\"]');"
        )
        first.eval(
            "const popup=document.querySelector("
            "'[aria-label=\"Terminal braucht Aufmerksamkeit\"]');"
            "if(popup.closest('.terminal-surface')) throw Error('Popup hidden by terminal');"
            "byRole('button','Zum Terminal',popup).click();"
            "document.querySelector('.terminal-surface').style.visibility=''; return true;"
        )
        command(first, "sleep 30")
        key(first, interrupt=True)
        command(first, "printf '%s%s\\n' 'interrupt-' 'ok'")
        first.terminal.wait_text("interrupt-ok")
        command(first, "exit")
        first.terminal.wait_text("Shell beendet")
        first.eval("byRole('button','Neu starten').click(); return true;")
        first.wait(
            "return window.__speccifyQa.terminalReady() && "
            "!window.__speccifyQa.terminalText().includes('Shell beendet');",
            timeout=30,
        )
        command(first, "printf '%s%s\\n' 'restart-' 'ok'")
        first.terminal.wait_text("restart-ok")

        # Native parser/patch path uses supplied test strings, not real settings files.
        draft = app.bridge.invoke(
            first.label,
            "agent_config_patch",
            {
                "id": "codex-config",
                "content": "# retained\ncustom_key='retained'\n",
                "changes": [{"path": ["approvals_reviewer"], "value": "auto_review"}],
            },
        )
        assert "# retained" in draft and "custom_key" in draft
        parsed = app.bridge.invoke(
            first.label, "agent_config_parse", {"id": "codex-config", "content": draft}
        )
        assert parsed["approvals_reviewer"] == "auto_review"
    finally:
        app.bridge.invoke(
            first.label,
            "terminal_preferences_update",
            {
                "fontSize": prefs["font_size"],
                "popups": prefs["popups"],
                "systemNotifications": prefs["system_notifications"],
            },
        )
