---
title: MCPs
description: Model Context Protocol servers — how agents and apps reach capabilities beyond the file system.
sidebar:
  order: 4
---

**MCP** (Model Context Protocol) is an open standard for connecting an
AI client to external capabilities. An **MCP server** exposes tools —
named operations with JSON-schema'd inputs — and any MCP client (a
terminal agent, an IDE, an app) can list and call them. Where the
[tools](/fundamentals/tools/) of this workflow are small local
programs with a stdin/stdout contract, MCP is the wire protocol for
capabilities that live in a *running process*: a database, a browser,
an execution service.

## In this workflow

The project file `.mcp.json` declares which MCP servers a project
uses. It sits in the repository root, next to `.agent/`, and the agent
reads it like any other project file:

```json
{
  "mcpServers": {
    "exec": {
      "type": "http",
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

The same rule applies here as to all `.agent/` configuration: **never
put secrets in this file** — it is part of the repository. Tokens stay
in a keychain or come in as environment references like
`${MY_TOKEN}`.

## A real example: the exec server

The Speccify project ships a local **exec MCP server** for clients
that must not spawn processes themselves. The Speccify app doesn't
need it — it [runs actions natively](/app/actions/) — but the
terminal agent and any sandboxed third-party client reach the same
commands through the same server.

```text
 terminal agent ──MCP──▶ ┌─────────────────┐
                         │  exec server    │──▶ runs commands in the
 sandboxed app ──MCP──▶  │  (local, :8765) │    project root, allowlisted
                         └─────────────────┘
```

The server exposes three tools:

- `run_command` — run one command in the project root,
- `run_action` — run a named project action (defined in
  `.agent/actions.json`),
- `list_actions` — enumerate those actions.

Sandboxed apps must not spawn arbitrary processes, and agents should
not run unreviewed commands either — the exec server solves both with
one mechanism: an **allowlist** (`.agent/exec-allowlist.json`). A
command that is not covered by an allowed pattern is not executed; it
is parked as a pending request that the owner confirms once (or
permanently) in the Speccify app. The working directory is pinned to
the project root, runs have a timeout, and output streams live to the
client.

The pattern generalizes: an MCP server is a good seam wherever a
capability needs **one implementation, several clients, and a policy
in the middle**. The protocol carries the calls; the server decides
what it is willing to do.
