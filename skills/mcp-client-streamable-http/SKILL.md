---
name: mcp-client-streamable-http
description: 'Build a Model Context Protocol client that talks Streamable HTTP: handshake,
  session id, tool calls, and the two failure modes that only show up in practice — a server
  that restarts underneath you, and a response that arrives as an SSE stream instead of JSON.
  Use when the user mentions mcp, streamable-http, json-rpc, sse, session, agents or tools.'
license: MIT
compatibility: Requires An HTTP client with header access and JSON parsing
metadata:
  speccify.version: 1.0.0
  speccify.scope: speccify
---

## Prerequisites

- An MCP server you can reach over HTTP (a local one on 127.0.0.1 is fine).
- A way to fake the transport in tests — you do not want the network in your unit tests.

## 1 — Talk to exactly one endpoint, over POST

Streamable HTTP is not a REST API. The server exposes **one** path (the
*MCP endpoint*, e.g. `https://host/mcp`) that accepts both POST and GET,
and every JSON-RPC message the client sends is a **new HTTP POST** to it.

Two headers are not optional:

```
Content-Type: application/json
Accept: application/json, text/event-stream
```

The `Accept` header is a MUST in the spec, and it is not decoration: the
server chooses per request whether to answer with a single JSON object or
to open an SSE stream. Send only `application/json` and a
spec-conforming server is entitled to refuse you.

**Verify:** A request without the SSE type in `Accept` is the only difference between a working and a failing call — try it once, so you have seen it.

*Source: MCP specification 2025-03-26 — Transports (Streamable HTTP).*

## 2 — Do the handshake lazily, and finish it

The order is fixed: `initialize` request → server's `InitializeResult` →
`notifications/initialized` from the client. Only then does normal
operation begin.

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{
  "protocolVersion":"2025-03-26",
  "capabilities":{},
  "clientInfo":{"name":"YourApp","version":"1.0"}}}
```

Three things people get wrong:

* **The `initialized` notification is skipped.** It is a notification, so
  nothing fails loudly — the server just never leaves the initialization
  phase and may withhold requests it would otherwise send.
* **`initialize` is put in a JSON-RPC batch.** The spec forbids it.
* **The handshake runs eagerly at construction.** Do it lazily, on the
  first real call. A client that hits the network the moment it is
  constructed cannot be created in a settings screen, in a test, or for a
  server that is not running yet.

**Verify:** A transport fake records exactly three requests for the first tool call - initialize, notifications/initialized, then the call itself.

*Source: MCP specification 2025-03-26 — Lifecycle.*

## 3 — Round-trip the session id

The server **may** hand out a session by putting `Mcp-Session-Id` on the
HTTP response that carries the `InitializeResult`. If it does, the client
**must** send that header on every subsequent request.

Store it when you see it, on any response — not only on the initialize
response — and attach it to everything afterwards. A server that requires
a session and gets a request without one answers `400`.

The value is opaque: treat it as a string of visible ASCII, never parse it.

**Verify:** The second request in a transport fake carries the same Mcp-Session-Id the first response returned.

*Source: MCP specification 2025-03-26 — Transports (Streamable HTTP).*

## 4 — Treat 404-with-a-session as "start over", not as an error

This is the one that costs a day.

A server may end a session whenever it likes — a restart is the common
case. From then on it answers **every** request carrying that session id
with `404 Not Found`. The spec is explicit about what the client must do:

> When a client receives HTTP 404 in response to a request containing an
> `Mcp-Session-Id`, it **MUST** start a new session by sending a new
> `InitializeRequest` without a session ID attached.

Without this, restarting the server bricks the client until the whole app
is restarted — every call 404s forever, and nothing in the error message
hints at the cause. (Observed exactly this way on 2026-07-14: a
Playwright MCP server was restarted, and every call failed until the
client process itself was restarted.)

Implement it as: on `404` **and** we had a session → drop the session id,
clear the initialized flag, handshake again, replay the request once.
Retry once, not in a loop, or a genuinely missing endpoint becomes an
infinite handshake.

**Verify:** Script a fake transport as handshake -> 404 -> and assert the client performs a second handshake and the retried call succeeds.

*Source: MCP specification 2025-03-26 — Transports (Streamable HTTP).*

## 5 — Accept a plain JSON answer and an SSE stream for the same request

The server decides per request. Branch on the response `Content-Type`:

* `application/json` — a single JSON-RPC object, or an array (a batch).
* `text/event-stream` — a stream of SSE events, each carrying one
  JSON-RPC message.

In the SSE case the response you want may not be the first message:
the server is allowed to send requests and notifications ahead of it.
So collect every message and **select the one whose `id` matches the
request you sent**. Never take "the last message" or "the first one with
a result" — both work in testing and fail against a chatty server.

Give every outgoing request a monotonically increasing id and keep it.

**Verify:** A stream with a notification before the response still resolves to the response - assert on a fixture with interleaved messages.

*Source: MCP specification 2025-03-26 — Transports (Streamable HTTP) or HTML Standard — Server-sent events.*

## 6 — Parse SSE the boring way

You need very little of the SSE standard for MCP, but you need that part
right:

* Events are separated by a **blank line**.
* Within an event, lines starting with `data:` contribute payload; a
  single event may carry **several** `data:` lines, and they are joined
  with `\n` before parsing as JSON.
* Normalise `\r\n` to `\n` first.
* Ignore `event:`, `id:`, `retry:` and comment lines (`:`) unless you
  implement resumption — but do not choke on them.

A parser that assumes one `data:` line per event works until a server
pretty-prints its JSON.

**Verify:** A fixture with a multi-line data event parses into one JSON object, not several failures.

*Source: HTML Standard — Server-sent events.*

## 7 — List and call tools without interpreting them

`tools/list` returns descriptors; keep the `inputSchema` as **raw JSON**
and hand it to whatever consumes it (a model's tool definitions, a UI).
Every time a client re-models that schema into its own types, it loses
fields the server cared about. If a descriptor has no schema, substitute
`{"type":"object"}` rather than dropping the tool.

`tools/call` takes `{"name": ..., "arguments": {...}}` and returns
`{"content": [...], "isError": bool}`. Two rules:

* Join the `text` blocks; ignore block types you do not render, do not
  fail on them.
* **`isError: true` is a result, not a transport failure.** It means the
  tool ran and reported a problem. Pass the text on to whoever asked —
  for an agent, that text is the input it needs to try something else.
  Throwing here turns a recoverable situation into a dead end.

**Verify:** A tools/call answering isError true surfaces the text to the caller instead of raising.

*Source: MCP specification 2025-03-26 — Tools.*

## 8 — Decide — out loud — what you do when versions disagree

The client sends a `protocolVersion` it supports. If the server does not
support it, the server answers with one **it** supports. The spec says
that if the client does not support the server's version, it *SHOULD*
disconnect.

In practice many clients ignore the returned version and keep going,
because the wire shapes they use (`tools/list`, `tools/call`) have been
stable across revisions. That is a legitimate choice — *degrade rather
than block* — but it is a choice, and it belongs in a comment next to the
constant, not in someone's head. Write down which revision you send and
what you do with the answer.

Send the version as a header too (`MCP-Protocol-Version`); newer
revisions expect it and older servers ignore unknown headers.

**Verify:** The protocol version appears in exactly one place in the code, with a comment stating the policy.

*Source: MCP specification 2025-03-26 — Lifecycle.*

## 9 — Put a timeout on every request

The spec asks implementations to time out requests and to send a
cancellation notification rather than waiting forever. The practical
minimum: a per-request timeout on the HTTP call itself, so one hung tool
cannot freeze the caller.

If you also want to be a good citizen, send
`notifications/cancelled` for the request you gave up on — but a timeout
without cancellation still beats no timeout.

**Verify:** A transport that never returns causes a failed call within the timeout, not a hang.

*Source: MCP specification 2025-03-26 — Lifecycle.*

## 10 — If the server is local, check the guard rails from the other side

When you also control (or choose) the server, the spec puts two
requirements on it that protect the machine the client runs on:

* The server **MUST** validate the `Origin` header — otherwise a web page
  the user visits can drive their local MCP server through DNS
  rebinding.
* A local server **SHOULD** bind to `127.0.0.1`, not `0.0.0.0`.

Worth verifying before you point a client at a local server you did not
write. `curl` with a made-up `Origin` is a ten-second check.

**Verify:** curl -H "Origin: https://evil.example" against the local server is rejected, and `lsof -i` shows it bound to 127.0.0.1.

*Source: MCP specification 2025-03-26 — Transports (Streamable HTTP).*

## Pitfalls

- Re-initializing on **every** 404 — including one from a server that simply is not there — turns a typo in the URL into an endless handshake loop. Retry once, and only when a session existed.
- Selecting the JSON-RPC response by position instead of by `id`. It works against a quiet server and breaks the moment one sends progress notifications.
- Doing the handshake in the constructor. It makes the client untestable without the network and unusable in a settings screen where the user has not started the server yet.
- Treating `isError: true` as an exception. It is the tool telling you what went wrong, in text — the most useful thing the call produced.
- Modelling `inputSchema` into your own types. Keep the raw JSON; you are a pipe, not a validator.

## Acceptance

- Given A server that hands out a session id and is then restarted, when The client makes a call with the stale session, then It re-initializes without a session id and the call succeeds, with no user-visible error.
- Given A tools/call whose response arrives as SSE with a notification first, when The client parses the stream, then It returns the response matching the request id.

## Sources

- [MCP specification 2025-03-26 — Transports (Streamable HTTP)](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports) — retrieved 2026-08-06
  Source of the Accept-header rule, the Mcp-Session-Id round-trip, the 404-means-reinitialize MUST, the 202-for-notifications rule and the Origin/localhost security requirements.
- [MCP specification 2025-03-26 — Lifecycle](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle) — retrieved 2026-08-06
  Handshake order, the no-batch rule for initialize, version negotiation and timeout guidance.
- [MCP specification 2025-03-26 — Tools](https://modelcontextprotocol.io/specification/2025-03-26/server/tools) — retrieved 2026-08-06
- [HTML Standard — Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html) — retrieved 2026-08-06
  Event framing, multiple data lines per event, field names.
