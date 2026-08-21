---
name: sandboxed-mac-app-local-exec
description: 'A sandboxed app cannot spawn processes, and the App Store forbids shipping executables
  that add functionality. The way out is to stop trying: the app becomes a pure HTTP client
  to a small local server the user installs and starts themselves — with an allowlist, live
  output over SSE, and a stop button that actually kills the process. Use when targeting macos,
  or when the user mentions sandbox, app-store, exec, sse, streaming, allowlist, mcp or developer-tools.'
license: MIT
compatibility: Requires A sandboxed macOS app and A local helper server the user installs
  separately
metadata:
  speccify.version: 1.0.0
  speccify.scope: speccify
  speccify.platforms: macos
  speccify.uses: '@speccify/mcp-client-streamable-http@^1.0'
---

## Prerequisites

- The audience is developers. For a general-audience app, asking users to install and start a server is not a viable design.
- You control (or can specify) the local server, so the wire contract is yours to define.

## 1 — Understand what is actually forbidden — it is narrower than "no commands"

Two guidelines set the boundary. Apps must be self-contained and

> may not download, install, or execute code which introduces or changes
> features or functionality of the app, including other apps

and Mac App Store apps

> may not download or install standalone apps, kexts, additional code, or
> resources to add functionality.

Read carefully: the prohibition is on **your app** shipping, downloading,
installing or executing code. It is not a prohibition on your app talking
over the network to software the user chose to install.

So the design constraint is precise:

* The app must **not** bundle the helper, must not download it, must not
  install it, and must not spawn it.
* The user installs it (Homebrew, a release download, `cargo install`)
  and starts it themselves.
* The app only ever opens an HTTP connection to `127.0.0.1`.

Be honest about the residual risk: review outcomes are judged case by
case, and an app whose *entire* value is executing arbitrary commands
will attract more scrutiny than one where this is a power-user feature.
Do not put a "Download the server" button in the app — that is the line.

**Verify:** The app binary contains no bundled executable, and nothing in the code path spawns a process (`Process`/`posix_spawn` appear nowhere).

*Source: App Store Review Guidelines — 2.5.2 and 2.4.5(iv) or Apple Developer — App Sandbox.*

## 2 — Speak a real protocol to the helper, not a bespoke one

Covered by the skill `@speccify/mcp-client-streamable-http@^1.0` — follow that one, then continue.

## 3 — Make the server say which project it serves

A local server on a fixed port is indistinguishable from *another* local
server on that port — including yesterday's instance, still running,
still pointed at a different repository. Commands then execute in the
wrong working directory and look like they simply failed.

Have the server report its root in the handshake, in
`serverInfo` of the `initialize` result:

```json
{"serverInfo": {"name": "exec-mcp", "version": "1.0",
                "projectRoot": "/Users/me/Work/project-a"}}
```

The client compares it against the project the window is showing and says
so plainly — "connected, but this server serves *project-a*" is a very
different message from "connected".

Servers that do not send the field are not an error; treat a missing
`projectRoot` as unknown and carry on.

**Verify:** Point the app at a server started for a different folder — the status must say so rather than showing a green light.

*Source: MCP specification 2025-03-26 — Lifecycle (serverInfo in the initialize result).*

## 4 — Put an allowlist between the caller and the shell

The server executes on the user's real machine, outside the sandbox, with
the user's permissions. Anything that can reach the port can run
commands. An allowlist is not a nicety.

What works in practice:

* Store patterns in the project, not in the app:
  `.agent/exec-allowlist.json`, an array of
  `{"pattern": "npm test", "permanent": true}`.
* Match on **token prefix**, not substring. Tokenise both sides (shell
  lexing) and compare element by element: `npm test` then allows
  `npm test --watch=false`, but not `npm testfoo` and not `npm install`.
  A substring match would allow `rm -rf /; npm test`.
* `permanent: false` means a one-time grant, removed after a matching run.
* A rejected command is **not** just an error — append it to
  `.agent/exec-pending.json`, deduplicated by command text, so the user
  can approve it in the UI afterwards. That turns "denied" into a
  one-click workflow instead of a dead end.
* Fix the working directory to the project root. Never let the caller
  choose it.
* Give every run a timeout (600 s is a reasonable ceiling) and kill the
  process when it expires.

**Verify:** A command not on the list is refused, appears in the pending file exactly once even if attempted three times, and runs after approval.

## 5 — Stream output line by line, over SSE

A build that prints nothing for four minutes is indistinguishable from a
hung one. Add a streaming endpoint next to the JSON-RPC one — a plain
`POST …/stream` with `{"command": "...", "project": "..."}`, answering
`text/event-stream`:

```
data: {"type":"line","text":"compiling foo.rs"}

data: {"type":"exit","exit_code":0,"duration_ms":8123}
```

Details that matter:

* **Merge stderr into stdout.** Two separate streams arrive interleaved
  in the wrong order and the output stops matching what the same command
  prints in a terminal.
* Flush after every event, or the whole point is lost to buffering.
* Send one terminal `exit` event, always — including for failures that
  happen *before* execution (not allowlisted, program not found, bad
  project), with `exit_code: null` and an `error` field. A client that
  waits for `exit` must never wait forever.
* Clients skip unknown event types. That lets you add events later
  without breaking older clients; renaming one breaks them all.

**Verify:** Run a command that prints slowly — the first line appears in the UI within a second, not at the end.

*Source: HTML Standard — Server-sent events.*

## 6 — Make disconnect kill the process

The stop button is the reason this is worth building at all, and it is
the part most implementations get wrong: they close the stream and leave
the child running to completion, or worse, leave a zombie.

Bind the process lifetime to the connection. When the client disconnects,
**kill the child and reap it** — immediately, not at the next timeout
tick.

On the client side, that means "stop" is just closing the connection;
there is no separate cancel call to get out of sync.

**Verify:** Start a long command, hit stop, then check `ps` — no child process and no zombie remains.

## 7 — Cap what goes into an agent, never what goes into the window

If an agent can also call this, it will call the JSON-RPC tool and put
the output into a model context. That output needs a cap (20k characters
is a workable default) or one `npm ci` blows the context budget.

The **stream** to the app window must stay uncapped. A human scrolling a
build log wants the end of it, and that is exactly what a naive cap
throws away.

Two consumers, two budgets. Conflating them means either a truncated log
in the UI or a blown context — and both look like bugs elsewhere.

**Verify:** A command producing 100k of output is complete in the window and truncated in the tool result.

## 8 — Degrade instead of failing when the helper is absent

The server is not running most of the time. That is the normal state, not
an error:

* Probe periodically (every 15 s is unobtrusive) and show a plain
  connected/disconnected indicator.
* Put the exact start command in the UI, copyable. "Cannot connect to
  the exec server" without the command is a support ticket.
* If the streaming endpoint does not answer `200`, fall back to the
  plain tool call — you lose live output, not the feature.
* Features that need the helper are disabled with a reason, not hidden.

**Verify:** With no server running, the app shows a disconnected state and a copyable start command, and nothing throws.

## 9 — Close the two holes every local server has

A server on localhost is reachable from any web page the user visits.
The MCP specification is explicit about both mitigations:

* **Validate the `Origin` header** on every request, or a website can
  drive the server through DNS rebinding.
* **Bind to `127.0.0.1`**, never `0.0.0.0`, or everyone on the coffee
  shop network can run commands on the user's machine.

Both are one-line checks and neither is optional for something whose
purpose is executing shell commands.

**Verify:** `lsof -iTCP -sTCP:LISTEN | grep <port>` shows 127.0.0.1, and a request with a foreign Origin is rejected.

*Source: MCP specification 2025-03-26 — Transports (security requirements for local servers).*

## Pitfalls

- Shipping the helper inside the app bundle "just for convenience". That is precisely what guideline 2.4.5(iv) forbids, and it converts a defensible design into a rejection.
- Substring matching in the allowlist. `npm test` must not allow `rm -rf /; npm test`. Tokenise and compare prefixes.
- Closing the SSE stream without killing the child. The user presses stop, the UI goes quiet, and the build keeps running — sometimes holding a lock that makes the next attempt fail mysteriously.
- Separate stdout and stderr streams. The output stops matching what the terminal shows, and every bug report becomes unreproducible.
- One output cap for both the UI and the agent. Whichever number you pick is wrong for one of them.
- Assuming the server on the expected port serves your project. Check `serverInfo.projectRoot`; the alternative is commands silently running in the wrong repository.

## Acceptance

- Given A sandboxed, signed app and a helper server the user started for this project, when The user runs an allowlisted command and presses stop midway, then Output streams live, the child process dies immediately, and no process is left behind.
- Given The helper is not running, when The user opens the actions tab, then The UI shows a disconnected state with a copyable start command, and nothing errors.

## Sources

- [App Store Review Guidelines — 2.5.2 and 2.4.5(iv)](https://developer.apple.com/app-store/review/guidelines/) — retrieved 2026-08-06
  2.5.2 - apps may not download, install or execute code that introduces or changes features. 2.4.5(iv) - Mac App Store apps may not download or install standalone apps, kexts or additional code.
- [Apple Developer — App Sandbox](https://developer.apple.com/documentation/security/app-sandbox) — retrieved 2026-08-06
- [MCP specification 2025-03-26 — Transports (security requirements for local servers)](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports) — retrieved 2026-08-06
  Servers MUST validate Origin; local servers SHOULD bind to 127.0.0.1 rather than 0.0.0.0.
- [MCP specification 2025-03-26 — Lifecycle (serverInfo in the initialize result)](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle) — retrieved 2026-08-06
- [HTML Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html) — retrieved 2026-08-06

## Tools

- [verify-stream](tools/verify-stream/TOOL.md) — the contract; `reference.sh` beside it is one
  implementation for macOS. Write your own where that one does not run.
