---
lifecycle: active
status: P1 (Registry-Rückbau) + P2 (API/Komposition/Mocks) + P3-Runde-1 geliefert; offen: P3-Rest (Mock-Bundle-Rendering statt Contract-Interpretation, Drag & Drop), P4 `speccify build`, P5 Git-Quellen
sessionId: pivot-open-source-git-composer
---
# Plan: Pivot — Open Source, Git-basierte Registry, Projekt-Builds & visueller Composer

> **Status**: 📋 In Umsetzung (P1 gestartet 2026-07-23)
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
> **✅ Verfeinerung Runde 1 (2026-07-24):** visuelles Slot-Befüllen (Slot-Zonen im Canvas als klickbares Einfüge-Ziel, rekursives Mock-Rendering, „Platzierung"-Umhängen im Inspector, Teilbaum-Entfernen mit Wiring-Cleanup), Undo/Redo (`{doc, children}`-Snapshots, Tipp-Koaleszierung, ⌘Z/⇧⌘Z + Topbar-Buttons) und Playwright-UI-Smoke (`apps/composer/e2e/`, 3 Tests gegen echtes Backend mit Wegwerf-Registry, eigener CI-Job). **Weiter offen:** `kind: app`-Routen (P4), Mock-Bundle-Rendering statt Contract-Interpretation, Drag & Drop statt Klick-Ziel.
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
- App-Spec-Schema finalisieren (Routen/Navigation/Theme/Env auf dem `composition:`-Fundament aus P2).
- `speccify build --target react [--mocks]` → komplettes Vite-Projekt; mit `--mocks` sofort lauffähig.
- Beispiel-App aus den Referenz-Specs; E2E-Test: Build mit Mocks läuft headless (Playwright-Smoke).

### Phase P5 — Git-basierte Spec-Quellen
- `GitRegistry` (Registry-Protocol) mit Tag-Discovery, Shallow-Fetch, Content-Addressed Cache.
- Identitäts-Schema + Lockfile v4 (Commit-Pin) + Migration bestehender Lockfiles.
- CLI: `add <git-ref>`, `pull`, `verify` gegen Git-Quellen; neues `publish` als Tag-Helfer (validieren → taggen → push-Hinweis).
- Index-Repo (Discovery): Format, CI-Validierung, `speccify search` liest Index; Composer-Palette kann aus dem Index laden.
- MCP + Web auf Git-Quellen nachziehen (Cross-Consistency-Vertrag hält).

### Phase P6 — Ökosystem & Launch
- Doku-Site umbauen (Composer, App-Builds, Git-Workflow), Quickstarts, Beispiel-Repos als Saatgut im Index.
- OSS-Launch (HN/X), Community-Aufbau.

---

## Entschieden (Refinement 2026-07-23)

- **Registry-Schicksal**: Archiv-Branch `archive/pre-oss-pivot-registry` + Löschung aus dem Arbeitszweig. Discovery später über statisches Index-Repo (P5).
- **Reihenfolge**: Composer-Fast-Track — API/Mocks (P2) und Composer (P3) vor Projekt-Builds (P4) und Git-Quellen (P5). Begründung: durch Rumprobieren im Composer schlauer werden, bevor Verdrahtungs-/Build-Semantik final geschnitten wird.
- **Composer-Scope**: baut Apps **und** Composite-Komponenten (Komponenten aus Unterkomponenten); `composition:` wird gemeinsames Schema-Konzept.
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
