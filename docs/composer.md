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
| **Palette** (links) | Alle Registry-Specs. **Ziehen** legt die Komponente dort ab, wo man sie fallen lässt (Canvas = Top-Level, Slot-Zone = in den Slot); „+ als Kind" tut dasselbe per Klick, „öffnen" lädt eine Spec in den Editor. Selbst gespeicherte Composites erscheinen sofort — **Komposition ist rekursiv**. |
| **Canvas** (Mitte) | Rendert den **generierten Mock** — dieselben `*.mock.tsx`-Dateien, die `speccify mock` schreibt (im Browser kompiliert, siehe unten). Zwei Modi: *Bearbeiten* zeigt den Baum mit Editor-Rahmen (Klick selektiert, Event-Chips des Mocks feuern die Wiring-Simulation), *Vorschau* rendert die Mock-Komponente des Dokuments selbst — dort verdrahtet der generierte Code, nicht der Composer. **Slot-Zonen**: Komponenten mit Slots zeigen pro Slot eine Zone *an der Stelle, an der der Mock den Slot rendert* — Komponenten hineinziehen, oder anklicken (macht sie zum Einfüge-Ziel für „+ als Kind"). Bestehende Knoten hängt man am Griff (⠿ in der Kopfzeile) um: in eine andere Slot-Zone oder zurück auf den Canvas-Hintergrund (= Top-Level), immer samt Teilbaum. |
| **Inspector** (rechts) | *Knoten*: typisierte Prop-Editoren (Enum-Dropdowns etc.), Reihenfolge, **Platzierung** (Knoten samt Teilbaum zwischen Top-Level und Slots umhängen), Entfernen (entfernt den ganzen Teilbaum inkl. Wiring-Cleanup). *Verdrahtung*: Regeln ansehen/löschen + Formular mit API-getriebenen Dropdowns. *API*: eigene Events/Props (inkl. `map_to`-Forwarding). *Spec*: Name/Version/Kind/Summary. |
| **YAML** (unten links) | Live generierte Spec-YAML; direkt editierbar („übernehmen" lädt sie zurück ins Modell). Validierungs-Issues erscheinen hier. |
| **Event-Log** (unten rechts) | Trigger, `set`-Effekte und emittierte eigene Events der Simulation. |

**Validieren** prüft Schema v1 + Kompositions-Typprüfung serverseitig;
**Speichern** schreibt die Spec in die lokale Registry
(`registry-fixtures/<scope>/<name>/<version>/spec.speccify.yaml`).

**Undo/Redo**: jede Modell-Änderung (Kind hinzufügen/entfernen/umhängen,
Props, Wiring, YAML-übernehmen, Neu/Öffnen) ist rückrollbar — Buttons in der
Topbar oder `⌘Z`/`Ctrl+Z` bzw. `⇧⌘Z`/`Shift+Ctrl+Z`. Schnelles Tippen im
Prop-Editor wird zu einem Schritt zusammengefasst; in Eingabefeldern gewinnt
das native Text-Undo.

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
# Mock-Closure einer gespeicherten Spec
curl -s -X POST localhost:8000/api/v1/mock \
  -d '{"spec_id": "@org/search-bar"}' -H 'content-type: application/json' | jq '.files | keys'
# Mock-Closure eines ungespeicherten Entwurfs — genau das, was der Canvas rendert
curl -s -X POST localhost:8000/api/v1/mock/draft \
  -d '{"spec_yaml": "…"}' -H 'content-type: application/json' | jq '{entry, files: (.files | keys)}'
# Discovery: Specs in den konfigurierten Index-Repos finden (P5)
curl -s 'localhost:8000/api/v1/index?q=rating' | jq '.hits[].source'
```

Kompositions-Kinder dürfen auch Git-Quellen sein (`git+<url>[#<pfad>]`) —
Validierung und Mock-Rendering lösen sie über dieselbe Registry-Fassade auf wie
die CLI. Details: [`git-sources.md`](./git-sources.md).

## Architektur & Tauri-2-Zielbild

- **Frontend**: Vite-React-SPA unter `apps/composer/` — statischer Export mit
  relativen Pfaden (`base: "./"`), keine SSR-/Server-Features. Genau die Form,
  die eine Tauri-2-Shell später direkt lädt.
- **Backend-Grenze**: ausschließlich HTTP (`/api/v1/...`). Im Dev proxied Vite
  auf `:8000`; `VITE_API_BASE` erlaubt der Tauri-Shell, auf einen Sidecar zu
  zeigen. CORS ist für `tauri://localhost` vorbereitet.
- **Drag & Drop in der Desktop-App**: Das Composer-Fenster wird mit
  `disable_drag_drop_handler()` gebaut (`apps/desktop/src-tauri/src/lib.rs`) —
  sonst fängt Tauris OS-Datei-Drop-Handler die HTML5-Drag-Events ab und im
  Canvas ließe sich nichts ablegen.
- **Canvas-Rendering (Mock-Bundle)**: Der Canvas holt bei jeder Änderung die
  Mock-Closure des aktuellen Dokuments (`POST /api/v1/mock/draft`, debounced)
  und kompiliert sie im Browser (`sucrase`: TSX → CommonJS, Mini-`require` für
  die Closure-Importe, `"react"` gebunden an die Composer-Instanz — siehe
  `apps/composer/src/mockRuntime.ts`). Gerendert wird damit **der generierte
  Code**, nicht eine zweite Interpretation des Contracts: keine Drift zwischen
  Vorschau und `speccify mock`-Output. Kein LLM, kein Netz über diesen einen
  Endpoint hinaus; Tauri-safe (CSP der Desktop-App erlaubt die Auswertung).
  Der Composer steuert nur bei, was er als Editor weiß: gemergte Props,
  Event-Callbacks und Slot-Inhalte. Schlägt der Bau eines Zwischenstands fehl,
  bleibt die letzte lauffähige Closure stehen und der Canvas markiert sie als
  „Mock veraltet".
- **Zustand = Spec-Datei**: Der Composer hält keinen eigenen Speicher; Laden
  und Speichern gehen gegen die Registry auf Disk. Git ist die Historie.

## UI-Smoke (Playwright)

`pnpm run composer:e2e` fährt Backend (FastAPI gegen eine **Wegwerf-Kopie**
der `registry-fixtures/`, Port 8788) und Vite (Port 5199) hoch und spielt den
kompletten Flow durch die echte Oberfläche durch: Composite anlegen → Kind +
Prop → eigenes Event + Wiring-Regel → Simulation → validieren → speichern →
YAML-Round-Trip; dazu Undo/Redo und Slot-Befüllen. Läuft in CI als eigener
Job (`apps/composer ui smoke`). Die Ports kollidieren bewusst nicht mit
`dev-up.sh`. Browser einmalig installieren:
`pnpm --filter speccify-composer exec playwright install chromium`.

## Grenzen des MVP (bewusst)

- Drag & Drop hängt Knoten um und fügt ein, sortiert aber nicht: die
  Reihenfolge innerhalb der Geschwister ändert man im Inspector (↑/↓).
- Routen für `kind: app` gibt es (Phase P4, siehe [`app-builds.md`](./app-builds.md)), der Composer editiert sie aber noch nicht visuell — sie stehen im YAML.
- Wiring-Quellen sind `payload.*`, `props.*` und Literale — keine Expressions.
- Im Bearbeiten-Modus simuliert der Composer die Verdrahtung zwischen den
  einzeln gerenderten Knoten selbst (`simulate.ts`, gleiche Semantik wie der
  Generator); die *echte* generierte Verdrahtung läuft im Vorschau-Modus.
- Kein Typecheck im Browser: `sucrase` transpiliert nur Syntax. Typfehler
  fängt weiterhin die Conformance-Stufe (`tsc --noEmit`).

## Cross-Referenzen

- Hands-on-Einstieg: [`composer-tristate-walkthrough.md`](./composer-tristate-walkthrough.md)
- API-Vertrag & Mocks: [`component-api-and-mocks.md`](./component-api-and-mocks.md)
- Projekt-Builds: [`app-builds.md`](./app-builds.md)
- Lokaler Gesamt-Workflow: [`local-dev-e2e.md`](./local-dev-e2e.md)
- Roadmap: [`.agent/plans/pivot-open-source-git-composer.md`](../.agent/plans/pivot-open-source-git-composer.md)
