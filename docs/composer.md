# Visueller Composer (P3, MVP)

Der Composer ist ein **visueller Spec-Editor**: Komponenten aus der Registry
werden auf einem Canvas zu **Composite-Komponenten oder Apps** komponiert —
gerendert als interaktive Mocks, verdrahtet per typgeprüfter Wiring, gespeichert
als ganz normale `speccify.yaml` (Round-Trip, kein eigenes Dateiformat).

## Starten

```bash
./scripts/dev-up.sh          # Backend :8000 + Composer :5173 (+ Playground/Doku)
# oder einzeln:
uv run speccify-web-backend --host 127.0.0.1 --port 8000
pnpm run composer:dev        # http://localhost:5173
```

## Die Oberfläche

| Bereich | Funktion |
|---|---|
| **Palette** (links) | Alle Registry-Specs. „+ als Kind" fügt eine Komponente in die aktuelle Komposition ein, „öffnen" lädt eine Spec in den Editor. Selbst gespeicherte Composites erscheinen sofort — **Komposition ist rekursiv**. |
| **Canvas** (Mitte) | Jeder Knoten wird als interpretierter Mock gerendert (Titel, aktuelle Props, Event-Chips). Chips feuern die Wiring-Simulation live. Klick selektiert. |
| **Inspector** (rechts) | *Knoten*: typisierte Prop-Editoren (Enum-Dropdowns etc.), Reihenfolge, Entfernen. *Verdrahtung*: Regeln ansehen/löschen + Formular mit API-getriebenen Dropdowns. *API*: eigene Events/Props (inkl. `map_to`-Forwarding). *Spec*: Name/Version/Kind/Summary. |
| **YAML** (unten links) | Live generierte Spec-YAML; direkt editierbar („übernehmen" lädt sie zurück ins Modell). Validierungs-Issues erscheinen hier. |
| **Event-Log** (unten rechts) | Trigger, `set`-Effekte und emittierte eigene Events der Simulation. |

**Validieren** prüft Schema v1 + Kompositions-Typprüfung serverseitig;
**Speichern** schreibt die Spec in die lokale Registry
(`registry-fixtures/<scope>/<name>/<version>/spec.speccify.yaml`).

## Agent-bedienbar (Headless-API)

Jede UI-Aktion existiert als HTTP-Endpoint — Coding-Agents komponieren ohne
Browser (der Vertrag ist per E2E-Test gepinnt:
`apps/web/backend/tests/test_composer_agent_flow.py`):

```bash
# Palette
curl -s localhost:8000/api/v1/specs | jq '.specs[].id'
# Kind-Contract (Props/Events/Slots als JSON, inkl. Enum-Werten)
curl -s localhost:8000/api/v1/specs/org/button | jq '.api'
# Validieren
curl -s -X POST localhost:8000/api/v1/validate \
  -H 'content-type: application/json' \
  -d '{"spec_yaml": "…"}' | jq
# Speichern (Pfad ergibt sich aus id + version)
curl -s -X POST localhost:8000/api/v1/specs \
  -H 'content-type: application/json' \
  -d '{"spec_yaml": "…"}' | jq
# Mock-Closure (auch Canvas-Grundlage)
curl -s -X POST localhost:8000/api/v1/mock \
  -d '{"spec_id": "@org/search-bar"}' -H 'content-type: application/json' | jq '.files | keys'
```

## Architektur & Tauri-2-Zielbild

- **Frontend**: Vite-React-SPA unter `apps/composer/` — statischer Export mit
  relativen Pfaden (`base: "./"`), keine SSR-/Server-Features. Genau die Form,
  die eine Tauri-2-Shell später direkt lädt.
- **Backend-Grenze**: ausschließlich HTTP (`/api/v1/...`). Im Dev proxied Vite
  auf `:8000`; `VITE_API_BASE` erlaubt der Tauri-Shell, auf einen Sidecar zu
  zeigen. CORS ist für `tauri://localhost` vorbereitet.
- **Canvas-Rendering**: Der Canvas interpretiert den **API-Contract als JSON**
  (gleiche Semantik wie die generierten `*.mock.tsx`-Dateien aus
  `speccify mock`) — kein TSX-Compiler im Browser, deterministisch, Tauri-safe.
- **Zustand = Spec-Datei**: Der Composer hält keinen eigenen Speicher; Laden
  und Speichern gehen gegen die Registry auf Disk. Git ist die Historie.

## Grenzen des MVP (bewusst)

- Slots werden angezeigt, aber noch nicht visuell befüllt (Verschachtelung per
  YAML möglich).
- Keine Routen-/Navigations-Semantik für `kind: app` (Phase P4).
- Wiring-Quellen sind `payload.*`, `props.*` und Literale — keine Expressions.
- Kein Playwright-UI-Smoke (nur der headless Agent-Flow-E2E); Kandidat für die
  P3-Verfeinerung nach erstem Rumprobieren.

## Cross-Referenzen

- API-Vertrag & Mocks: [`component-api-and-mocks.md`](./component-api-and-mocks.md)
- Lokaler Gesamt-Workflow: [`local-dev-e2e.md`](./local-dev-e2e.md)
- Roadmap: [`.agent/plans/pivot-open-source-git-composer.md`](../.agent/plans/pivot-open-source-git-composer.md)
