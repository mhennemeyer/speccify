# Reference: what the two response shapes look like on the wire

Compare your parser against these. Both are valid answers to the *same*
`tools/call` request (`id: 4`).

## Plain JSON

```http
HTTP/1.1 200 OK
Content-Type: application/json
Mcp-Session-Id: 1868a90c-...

{"jsonrpc":"2.0","id":4,"result":{"content":[{"type":"text","text":"ok"}],"isError":false}}
```

## SSE, with a notification arriving first

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache

event: message
data: {"jsonrpc":"2.0","method":"notifications/progress","params":{"progress":1}}

id: 42
data: {"jsonrpc":"2.0","id":4,"result":{"content":[{"type":"text",
data: "text":"ok"}],"isError":false}}

```

Three things this fixture is designed to break:

1. **Taking the first message.** It is a notification, not your response.
   Select by `id == 4`.
2. **Assuming one `data:` line per event.** The second event's payload is
   split across two lines and must be joined with `\n` before parsing.
3. **Choking on `event:` and `id:` lines.** Skip them; they are not payload.
   (`id:` becomes relevant only if you implement resumption via
   `Last-Event-ID`.)

## Session expiry

```http
HTTP/1.1 404 Not Found
```

If the request that got this carried an `Mcp-Session-Id`, the correct reaction
is not an error to the user: drop the session, send a fresh `initialize`
**without** a session id, then replay the request once.
