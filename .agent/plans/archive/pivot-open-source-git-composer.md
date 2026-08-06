---
lifecycle: done
status: abgeschlossen 2026-08-06 — P1–P5 geliefert, P6.1 Doku-Site + Launch-Vorbereitung; die Produktrichtung wurde danach neu gesetzt (siehe `neuausrichtung-workflow-playbooks.md`). Offene Punkte hier waren nur noch BO-Aktionen (`docs/launch.md`).
sessionId: pivot-open-source-git-composer
---
# Plan: Pivot — Open Source, Git-basierte Registry, Projekt-Builds & visueller Composer

> **Status**: ✅ Abgeschlossen (P1 2026-07-23 → P6.1 2026-08-05). **Abgelöst am 2026-08-06** durch [`neuausrichtung-workflow-playbooks.md`](../neuausrichtung-workflow-playbooks.md): der Composer-/Komponenten-Ansatz hat sich durch den Fortschritt bei Coding-Agents überholt. Was aus diesem Plan trägt (Git-Quellen, Discovery, MCP-Vertrag, Determinismus-Stack, Desktop-App), wird dort weitergeführt.
> **Erstellt**: 2026-07-23
> **Refinement 2026-07-23 (User)**: (1) Aufräumen sofort, Empfehlungen bestätigt (Registry → Archiv-Branch + Löschung). (2) **Visueller Composer so früh wie möglich** — durch Rumprobieren schlauer werden; Git-Datenteilung wird dafür nach hinten geschoben. (3) Der Composer baut nicht nur Apps, sondern auch **Composite-Komponenten** (Komponenten aus Unterkomponenten) — Komposition ist damit ein gemeinsames Schema-Konzept für Komponenten- und App-Specs.
> **Ersetzt perspektivisch**: Teile von [`speccify-plan.md`](./speccify-plan.md) (Open-Core-Prinzip, zentrales Registry als Service, Marketplace, Phasen 5–7 alt)
> **Kontext**: Stand nach Phase 6 (v0.11.0) — CLI/MCP/Web-Playground/Registry/3 Codegen-Targets/Conformance/Workspaces sind produktiv.

---

## Neue Vision in einem Satz

> *„Ein vollständig offenes Ökosystem, in dem Specs über Git-Repos geteilt werden — und aus dem man ein **komplettes Projekt** bauen kann. Jede Spec-Komponente hat eine klare, mockbare API, sodass visuelles Komponieren echter Entwicklungs-Workflow wird, nicht Demo."*

### Die vier Säulen des Umbaus

1. **Open Source statt Open Core** — kein Pro Plan, kein Marketplace, kein Hosted-Service-Geschäftsmodell. Alles MIT. Der Wert entsteht im Ökosystem, nicht hinter einer Paywall.
2. **Git-Repos als Datenteilung** — Specs werden wie Go-Module / SwiftPM-Packages über Git geteilt. Publishing = `git push` + Tag. Kein zentrales Django-Registry mit Auth/2FA/Tokens mehr als Pflichtpfad.
3. **Projekt-Builds aus Specs** — nicht nur einzelne Komponenten generieren, sondern ein komplettes, lauffähiges Projekt (`kind: app`), das Komponenten komponiert und verdrahtet.
4. **Klare API + Mockbarkeit pro Komponente** — die Spec definiert einen formalen API-Vertrag, aus dem deterministisch (ohne LLM) Mocks generierbar sind. Das ist die technische Grundlage für einen **visuellen Composer**: Komponieren mit echten, live gerenderten Mock-Komponenten statt mit Platzhalter-Grafiken — der Unterschied zu allen gescheiterten Visual-Programming-Ansätzen der Vergangenheit.

### Warum Mockbarkeit der Schlüssel zum visuellen Entwickeln ist

Frühere visuelle Ansätze (RAD-Tools, No-Code, Design-to-Code) scheiterten an zwei Punkten: (a) das visuelle Artefakt war nicht die Quelle der Wahrheit (Code-Drift), (b) Komponenten hatten keine formale Schnittstelle, also war Komposition entweder trivial (nur Layout) oder ein Leaky-Abstraction-Sumpf. Speccify dreht das um:

- Die **Spec ist bereits die Quelle der Wahrheit** — der Composer editiert Specs, keinen Code. Kein Round-Trip-Problem.
- Der **API-Vertrag** (Inputs/Outputs/Events/Slots) ist formal und maschinenlesbar → der Composer kann Verdrahtung typgeprüft anbieten (Event `pressed` → Input `visible` nur wenn Typen passen).
- **Mocks sind deterministisch aus der API generierbar** → der Composer rendert sofort, ohne LLM-Call, ohne Backend, ohne dass die Komponente „fertig" ist. Implementierung und Komposition entkoppeln sich.

---

## Was sich konkret ändert (Delta zum Ist-Zustand)

| Bereich | Ist (v0.11.0) | Soll |
|---|---|---|
| Lizenz/Modell | Open Core (Format+CLI offen, Hosting/Search als Service geplant) | Alles Open Source (MIT), Community-Governance |
| Distribution | Django-Registry (`registry/`): Publish/Auth/2FA/Tokens/Device-Code | Git-Repos als primäre Quelle; Registry entfällt bzw. schrumpft zu optionalem statischen Index (Discovery) |
| Identität | `@scope/name@semver`, registry-gebundene Scopes | Git-URL-basiert (`github.com/org/repo[/path]@semver`-Stil, Details offen) + Commit-/Tree-Hash-Pin |
| Publishing | `speccify publish` (multipart-Upload, 2FA) | `git tag` + `git push`; `speccify publish` wird zu Tag-/Manifest-Helfer |
| Trust | Bearer-Tokens, argon2, TOTP, sigstore-Slot | Git-Commit-Hashes + optional signierte Tags; Transparenz durch öffentliche Repos |
| Scope | Einzelkomponenten generieren | Komplette Projekte (`kind: app`) mit Komposition & Verdrahtung |
| Spec-API | `inputs`/`events` informell im Schema | Formaler API-Vertrag als eigenständiges, versioniertes Artefakt; deterministische Mock-Generierung |
| Visuelles Tooling | „Phase 5+, nach echter Nutzung" (geparkt) | Visueller Composer wird Kern-Roadmap-Ziel (auf Mock-Fundament) |
| `example-commercial-specs/` | Beispiel für bezahlte Specs | Entfällt (wird normales OSS-Beispiel oder gelöscht) |

### Was bleibt (bewusst erhalten)

- **Determinismus-Stack**: MVS-Resolver, Lockfile mit Spec- + Output-Hashes + Generator-Pin, Replay-Cache. Das ist der Kern und wird nur auf Git-Quellen umgestellt, nicht ersetzt.
- **Core-Architektur**: Resolver/Codegen in `core/`, CLI/MCP/Web als dünne Adapter, Cross-Consistency-Tests (byte-identisch über alle Pfade).
- **Conformance + Visual Regression**: bleibt der Qualitäts-Vertrag pro Target — wird um Mock-Conformance erweitert.
- **Workspaces**: Cargo-Style Workspaces passen unverändert; ein `kind: app`-Projekt ist natürlicher Workspace-Bewohner.
- **3 Targets** (React, SwiftUI, Angular): bleiben; Projekt-Build startet mit einem Target (Vorschlag: React/Vite, weil Playground-Synergie).

---

## Architektur-Skizze

### 1. Git-basierte Spec-Quellen

Vorbild: **Go-Module + SwiftPM**, nicht npm.

- Ein „Spec-Repo" ist ein Git-Repo mit einer oder mehreren Specs (Konvention: `specs/<name>/spec.speccify.yaml` oder Single-Spec-Repo mit Top-Level-Manifest).
- **Identität**: vollqualifizierte Repo-URL statt Registry-Scope, z. B. `spec://github.com/acme/rating-stars@1.2.0`. Volle URL = kein Dependency-Confusion-Problem, keine Scope-Reservierung nötig.
- **Versionen = Git-Tags** (SemVer, z. B. `v1.2.0` oder `rating-stars/v1.2.0` bei Multi-Spec-Repos — Konvention zu klären).
- **Lockfile pinnt Commit-SHA** (+ weiterhin Spec-Bundle-Hash + Output-Hashes + Generator-Pin). Verify prüft: Tag → Commit → Tree-Hash → Spec-Hash.
- **`GitRegistry`** implementiert das bestehende `Registry`-Protocol (neben `LocalRegistry`/`RemoteRegistry`) — Resolver/Lockfile-Logik bleibt unangetastet. Shallow-Clone/Sparse-Checkout in einen Content-Addressed Cache (`~/.cache/speccify/git/…`).
- **Discovery ohne zentrales Registry**: statisches Index-Repo (à la Homebrew-Taps / Scoop-Buckets): ein Git-Repo mit JSON/YAML-Index aller bekannten Spec-Repos, per PR erweiterbar, von CI validiert. `speccify search` liest den Index (lokal gecacht). Optional später: generierte statische Website aus dem Index (GitHub Pages) — kein Backend.

**Schicksal von `registry/`** (Refinement-Frage, s. u.): Vorschlag — archivieren (Branch/Tag), aus Workspace + CI entfernen. Die 134 Registry-Tests und der Auth-Stack tragen im Git-Modell nichts mehr; ein „Read-Only-Index-Server" wäre über das statische Index-Repo abgedeckt.

### 2. Formaler API-Vertrag + Mocks

- **Spec-Schema v1** (erster expliziter Bump seit v0): `inputs`/`outputs`/`events` werden zu einem formalen `api:`-Block geschärft (Typen, Defaults, Slots/Children, Event-Payloads; State-Machine per D2 nicht in P2, Key `behavior:` reserviert). Der API-Block ist separat hashbar → **API-Version ≠ Spec-Version** (API-Breaking-Change erzwingt Major).
- **Mock-Generator** (deterministisch, templatebasiert, **kein LLM**): aus dem `api:`-Block wird pro Target eine Mock-Implementierung generiert — gleiche Props/Events/Slots, generische aber ansehnliche Darstellung (Label, Variant-Badge, Event-Logging). `speccify mock <id> --target react`.
- **Vertragsgleichheit**: Mock und echte (LLM-generierte) Implementierung erfüllen dieselbe API → austauschbar per Import-Swap. Conformance-Suite bekommt eine Stufe „API-Conformance" (Props/Events stimmen), die für Mock UND echte Implementierung läuft.
- Nutzen sofort: Projekte sind baubar/testbar, bevor alle Komponenten „echt" generiert sind; der Composer rendert ausschließlich Mocks.

### 3. Projekt-Specs (`kind: app`)

- Neues Spec-Kind `app` (Arbeitsname): komponiert Komponenten zu einem lauffähigen Projekt. Enthält:
  - `uses:` (wie bisher, transitiv resolved),
  - **Struktur**: Screens/Routen und welche Komponente wo sitzt (Baum/Slots),
  - **Verdrahtung**: Event → Handler/Input-Bindung, typgeprüft gegen die API-Verträge,
  - **App-Belange**: Navigation, Theme-Tokens, Env/Config.
- `speccify build --target react` erzeugt ein komplettes Projekt-Scaffold (Vite + Routing + verdrahtete Komponenten). Scaffold ist templatebasiert/deterministisch; nur Komponenten-Implementierungen kommen aus dem (LLM-)Codegen — oder aus Mocks (`--mocks`-Flag).
- **Definition of Done**: eine Beispiel-App (z. B. die vorhandenen 5 Referenz-Specs zu einer kleinen App komponiert) entsteht komplett aus Specs, läuft mit `--mocks` sofort und mit echtem Codegen identisch verdrahtet.

### 4. Visueller Composer

- Web-App (Ausbau von `apps/web/`): Canvas + Komponenten-Palette (aus Index/Workspace) + Property-Panel + Verdrahtungs-Editor.
- Rendert **ausschließlich Mocks** (schnell, deterministisch, kein LLM im Loop).
- **Output ist die App-Spec** (YAML) — der Composer ist ein Spec-Editor mit visueller Oberfläche, kein Codegenerator. Round-Trip: App-Spec laden → visuell editieren → speichern → `speccify build`.
- Verdrahtung typgeprüft gegen API-Verträge; ungültige Verbindungen sind im UI nicht herstellbar.

---

## Phasen (Reihenfolge nach Refinement 2026-07-23: Composer-Fast-Track)

> Jede Phase einzeln shippable und wie bisher mit eigenem Phasen-Plan + Stage 0 (Open Questions) zu starten. **Kürzester Weg zum Composer**: Aufräumen → API/Mocks + Komposition → Composer. Git-Datenteilung und Projekt-Builds folgen, sobald das Rumprobieren im Composer die Konzepte validiert hat.

### Phase P1 — Open-Source-Fundament & Entrümpelung ✅ (2026-07-23)
- Master-Plan überarbeitet: Open-Core-Prinzip, Marketplace, „Hosting als Service" gestrichen; neue Vision verankert.
- `example-commercial-specs/` entfernt.
- Registry-Rückbau umgesetzt: `registry/` (Django-Backend), CLI `login`/`whoami`/`publish`/`yank` + Credentials, MCP-Tools `publish`/`yank` entfernt; Archiv-Branch `archive/pre-oss-pivot-registry` behält den Stand. CI/Docs/Scripts bereinigt.
- OSS-Hygiene: `CONTRIBUTING.md`, Code of Conduct, Issue-Templates.

### Phase P2 — API-Vertrag, Komposition & Mock-Generator (Composer-Fundament)

> **Aktiver Phasen-Plan (2026-07-23):** [`phase-p2-api-composition-mocks.md`](./phase-p2-api-composition-mocks.md) — Entscheidungen D1–D6 dort dokumentiert (per User-Delegation).

- Spec-Schema v1 (erster Bump seit dem unversionierten v0) mit formalem `api:`-Block (Typen, Defaults, **Slots/Children**, Event-Payloads); Migrations-Lint für bestehende Specs.
- **`composition:`-Block als gemeinsames Konzept**: eine Komponente kann aus Unterkomponenten komponiert sein (Baum + Slot-Belegung + Event→Input-Verdrahtung, typgeprüft gegen die API-Verträge der Kinder). Derselbe Block trägt später `kind: app` — Apps sind Top-Level-Kompositionen plus Routen/Env.
- Deterministischer Mock-Codegen für React (kein LLM); `speccify mock <id> --target react`. Composite-Komponenten rendern als Mock-Baum ihrer Kinder.
- API-Conformance-Testsuite (läuft gegen Mock und echte Implementierung).
- 5 Referenz-Specs auf Spec-Schema v1 heben; neue Referenz-Specs `@org/text-input` (Leaf) + `@org/search-bar` (Composite aus text-input + button).

### Phase P3 — Visueller Composer (MVP)

> **✅ MVP geliefert (2026-07-24):** `apps/composer/` (Vite-React-SPA, statisch exportierbar, `base: "./"`) + Composer-Backend-API (`GET /api/v1/specs/{scope}/{name}`, `POST /api/v1/validate`, `POST /api/v1/specs`, dazu `POST /api/v1/mock` aus P2). Palette/Canvas (interpretierte Mocks mit Live-Wiring-Simulation)/Inspector (typisierte Prop-Editoren, Verdrahtungs-Formular mit API-Dropdowns, eigene Events/Props inkl. `map_to`)/YAML-Round-Trip/Speichern in die Registry. Agent-Bedienbarkeit per Headless-E2E gepinnt (`test_composer_agent_flow.py`: komponieren → validieren → speichern → mocken, rein über HTTP).
>
> **✅ Verfeinerung Runde 1 (2026-07-24):** visuelles Slot-Befüllen (Slot-Zonen im Canvas als klickbares Einfüge-Ziel, rekursives Mock-Rendering, „Platzierung"-Umhängen im Inspector, Teilbaum-Entfernen mit Wiring-Cleanup), Undo/Redo (`{doc, children}`-Snapshots, Tipp-Koaleszierung, ⌘Z/⇧⌘Z + Topbar-Buttons) und Playwright-UI-Smoke (`apps/composer/e2e/`, 3 Tests gegen echtes Backend mit Wegwerf-Registry, eigener CI-Job).
>
> **✅ Verfeinerung Runde 2 (2026-08-04) — P3 damit abgeschlossen:**
> 1. **Mock-Bundle-Rendering statt Contract-Interpretation** (D7): neuer Endpoint `POST /api/v1/mock/draft` mockt das *ungespeicherte* Dokument (Kinder aus der Registry); `apps/composer/src/mockRuntime.ts` kompiliert die Closure im Browser (sucrase TSX → CJS, Mini-`require` für Closure-Importe, `"react"` an die Composer-Instanz gebunden) und `useMockBundle.ts` hält sie debounced aktuell. Der Canvas rendert damit **den generierten Code** — Prop-Darstellung, Event-Chips, Styles und Slot-Positionen kommen aus `*.mock.tsx`, nicht mehr aus einer zweiten Interpretation. Test: Entwurfs-Closure ist byte-identisch zur Registry-Closure derselben Spec.
> 2. **Zwei Canvas-Modi** (D8): *Bearbeiten* (Baum mit Editor-Rahmen; der Composer liefert gemergte Props, Event-Callbacks und Slot-Inhalte, die Verdrahtung simuliert `simulate.ts`) und *Vorschau* (die Mock-Komponente des Dokuments selbst — Verdrahtung läuft im generierten Code). Beide Wege nebeneinander sind der laufende Abgleich zwischen Simulation und Generator.
> 3. **Drag & Drop** (D9): Palette → Canvas/Slot-Zone, Knoten am Griff umhängen (samt Teilbaum, No-Op in den eigenen Teilbaum). Klick-Einfüge-Ziel bleibt als tastatur-/agent-freundlicher Weg. Desktop: Composer-Fenster mit `disable_drag_drop_handler()`, sonst frisst Tauris Datei-Drop-Handler die Events.
>
> **Weiter offen (bewusst nach P4 verschoben):** `kind: app`-Routen, Sortieren per Drag (Reihenfolge bleibt im Inspector), Typecheck im Browser (bleibt bei der Conformance-Stufe).
>
> **Rahmenbedingungen (User, 2026-07-24):**
> 1. **Agent-bedienbar**: Der Composer muss von Coding-Agents (Claude) selbst nutzbar sein — jede UI-Aktion existiert auch als HTTP-API (Laden/Speichern/Validieren/Mocken), der Zustand ist die Spec-Datei auf Disk (Round-Trip), keine UI-only-Funktionen. Agents arbeiten wahlweise über die API/CLI/MCP oder per Browser-Automation.
> 2. **Tauri-2-fähig**: Der Composer wird später eine Tauri-2-Desktop-App. Deshalb: Frontend als **statisch exportierbare Vite-React-SPA** (kein Next.js-Server-Coupling, keine SSR-Abhängigkeit), Backend ausschließlich hinter einer sauberen HTTP-Grenze (später als Tauri-Sidecar oder Rust-Reimplementierung austauschbar), keine Browser-only-APIs ohne Fallback.

- Web-App (Ausbau `apps/web/`): Canvas + Komponenten-Palette (aus Workspace/Fixtures, geladen über `POST /api/v1/mock`) + Property-Panel + Verdrahtungs-Editor.
- **Zwei Editier-Modi mit demselben Modell**: Composite-Komponente bauen (Output: Komponenten-Spec mit `composition:`) und App bauen (Output: App-Spec). Selbst gebaute Composites erscheinen sofort in der Palette → Komposition ist rekursiv.
- Rendering ausschließlich über Mock-Bundles (schnell, deterministisch, kein LLM im Loop).
- Round-Trip: Spec laden → visuell editieren → YAML speichern; ungültige Verdrahtung ist im UI nicht herstellbar.
- Ziel: rumprobieren können — Erkenntnisse fließen als Refinement in P4/P5-Schnitt zurück.

### Phase P4 — Projekt-Builds (`kind: app`)

> **✅ Geliefert 2026-08-04.** Kein eigener Phasen-Plan: die Konvention „genau ein aktiver Plan" gilt, also stehen Stufen und Entscheidungen hier.
>
> **Ergebnis**: `speccify build @org/demo-app` erzeugt ein Vite-React-Projekt, das durch `tsc --noEmit` und `vite build` geht und im Browser tut, was die Spec sagt — Startroute, `navigate`-Verdrahtung, Datenfluss über Screens, unbekannte Routen. Adapter: CLI, MCP-Tool `build`, `POST /api/v1/build` (byte-identisch). Beispiel-App `@org/demo-app` (4 Screens). Doku: [`docs/app-builds.md`](../../docs/app-builds.md).

- App-Spec-Schema finalisieren (Routen/Navigation/Theme/Env auf dem `composition:`-Fundament aus P2).
- `speccify build --target react [--mocks]` → komplettes Vite-Projekt; mit `--mocks` sofort lauffähig.
- Beispiel-App aus den Referenz-Specs; E2E-Test: Build mit Mocks läuft headless (Playwright-Smoke).

**Entscheidungen (2026-08-04, per User-Delegation):**

- **D10 — App-Form**: `kind: app` erbt `composition:` unverändert; jeder **Top-Level-Knoten ist ein Screen**. Neuer Block `app:` mit `routes[] {path, node, title?}` (erste Route = Startroute), optional `theme.tokens` (→ CSS-Variablen) und `env[] {name, default?, description?}`. Kein zweites Baum-Konzept, keine Layout-Sprache — Screens sind normale Composites.
- **D11 — Navigation**: neue Wiring-Aktion `navigate: /pfad` neben `set`/`emit`. Typgeprüft gegen die deklarierten Routen-Pfade; nur in `kind: app` erlaubt. Bewusst keine Parameter/Guards/History-Semantik im ersten Schnitt (Risiko-Abschnitt: Verdrahtung minimal halten).
- **D12 — Scaffold ohne Router-Dependency**: der Build erzeugt einen ~40-zeiligen Hash-Router (`src/router.tsx`) statt `react-router` einzubinden. Grund: das Projekt bleibt mit `react`/`react-dom`/`vite` lauffähig, der Build bleibt deterministisch und offline-fähig, und die Route-Semantik ist im generierten Code lesbar statt in einer Fremd-API versteckt.
- **D13 — Ein Zustandsknoten**: `src/App.tsx` hält Wiring-State *und* Route und rendert nur den Knoten der aktiven Route — dieselbe Wiring-Semantik wie der Composite-Mock (`set` → State, `emit` → eigener Callback), plus `navigate`. Damit gibt es weiterhin genau eine Verdrahtungs-Implementierung pro Target.
- **D14 — Zwei Füllungen, ein Scaffold**: `--mocks` legt die Mock-Closure unter `src/components/` ab plus je Screen einen Re-Export (`<Name>.tsx` → `./<Name>.mock`) — der Import-Swap aus dem P2-Vertrag, sichtbar als eine Zeile. Ohne Flag stehen dort die (LLM-)generierten Implementierungen. Das Scaffold ist in beiden Fällen byte-identisch, bis auf die README-Zeile, die sagt, womit gebaut wurde.
- **D15 — Adapter-Symmetrie**: `speccify build` (CLI), MCP-Tool `build` und `POST /api/v1/build` liefern byte-identische Dateien (Cross-Consistency-Vertrag). Der teure Beweis (echter `vite build` + Playwright) läuft wie Conformance/Visual-Regression hinter einem Pytest-Marker und in einem eigenen CI-Job, nicht in der Standard-Suite.

**Stufen (alle ✅):** P4.1 Schema/Parser/Validierung (`app:`, `navigate:`) · P4.2 Core-Codegen `app_react` + Determinismus · P4.3 CLI/MCP/Web-Adapter + Cross-Consistency · P4.4 Beispiel-App + echter Vite-Build-Smoke (`pytest -m app_build`, eigener CI-Job) + Doku.

**Beim Bauen gelernt:** Event-Payloads eines Mocks entstehen aus gleichnamigen Props — ein Datenfluss ist im gemockten Build also nur sichtbar, wenn seine Quelle eine statische Prop ist. Deshalb hat die Demo-App einen Notiz-Screen (`@org/text-input` mit statischem `value`). Steht in `docs/app-builds.md`.

**Weiter offen (bewusst):** nur Target `react`; Routen ohne Parameter/Guards/verschachteltes Routing; der Composer editiert `app:`-Routen noch nicht visuell.

### Phase P5 — Git-basierte Spec-Quellen

> **✅ Geliefert 2026-08-04/05.** Stufen und Entscheidungen hier (ein aktiver Plan).
>
> **Ergebnis**: Eine Dependency kann aus einem Git-Repo kommen (`git+<url>[#<pfad>]`, Tags als Versionen), das Lockfile pinnt den Commit, `pull`/`verify` laufen danach offline gegen einen Bare-Clone-Cache. Discovery über Index-Repos (eine Datei pro Spec-Repo) mit `speccify search`, MCP-Tool `search` und `GET /api/v1/index`. Doku: [`docs/git-sources.md`](../../docs/git-sources.md).

- `GitRegistry` (Registry-Protocol) mit Tag-Discovery, Shallow-Fetch, Content-Addressed Cache.
- Identitäts-Schema + Lockfile v4 (Commit-Pin) + Migration bestehender Lockfiles.
- CLI: `add <git-ref>`, `pull`, `verify` gegen Git-Quellen; neues `publish` als Tag-Helfer (validieren → taggen → push-Hinweis).
- Index-Repo (Discovery): Format, CI-Validierung, `speccify search` liest Index; Composer-Palette kann aus dem Index laden.
- MCP + Web auf Git-Quellen nachziehen (Cross-Consistency-Vertrag hält).

**Entscheidungen (2026-08-04, per User-Delegation) — beantworten die offenen Fragen 1–3:**

- **D16 — Identität = Git-Ref als Spec-Id** (Frage 1): `git+https://host/org/repo` für Single-Spec-Repos, `git+https://host/org/repo#pfad/im/repo` für Specs in Unterverzeichnissen. Damit ist die Id host-qualifiziert (kein Dependency-Confusion-Problem, keine Scope-Reservierung) **und passt ohne Änderung in das bestehende `Registry`-Protocol** (`list_versions`/`fetch` bekommen die Id) — Resolver, Lockfile und MVS bleiben unangetastet. Keine Alias-Tabelle, keine Migration bestehender `@scope/name`-Ids: beide Formen existieren nebeneinander, `@scope/name` bleibt die lokale/Fixture-Form.
- **D17 — Tags sind die Versionen** (Frage 2): `v<semver>` im Single-Spec-Repo, `<pfad>/v<semver>` bei gesetztem `#pfad` (Go-Konvention). Ein Repo kann damit beliebig viele Specs unabhängig versionieren; die Regel ist mechanisch aus der Id ableitbar, es gibt keine zweite Konvention zu raten.
- **D18 — Trust über Commit-Pin** (Frage 3): das Lockfile pinnt zusätzlich den Commit-SHA hinter dem Tag (Lockfile v4); `verify` prüft Tag → Commit → Spec-Bytes. Signierte Tags/gitsign bleiben ein späterer, additiver Slot — der bestehende `signature`-Block deckt das ab. Kein sigstore in P5.
- **D19 — Der Cache ist ein Bare-Repo**: pro Repo-URL ein Bare-Clone unter `~/.cache/speccify/git/<hash>/`, Tags per `fetch --depth 1`, Spec-Bytes per `git cat-file blob <tag>:<pfad>` — kein Working Tree, kein Checkout. Nach einem Fetch ist alles offline reproduzierbar (`list_versions`/`fetch` lesen lokale Refs); `offline=True` verbietet jeden Netz-Zugriff hart. Tests laufen gegen `file://`-Fixture-Repos, CI braucht kein Netz.

**Stufen (alle ✅):** P5.1 `GitRegistry` + Ref-Parsing + Cache · P5.2 Lockfile v4 (Commit-Pin) + `lock`/`pull`/`verify` gegen Git · P5.3 Discovery (Index-Format, Schema, `speccify search`) · P5.4 MCP + Web-Backend auf Git-Quellen, `GET /api/v1/index`, MCP-Tool `search`.

**Weitere Entscheidungen:** **D20** der Codegen benennt nach der deklarierten Id (`Spec.name_id`), nicht nach der Quelle — Herkunft ist eine Lockfile-Eigenschaft. **D21** eine Datei pro Index-Eintrag (`entries/*.yaml`): ein PR fasst eine Datei an, keine Merge-Konflikte, CI validiert einzeln; der Index nennt nie Versionen, weil Tags die Wahrheit sind. **D22** Such-Ranking Id > Titel > Keyword > Summary, `--json` für Agents. **D23** eine `MultiRegistry`-Fassade bringt Git-Quellen in alle Pfade, die genau *eine* Registry erwarten (Komposition, Mocks, Builds) — statt jede Aufrufstelle auf Listen umzubauen.

**P5.5 (2026-08-05):** Index-Suche in der Composer-Palette — Treffer aus einem Index-Repo lassen sich einfügen oder ziehen, in `composition.uses` landet die Git-Quelle, im Canvas rendert deren generierter Mock. Dafür trennt die Detail-Antwort jetzt `id` (deklarierter Name) und `source` (Ref), und `GET /api/v1/spec?source=` löst beliebige Quellen auf.

**Offen (bewusst):** Index-Treffer lassen sich nicht „öffnen" (im Editor bearbeiten) — dafür müsste der Composer in ein fremdes Repo schreiben. Außerdem: nur `https`/`file`-Remotes (kein SSH), Tags müssen exaktes Semver tragen, und der Repo-Index bleibt leer, bis das Ökosystem zum Launch gesät wird.

**Stand nach P5.2 (2026-08-04):** der CLI-Pfad ist vollständig — ein Projekt kann seine Dependencies aus Git beziehen, das Lockfile pinnt den Commit, `pull`/`verify` laufen danach offline gegen den Bare-Clone-Cache. Doku: [`docs/git-sources.md`](../../docs/git-sources.md).

**Beim Bauen entschieden (D20):** Der Codegen benennt Dateien nach der **in der Spec deklarierten** Id (`Spec.name_id`), nicht nach der Quelle — eine aus Git bezogene `@acme/button` heißt im generierten Projekt weiter `Button.tsx`. Herkunft ist eine Lockfile-Eigenschaft, kein Dateiname. Für Registry-Specs sind `name_id` und `spec_id` identisch, es ändert sich also kein Byte (per `-m app_build`-Smoke und den Cross-Consistency-Tests belegt).

### Phase P6 — Ökosystem & Launch

> **P6.1 geliefert 2026-08-05**: Doku-Site auf den heutigen Stand gezogen (Sync um API/Mocks, Composer, Projekt-Builds, Git-Quellen erweitert; Registry-Abschnitt raus; Stub-Seiten gefüllt; Landing + README auf die Git-Geschichte), plus [`docs/launch.md`](../../docs/launch.md) mit Checkliste, Saatgut-Plan und Post-Entwürfen.

- Doku-Site umbauen (Composer, App-Builds, Git-Workflow), Quickstarts ✅, Beispiel-Repos als Saatgut im Index.
- OSS-Launch (HN/X), Community-Aufbau.

**Was jetzt noch offen ist, ist bewusst BO-Sache** (nichts davon selbst tun): Repo öffentlich anlegen und pushen, Saatgut-Repos für den Index erzeugen, Doku-Site deployen, signierte Mac-App (Developer-ID + Notarisierung), Updater-Schlüssel, Launch-Posts absetzen. Alles Nötige liegt vor — `docs/launch.md` nennt pro Punkt den Befehl bzw. den fertigen Text.

---

## Entschieden (Refinement 2026-07-23)

- **Registry-Schicksal**: Archiv-Branch `archive/pre-oss-pivot-registry` + Löschung aus dem Arbeitszweig. Discovery später über statisches Index-Repo (P5).
- **Reihenfolge**: Composer-Fast-Track — API/Mocks (P2) und Composer (P3) vor Projekt-Builds (P4) und Git-Quellen (P5). Begründung: durch Rumprobieren im Composer schlauer werden, bevor Verdrahtungs-/Build-Semantik final geschnitten wird.
- **Composer-Scope**: baut Apps **und** Composite-Komponenten (Komponenten aus Unterkomponenten); `composition:` wird gemeinsames Schema-Konzept.
- **P3-Entscheidungen (2026-08-04, per User-Delegation)**: **D7** Canvas rendert die generierte Mock-Closure (Browser-Kompilat via sucrase) statt den Contract zu interpretieren — Preis: +215 kB im Composer-Bundle und `new Function`-Auswertung (Tauri-CSP ist `null`, Vite-Dev ohne CSP); Gewinn: keine zweite Mock-Implementierung, keine Drift. **D8** Editier-Modus rendert Knoten einzeln (Composer behält Selektion/Slot-Zonen/Wiring-Log), Vorschau-Modus rendert das Dokument-Mock am Stück; kein Iframe, weil Selektion und Drop-Ziele sonst über Frame-Grenzen laufen müssten. **D9** Drag & Drop per HTML5-DnD (Playwright-testbar, Tauri-tauglich mit `disable_drag_drop_handler()`) statt Pointer-Events-Eigenbau.
- **P2-Entscheidungen (2026-07-23, per User-Delegation — Details im [P2-Plan](./phase-p2-api-composition-mocks.md))**: Logic-Mocks fixture-basiert (D1); keine State-Machine im API-Vertrag, `behavior:` reserviert (D2); kein automatisches Prop-Forwarding/Event-Bubbling in Composites, nur explizites Mapping (D3); Phase-7-S4 (`screenshots[].tolerance`) reitet auf dem Schema-Bump mit, Rest des Phase-7-Plans archiviert als Backlog (D4); Spec-Schema-Bump auf explizites `schema_version: 1` mit v0-Loader-Migration (D5); Mocks lockfile-frei, Reproduzierbarkeit über Spec-Hash + Template-Version (D6).

## Offene Fragen fürs Refinement

1. **Identitäts-Schema (P5)**: `spec://github.com/org/repo@1.2.0` (Go-Stil, host-qualifiziert) vs. Kurzform mit Default-Host? Wie werden bestehende `@org/name`-IDs migriert — Alias-Tabelle im Index-Repo?
2. **Multi-Spec-Repos (P5)**: Monorepo mit vielen Specs (Tag-Konvention `name/vX.Y.Z`?) vs. ein Repo pro Spec? Beides unterstützen?
3. **Trust-Modell (P5)**: reichen Commit-SHAs + optional signierte Git-Tags, oder sigstore-Slot aus Lockfile v2/v3 weiterführen (z. B. gitsign)?
4. **Erstes Build-Target (P4)**: React/Vite (Playground-Synergie, Composer rendert Web) — bestätigen? SwiftUI-App-Builds wären P4-Folge.
5. **Composer-Scope im MVP (P3)**: nur Layout + Props + Event-Verdrahtung? Oder auch Daten-Bindings/Routen visuell? (Vorschlag: MVP ohne visuelles Routing, Routen bleiben YAML.)
6. **Web-Playground vs. Composer (P3)**: Playground weiterentwickeln zum Composer oder als getrennte App daneben?

---

## Risiken

- **Git-Fetch-Performance/Offline**: Shallow-/Sparse-Fetch + Content-Cache müssen so gut sein wie der heutige File-Cache; CI muss ohne Netz laufen können (Fixture-Repos als `file://`-Remotes in Tests).
- **Verdrahtungs-Semantik ist das schwerste Stück** (P4): Event→Input-Bindung klingt simpel, wird aber schnell zur Sprache. Bewusst minimal starten (direkte Bindung + einfache Transformationen), keine allgemeine Expression-Language im MVP.
- **Mock-Fidelity**: Mocks, die zu hässlich/generisch sind, machen den Composer wertlos; Mocks, die zu viel können, werden heimlich zur zweiten Implementierung. Der `ux.references`-Block (Screenshots) kann Mocks stylen helfen — Grenze klar ziehen.
- **Spec-Schema-v1-Migration**: erster Spec-Schema-Bump; Migrations-Tooling und v0-Kompatibilität im Loader einplanen (bewährtes Muster aus Lockfile v1→v2). Größter operativer Haken: der Bump invalidiert den `spec_sha256`-gebundenen LLM-Replay-Cache (Mitigation siehe P2-Plan, Stage 1).
- **Scope-Explosion**: vier Säulen gleichzeitig ist viel. Die Phasen sind deshalb strikt sequenziell und einzeln shippable geschnitten; nach jeder Phase Go/No-Go wie bisher.
