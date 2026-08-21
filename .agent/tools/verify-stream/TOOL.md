---
name: verify-stream
description: Smoke-tests a local exec helper over HTTP — loopback-only binding,
  foreign Origin rejected, output streamed rather than buffered, a terminal exit
  event even when the command cannot start, and the child killed when the
  client disconnects. Tests the wire, not the client.
inputs:
  type: object
  additionalProperties: false
  properties:
    base_url:
      type: string
      default: http://127.0.0.1:8765
      description: Where the helper listens. The port is taken from here.
    project:
      type: string
      description: Project root sent with each command; defaults to the
        current directory.
outputs:
  type: object
  required: [ok, checks]
  properties:
    ok: {type: boolean}
    checks:
      type: array
      description: One entry per guard rail, in the order they ran.
      items:
        type: object
        required: [name, passed]
        properties:
          name:
            type: string
            enum: [loopback-only, origin-rejected, streams-early, exit-on-start-failure, kill-on-disconnect]
          passed: {type: boolean}
          detail: {type: string}
effects: opens HTTP connections to `base_url`; starts short-lived commands
  (`sh -c 'echo…; sleep…'`) through the helper and kills them; writes nothing
  outside a temp file
requires: curl
runtime: any
---

## Behaviour

Five checks, each independent, all reported (do not stop at the first
failure — the report is what gets pasted into the bug):

* **loopback-only** — something listens on the port and it is bound to
  `127.0.0.1`, not `0.0.0.0`/`*`. Skip with `passed: true` and a `detail`
  when the platform offers no way to list listeners.
* **origin-rejected** — a POST with `Origin: https://evil.example` must not
  return 200 (DNS-rebinding guard).
* **streams-early** — a command that prints, sleeps a second and prints again
  must produce a `"type":"line"` event within 500 ms, and a `"type":"exit"`
  event at the end.
* **exit-on-start-failure** — a command that cannot be started still ends the
  stream with an exit event; otherwise clients wait forever.
* **kill-on-disconnect** — start a `sleep 120` with a unique marker, drop the
  connection, and confirm that no process with that marker survives. Clean up
  the child yourself if it does, then report the failure.

`ok` is the conjunction of all `passed`.

## Examples

### a helper that does everything right
input: {"base_url": "http://127.0.0.1:8765"}
output: {"ok": true, "checks": [{"name": "loopback-only", "passed": true}, {"name": "origin-rejected", "passed": true, "detail": "HTTP 403"}, {"name": "streams-early", "passed": true}, {"name": "exit-on-start-failure", "passed": true}, {"name": "kill-on-disconnect", "passed": true}]}

### output is buffered until the command ends
input: {}
output: {"ok": false, "checks": [{"name": "loopback-only", "passed": true}, {"name": "origin-rejected", "passed": true, "detail": "HTTP 403"}, {"name": "streams-early", "passed": false, "detail": "no line event within 500ms"}, {"name": "exit-on-start-failure", "passed": true}, {"name": "kill-on-disconnect", "passed": true}]}
