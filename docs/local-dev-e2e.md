# Lokaler End-to-End-Workflow (Dogfooding)

Dieser Walkthrough fährt **das gesamte Speccify-System lokal** hoch und führt
einmal durch den kompletten Workflow: Market browsen (MIT + proprietär),
über einen Agenten/CLI mit dem System arbeiten und aus einer Spec **echten
Code generieren** (Live-Bedrock).

> Ziel: alles läuft lokal, du kannst im Market deine Specs sehen — sowohl
> `MIT` als auch `Commercial` lizenziert — und tatsächlich Code aus einer Spec
> generieren.

## 0. Voraussetzungen

- `uv` installiert (`brew install uv`), einmal `uv sync` gelaufen.
- `pnpm` installiert (nur für die beiden Web-Frontends nötig).
- Eine `.env` am Repo-Root mit AWS-Bedrock-Credentials für den Live-Codegen:

  ```dotenv
  AWS_ACCESS_KEY_ID=...
  AWS_SECRET_ACCESS_KEY=...
  AWS_REGION=eu-central-1
  ```

  Reine Offline-Nutzung (Replay-Cache) braucht **keine** `.env`.

## 1. Alles mit einem Befehl starten

```bash
./scripts/dev-up.sh
```

Das Skript

1. entversteckt die macOS-Venv-`.pth`-Dateien und setzt `UV_NO_SYNC=1`
   (verhindert, dass `uv run` zwischen Aufrufen die editable-Installs erneut
   versteckt),
2. migriert die Registry-DB,
3. **seedet den Market** mit den fünf Phase-0-Referenz-Specs (`MIT`) und der
   Commercial-Beispiel-Spec `@acme-pro/rating-stars` (`Commercial`),
4. startet alle Services parallel mit Präfix-Logs:

   | Service | URL | Zweck |
   |---|---|---|
   | Registry (Django) | <http://127.0.0.1:8001> | Market/Browse, Login, Tokens |
   | Playground-Backend (FastAPI) | <http://127.0.0.1:8000> | `/api/v1/render`, `/api/v1/specs` |
   | Playground-Frontend (Next.js) | <http://localhost:3000> | Monaco-Editor-Spielwiese |
   | Marketing/Doku (Astro) | <http://localhost:4321> | Landingpage + Doku |

`Ctrl-C` beendet alle Services gemeinsam.

Varianten:

```bash
./scripts/dev-up.sh --no-frontends   # nur Registry + Playground-Backend (kein pnpm/Node)
./scripts/dev-up.sh --no-seed        # Market nicht neu seeden
```

## 2. Market browsen (MIT + proprietär)

Öffne <http://127.0.0.1:8001>. Du siehst alle geseedeten Specs mit einem
**License-Badge**:

- grünes Badge `MIT` für die Open-Source-Referenz-Specs,
- rotes Badge `Commercial` für `@acme-pro/rating-stars`.

Klick auf eine Spec → Detailseite mit Versionen, YAML und Lizenz-Badge.

Der Seed ist idempotent — erneutes `seed_market` überspringt bereits
vorhandene Versionen. Eigene Specs kannst du jederzeit nachlegen:

```bash
uv run python -m speccify_registry.manage seed_market --roots registry-fixtures example-commercial-specs meine-specs
```

(Die Commercial-Beispiel-Spec liegt unter `example-commercial-specs/`; lege
weitere proprietäre Specs einfach als `license: Commercial` dort ab.)

## 3. Mit dem System über einen Agenten/MCP arbeiten

Der MCP-Server (`speccify-mcp`) exponiert die CLI-Operationen für Coding-Agents.
Beispiel-Konfiguration für einen MCP-fähigen Agenten (z. B. Junie/Claude):

```json
{
  "mcpServers": {
    "speccify": {
      "command": "uv",
      "args": ["run", "speccify-mcp"],
      "cwd": "/ABSOLUTER/PFAD/zu/speccify"
    }
  }
}
```

Damit kann der Agent `lint`, `lock`, `pull`, `verify`, `publish`, `yank` etc.
aufrufen. Für den Registry-Zugriff vorher lokal einloggen:

```bash
uv run speccify login --registry http://127.0.0.1:8001
uv run speccify whoami --registry http://127.0.0.1:8001
```

## 4. Aus einer Spec echten Code generieren

### Offline (deterministisch, Replay-Cache)

```bash
cd example-project
uv run speccify lock
uv run speccify pull            # --offline ist Default
```

Materialisiert den generierten Code nach `speccify_generated/<target>/`.
Nutzt nur den eingecheckten Replay-Cache — kein API-Verbrauch.

### Live (echte Bedrock-Generierung, auch für neue Specs)

```bash
uv run speccify pull --no-offline
```

Bei einem Cache-Miss holt die CLI eine **Live-Antwort über AWS Bedrock**
(Credentials aus Umgebung / `.env`) und schreibt das Ergebnis in den
Replay-Cache. Damit kannst du auch eine **selbst geschriebene neue Spec**
generieren lassen:

1. Neue `*.speccify.yaml` schreiben (siehe `specs/` als Vorlage).
2. Ins Manifest/Workspace aufnehmen und `uv run speccify lock`.
3. `uv run speccify pull --no-offline` — die erste Generierung geht live,
   danach liegt sie im Cache und ist reproduzierbar.

> Hinweis: Der Live-Pfad ist nicht deterministisch und kostet API-Calls. CI
> ruft `pull`/`verify` immer mit `--offline`; der Live-Pfad wird dort nie
> betreten.

### Über das Playground-Frontend

Öffne <http://localhost:3000>, schreib/füge eine Spec ein und render gegen das
lokale Backend (<http://127.0.0.1:8000>). Die Marketing-Seite
<http://localhost:4321/try-it> bettet das Playground per Iframe ein
(`PUBLIC_PLAYGROUND_URL` zeigt im Dev-Skript auf das lokale Frontend).

## 5. Troubleshooting

- **`No module named 'speccify_registry'` / `'speccify_core'`**: macOS hat die
  editable-`.pth` versteckt. Fix: `./scripts/fix-venv-hidden.sh --deep`. Das
  Dev-Skript macht das automatisch und setzt `UV_NO_SYNC=1`, damit `uv run`
  sie nicht erneut versteckt.
- **Port belegt**: Vorherige `dev-up.sh`-Instanz noch aktiv — beende sie mit
  `Ctrl-C` bzw. kill der `runserver`/`uvicorn`-Prozesse.
- **Live-Codegen schlägt mit Auth-Fehler fehl**: `.env` mit gültigen
  Bedrock-Credentials und passender `AWS_REGION` prüfen.

## Cross-Referenzen

- Conformance/Build-Smoke: [`conformance.md`](./conformance.md)
- Workspaces: [`workspaces.md`](./workspaces.md)
- Deploy der Doku/Landing: [`deploy.md`](./deploy.md)
