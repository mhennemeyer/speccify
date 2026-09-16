# Research: submit text to a terminal

Status: research for Spec 055, 2026-09-16. No change to existing handover behaviour.

## Result

The PTY accepts ordinary text and control characters. `terminal_write` writes
the supplied UTF-8 bytes and flushes the writer. A carriage return (`\r`) represents
the Enter input used by the existing startup path in `terminal.rs`.

`handover.ts` deliberately omits Enter. It wraps multiline text in bracketed-paste
markers so the receiving program can treat line breaks as a single paste.
Submission is a separate input. That separation prevents an ordinary insertion
from executing immediately.

## Practical proof

`scripts/test_terminal_settings_app.py` runs against the bundled app and a real
shell PTY in a disposable project. It pastes two commands that write a test file,
checks the file does not exist, sends `terminal_write` with `data: "\r"`, and
checks both lines executed exactly as intended. The same test exercises Unicode,
live appearance/font changes, two windows, an OSC notice, Ctrl-C, exit and restart.
The verification result is recorded in Spec 055 after the run.

## Shell, Codex and Claude

| Receiver | What Enter does | What Speccify can establish |
| --- | --- | --- |
| Ready interactive shell | Submits the pending shell input | Proven with the local zsh PTY test |
| Codex at its input prompt | Normally submits the pending prompt | PTY can deliver the key; no stable prompt-ready acknowledgement is exposed by the current terminal integration |
| Claude at its input prompt | Normally submits the pending prompt | Same transport; readiness, pending text and current dialog must be checked separately |
| Any host displaying an approval/choice dialog | May confirm the selected answer | A generic Enter cannot distinguish this from ordinary prompt submission |

CLI versions and input modes can alter the meaning of keys. This research does
not claim an automated end-to-end Codex/Claude submission test. Their existing
manually submitted task roundtrips are documented in `terminal-acceptance.md`.

## Proposed follow-up

Add a separate, clearly labelled **Insert and send** action alongside the existing
**Insert** action. Show the destination project/session and the exact text first.
Require a live terminal and explicit confirmation that its input is ready; do not
infer permission approval from a text match. Keep paste and Enter as separate
writes, handle failures without blindly retrying, and prevent repeated clicks.

A fixed delay after paste is not proof of readiness. The receiver may still be
starting, its input may contain a draft, or a trust/permission prompt may own the
keyboard. Reliable unattended submission would need a host-specific structured
interface with acknowledgements, rather than only a rendered terminal buffer.

## Sources and code

- [xterm.js Terminal API](https://xtermjs.org/docs/api/terminal/classes/terminal/):
  terminal input, paste and output parsing events.
- `apps/desktop/src-tauri/src/terminal.rs`: raw PTY writes and startup CR.
- `apps/desktop/src/lib/handover.ts`: paste framing without Enter.
- [Codex configuration](https://learn.chatgpt.com/docs/config-file/config-reference)
  and [Claude permissions](https://code.claude.com/docs/en/permission-modes): host
  modes that can change what the interactive terminal is waiting for.
