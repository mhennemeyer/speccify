---
title: Terminal & agent settings
description: Terminal appearance, attention alerts, and editable Codex and Claude configuration.
sidebar:
  order: 7
---

**Available in Speccify 0.8.2.** See the [release notes](/releases/0-8-2/)
for installation and update instructions.

## Language

The app speaks English and German. **Settings → Language** in the dashboard,
or the gear in a project or workspace window, offers **System**, **Deutsch**
and **English**. *System* follows the operating system (German for `de*`
locales, English otherwise). The choice applies at once in every open window
and is stored in `~/.speccify/settings.json` as `language`. Messages that come
straight from the native side are still German for now.

## Appearance

The terminal follows Light, Dark, or System appearance, including its controls,
cursor and ANSI colours. Use **A− / A+** in the terminal, or the font selector
in Settings, to choose **8–32 px**. The default is 14 px. The setting is shared
across windows and saved locally. Changing it resizes the terminal without
restarting the shell or agent.

## Terminals that survive app restarts

**Available in Speccify 0.8.7.** The switch **Terminals überleben App-Neustarts**
runs new terminals in a host process next to the app. Quitting or rebuilding the
app only disconnects them; the project or workspace window re-attaches on the
next start, shows the output so far and accepts input. Closing the window or
**Neu starten** still end the session, and the host process ends itself a minute
after its last session. Terminals started before the switch was turned on keep
running inside the app process. Copy with ⌘C (Ctrl+Shift+C) wherever the focus
is; the header confirms with **Kopiert**.

## Notice waiting questions

Settings provides two independent switches:

- **Rückfragen als Popup anzeigen**: show a notice in the source window, even
  when its terminal pane is hidden. **Zum Terminal** reveals that terminal.
- **Systemmeldungen bei inaktivem Fenster**: request operating-system attention
  when the window is not focused. **Systemmeldung testen** sends a test notice.

Speccify handles terminal notification signals (OSC 9, OSC 777 and bell) and
recognises common English/German approval prompts. Repeated redraws are
deduplicated. Free-form questions are not reliably detectable from terminal text.
The notice does not answer the question or grant command permissions.

On Windows, use the installed application. Enable notifications for Speccify in
the operating system and check Focus/Do Not Disturb settings if the test does not
appear. OS delivery can be suppressed while in-app notices remain available.

## Edit the agent's configuration

Open **Agents** in the dashboard, or **Agent-Einstellungen** from project/workspace
Settings or the Agent tab. Select Codex or Claude, then use topic groups or search.
Each documented field has help; complex arrays and objects use JSON editors.
**Nicht setzen** removes that key from this file and lets other configuration
layers or the host default apply. **Quelltext** exposes the whole TOML/JSON file,
including keys newer than the bundled catalogue. Instruction files remain editable
as text.

The editor modifies the current user's global configuration. The exact path is
shown; `CODEX_HOME` and `CLAUDE_CONFIG_DIR` are respected when present in Speccify's
environment. A shell that changes these variables may use a different path.
Project files, active profiles, command-line flags and managed policy can override
global values. This view is not a report of a running session's effective settings.

Changes stay in a draft until **Speichern**. Use **Änderungen zurücknehmen** to
discard them. Saving checks syntax and changed known types/enums/ranges, preserves
unknown keys, and refuses to overwrite a file modified since it was loaded.
TOML comments outside a replaced complex value are retained. Copy any draft you
need before reloading after a conflict. Restart the agent to apply saved settings
consistently; saving does not restart a running task.

## A starting profile for autonomous work

Expand **Selbstständig arbeiten** to see the exact proposed changes. Applying the
profile creates a draft; inspect it and save when ready.

For Codex it sets `approval_policy = "on-request"`,
`approvals_reviewer = "auto_review"` and `sandbox_mode = "workspace-write"`, plus
terminal notification settings. Eligible approvals are reviewed automatically;
workspace boundaries, network settings and managed restrictions still apply.
`never` instead prevents escalation and returns blocked operations as failures.
See the [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

On native Windows, review **windows.sandbox**: Codex recommends `elevated` and
requires a one-time setup. WSL uses the Linux environment. Speccify cannot skip
Windows' setup approval. See [Windows sandbox setup](https://learn.chatgpt.com/docs/windows/windows-sandbox).

For Claude, the profile sets `permissions.defaultMode` to `auto`. Availability
depends on the installed host, account, model and managed policy; explicit ask
rules can still prompt. `acceptEdits` mainly reduces file-edit questions.
See [Claude permission modes](https://code.claude.com/docs/en/permission-modes).

The catalogue is bundled for offline use (snapshot 2026-09-16). A newer schema
does not make an older CLI support new options. Existing rules and unrelated
settings are preserved. Read the [Claude settings reference](https://code.claude.com/docs/en/settings)
for configuration precedence and scope.

## Multiline input

Use **Shift+Enter** to insert a line break in a Codex or Claude prompt;
**Enter** submits it. Speccify forwards Shift+Enter as a distinct modified key
(`CSI-u`), so it requires support in the terminal application. Other shells or
custom host key bindings may behave differently.

## Insert versus run

Existing handover buttons paste text without submitting it. Sending an explicit
Enter is technically possible, but a terminal can be at a shell prompt, an agent
input, or a permission dialog. A future **Insert and send** action therefore needs
an explicit user action and a clear destination. This update does not change
existing handovers to automatic execution.
