---
title: "Projekt-Builds (`kind: app`, Phase P4)"
description: "Aus einer App-Spec wird ein **komplettes, lauffähiges Projekt**: Vite + React, Router, verdrahtete Screens. Das Scaffold ist deterministisch und ohne LLM; nur die Komponenten kommen wahlweise als Mocks oder als generierte Implementierungen."
---

<!-- AUTOGENERIERT aus docs/ via scripts/sync_docs_to_site.py — nicht von Hand editieren. -->

Aus einer App-Spec wird ein **komplettes, lauffähiges Projekt**: Vite + React,
Router, verdrahtete Screens. Das Scaffold ist deterministisch und ohne LLM;
nur die Komponenten kommen wahlweise als Mocks oder als generierte
Implementierungen.

```bash
uv run speccify build @org/demo-app --registry ./registry-fixtures --out ./demo-app
cd demo-app && pnpm install && pnpm dev
```

## Die App-Spec

Eine App ist eine ganz normale Komposition — **jeder Top-Level-Knoten ist ein
Screen**. Der `app:`-Block sagt nur, unter welchem Pfad welcher Knoten liegt:

```yaml
kind: app
app:
  routes:                       # die erste Route ist die Startroute
    - path: /
      node: login               # Alias aus composition.tree (Top-Level)
      title: Anmelden
    - path: /kontakt
      node: contact
  theme:
    tokens:                     # → CSS-Custom-Properties (--color-primary)
      color_primary: "#0f766e"
  env:                          # → import.meta.env (VITE_API_BASE_URL)
    - name: api_base_url
      default: "http://localhost:8000"

composition:
  uses:
    login: "@org/login-screen@^0.1"
    contact: "@org/contact-form@^0.1"
  tree:
    - node: login
    - node: contact
  wiring:
    - when: login.login_succeeded
      navigate: /kontakt          # dritte Wiring-Aktion neben set/emit
```

**Navigation** ist `navigate: /pfad` — typgeprüft gegen die deklarierten
Routen und nur in `kind: app` erlaubt. Bewusst ohne Parameter, Guards oder
History-Semantik: die Verdrahtungs-Sprache bleibt klein.

Referenz-App: [`registry-fixtures/org/demo-app/0.1.0/spec.speccify.yaml`](../registry-fixtures/org/demo-app/0.1.0/spec.speccify.yaml)
— vier Screens, Navigation und ein Datenfluss über Screens hinweg.

## Was erzeugt wird

| Datei | Inhalt |
|---|---|
| `package.json`, `tsconfig.json`, `vite.config.ts`, `index.html` | Scaffold mit gepinnten Versionen (react 19, vite 6, typescript 5.6) |
| `src/main.tsx` | Mount-Punkt |
| `src/App.tsx` | **Ein Zustandsknoten**: Wiring-State + Route; rendert nur den Screen der aktiven Route, unbekannte Routen sagen das sichtbar |
| `src/router.tsx` | ~40-zeiliger Hash-Router — kein Router-Paket, damit das Projekt mit `react`/`react-dom`/`vite` läuft |
| `src/theme.css` | `app.theme.tokens` als CSS-Variablen |
| `src/env.ts` | `app.env` als typisierter Zugriff auf `import.meta.env` mit Spec-Defaults |
| `src/components/**` | Mocks oder Implementierungen (siehe unten) |

## Mocks oder Implementierungen

`--mocks` (Default) legt die Mock-Closure ab **plus je Screen einen
Re-Export**:

```ts
// src/components/org/SearchBar.tsx
export { default } from "./SearchBar.mock";
export type { SearchBarProps } from "./SearchBar.mock";
```

Das ist der Import-Swap aus dem P2-Vertrag, sichtbar als eine Zeile: Mock und
echte Implementierung erfüllen dieselbe API. `--no-mocks` schreibt stattdessen
die generierten Implementierungen aus dem Replay-Cache an genau diese Stelle;
das Scaffold bleibt byte-identisch.

Die Mock-Dateien sind byte-identisch zu dem, was `speccify mock` schreibt — es
gibt weiterhin genau einen Mock-Pfad.

**Eigenheit gemockter Builds**: Event-Payloads eines Mocks kommen aus
gleichnamigen Props. Ein Datenfluss ist im gemockten Build deshalb nur
sichtbar, wenn seine Quelle eine statische Prop ist.

## Drei Wege, ein Ergebnis

| Weg | Aufruf |
|---|---|
| CLI | `speccify build @org/demo-app [--mocks/--no-mocks]` |
| MCP | Tool `build` (`spec_ref`, `out_dir`, `registry_path?`, `target?`, `mocks?`) |
| Web | `POST /api/v1/build` mit `{spec_id, version?, target?}` (immer Mocks) |

Alle drei liefern byte-identische Dateien (Cross-Consistency-Test
`apps/web/backend/tests/test_build_route.py`). Implementierungs-Builds laufen
über CLI/MCP — das Web-Backend hat weder Cache-Flags noch LLM-Zugang im
Vertrag.

## Verifikation

- **Unit** (Standard-Suite): Scaffold-Inhalte, Wiring, Determinismus,
  Byte-Gleichheit zur Mock-Closure, Adapter-Symmetrie.
- **Echter Build** (`pytest -m app_build`, eigener CI-Job): `speccify build`
  → `tsc --noEmit` → `vite build` → `dist/` ausliefern → Playwright spielt die
  App durch (Startroute, Navigation per Event, Datenfluss über Screens,
  unbekannte Route, keine Page-Errors). Wie Conformance und Visual-Regression
  bewusst nicht in der Standard-Suite: externe Toolchains, deutlich langsamer.

## Grenzen (bewusst)

- Nur Target `react`.
- Routen ohne Parameter/Guards; kein verschachteltes Routing.
- Der Composer editiert `app:`-Routen noch nicht visuell — sie stehen im YAML.

## Cross-Referenzen

- API-Vertrag & Mocks: [`component-api-and-mocks.md`](/concepts/api-and-mocks/)
- Visueller Composer: [`composer.md`](/composer/)
- Roadmap: [`.agent/plans/archive/pivot-open-source-git-composer.md`](../.agent/plans/archive/pivot-open-source-git-composer.md)
