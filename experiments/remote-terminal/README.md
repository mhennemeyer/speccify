# Remote terminal spike (Spec 062)

Throwaway prototype, not part of the product, the Cargo workspace, a release or
the website. It answers one question: can the agent terminal that lives inside
the Tauri app run in a Docker container and be operated from a browser, with the
person's own Claude or Codex login?

Findings live in `.agent/specs/062-spike-container-terminal-im-browser/SPEC.md`.
Take findings from here, not files.

## Run

```sh
./run.sh up        # build image, start container, print http://localhost:8791/#token=…
./run.sh restart   # restart the container only
./run.sh down      # remove the container, keep the volumes (logins, sessions on disk)
./run.sh wipe      # remove container and volumes
SPIKE_RING_BYTES=4096 ./run.sh up   # provoke a truncated ring-buffer replay
```

The port is published on `127.0.0.1` only. The token is generated once into
`.spike-token` (ignored). Open the printed URL; the page keeps the token in
`sessionStorage` and drops it from the address bar.

## What is in the box

- `server/` — Rust, `portable-pty` + axum. The server hands out the session id,
  keeps the PTY alive without viewers, and replays on attach: either the raw
  byte ring buffer or the screen state of a headless `vt100` parser.
- `web/index.html` — xterm.js page: attach/detach, replay kind, bracketed-paste
  handover, Shift+Enter as CSI-u, OSC 8 links, OSC 9/52/777, bell.
- `Dockerfile` — Node base image with `claude` and `codex` installed unmodified
  from npm, unprivileged user, home and `/workspace` as volumes. No credentials
  in the image; the server never reads, copies or sets provider credentials.

## Human checklist

1. "Neue Sitzung", then `claude`. Pick "Claude account with subscription". Click
   the login URL (any of its lines) or press `c` and paste it into a browser
   tab. Paste the code at `Paste code here if prompted`. `/status` shows the plan.
2. Start a longer request, close the tab, wait 30 s, reopen the printed URL and
   pick the session from the list. Try both replay kinds.
3. `./run.sh restart`, new session, `claude --resume`: login and conversation
   must still be there.
4. `codex login --device-auth`, then the same restart and `codex resume`.
5. After a login: `curl -H "Authorization: Bearer $(./run.sh token)"
   localhost:8791/api/sessions/<id>/buffer | less` — look for what should not
   be kept (pasted code, tokens).
