---
title: Installation
description: Speccify lokal aufsetzen — CLI, MCP-Server und Composer.
---

Speccify ist ein Python-Workspace (CLI, MCP-Server, Web-Backend) plus zwei
Node-Apps (Composer, Doku-Site). Alles ist MIT-lizenziert; es gibt keinen
Account und keinen Hosted-Service.

## Voraussetzungen

| Werkzeug | Wofür |
|---|---|
| [uv](https://docs.astral.sh/uv/) | Python-Workspace (CLI, MCP, Backend) |
| Node ≥ 22 + pnpm | Composer, Doku-Site, generierte Projekte |
| `git` | Specs aus Git-Repos beziehen (Phase P5) |

## Einrichten

```bash
git clone <repo-url> speccify && cd speccify
uv sync --all-packages
pnpm install --frozen-lockfile
```

Prüfen, ob alles steht:

```bash
uv run speccify --help
uv run speccify lint specs/*.yaml
uv run pytest -q
```

## Die drei Wege

Jede Fähigkeit gibt es dreimal — als CLI, als MCP-Tool und über HTTP. Alle
drei liefern **byte-identische** Dateien; das ist per Cross-Consistency-Test
festgenagelt.

```bash
# CLI
uv run speccify mock @org/search-bar --registry ./registry-fixtures

# MCP-Server (stdio) für Coding-Agents
uv run speccify-mcp --project .

# Web-Backend + visueller Composer
./scripts/dev-up.sh          # Backend :8000, Composer :5173
```

Als Desktop-App: `./scripts/dev.sh --release` baut `Speccify.app`
(siehe [Download](/download/)).

## Weiter

- [Deine erste Spec](/getting-started/first-spec/)
- [Spec-Format](/concepts/spec-format/)
- [Visueller Composer](/composer/)
