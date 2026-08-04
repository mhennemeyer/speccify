---
lifecycle: done
status: P2-Kern abgeschlossen 2026-07-24 (Schema v1, 7 Referenz-Specs, deterministischer Mock-Codegen über CLI/MCP/Web); Stage 4 (voller API-Conformance-Harness) vertagt
sessionId: phase-p2-api-composition-mocks
---
# Phase P2 — API-Vertrag, Komposition & Mock-Generator (Composer-Fundament)

> **Status:** ✅ Kern abgeschlossen (2026-07-24) — Stages 1, 2, 3, 5, 6 geliefert; **Stage 4 (API-Conformance-Harness) bewusst hinter P3 vertagt** (siehe Update unten). Nächster Schritt: **P3 — Visueller Composer**.
> **Update 2026-07-24 (User-Refinement „Start bei Null")**: Es gibt keine Bestandsnutzer — **kein v0-Migrationspfad** (D5 revidiert: v1 ersetzt v0 hart, Loader/Validator kennen nur v1). Replay-Cache-Mitigation entschieden und umgesetzt: **mechanisches Re-Keying** der 18 Cache-Einträge auf die neuen Spec-Hashes + `prompt_version 0.2.0` (Responses byte-identisch, kein Bedrock-Recording nötig). Wiring-Key heißt `when:` statt `on:` (YAML-1.1-Falle: `on` parst als Boolean).
> **Stage-4-Vertagung**: Der `@conformance`-Test `test_mock_closure_typechecks_via_tsc` deckt die Basisebene (Mock erfüllt tsc). Der vollwertige TS-Harness (API-Assertions gegen Mock **und** LLM-Output) lohnt erst nach den P3-Composer-Erkenntnissen — dann ist klar, welche Vertragsteile wirklich tragen.
> **Neue Rahmenbedingungen für P3 (User, 2026-07-24)**: (1) Der Composer muss **vom Coding-Agent selbst bedienbar** sein — alle UI-Aktionen auch als HTTP-API/CLI, Zustand = Spec-Dateien auf Disk. (2) Der Composer wird später eine **Tauri-2-App** — nichts bauen, was dem entgegensteht (statisch exportierbares Frontend, Backend hinter sauberer HTTP-Grenze).
> **Kontext:** [Pivot-Plan](./pivot-open-source-git-composer.md), Phase P2. Ziel ist das komplette technische Fundament für den visuellen Composer (P3): formale, mockbare Komponenten-APIs + Komposition aus Unterkomponenten.
> **Ziel-Tag (Vorschlag):** `v0.12.0-p2-api-mocks` (setzt der User, vgl. `rules.md`)
> **Vorgänger:** OSS-Pivot P1 (abgeschlossen 2026-07-23, Branch `feat/oss-pivot`)

## Overview & Goals

P2 macht aus dem informellen `inputs`/`events`-Teil der Spec einen **formalen,
separat hashbaren API-Vertrag** (`api:`), führt **Komposition** als gemeinsames
Schema-Konzept ein (`composition:` — Komponenten aus Unterkomponenten, später
identisch für `kind: app`) und liefert einen **deterministischen
Mock-Generator** (kein LLM), der aus dem API-Vertrag lauffähige
React-Mock-Komponenten erzeugt. Damit kann der Composer in P3 sofort rendern,
verdrahten und speichern — ohne LLM im Loop, ohne dass Komponenten „fertig"
implementiert sind.

**Definition of Done (Phase):** Eine neue Composite-Referenz-Spec
(`@org/search-bar` aus `@org/text-input` + `@org/button`) validiert, lintet,
und `speccify mock @org/search-bar --target react` erzeugt einen
byte-deterministischen, per `tsc --noEmit` typechecked Mock-Baum. Die
API-Conformance-Suite bestätigt, dass Mock und LLM-generierte Implementierung
denselben API-Vertrag erfüllen.

## Entscheidungen (Stage 0 — per User-Delegation „folge deinen Empfehlungen", 2026-07-23)

- **D1 — Logic-Mocks fixture-basiert:** `logic`-Kinds (z. B. `http-api-client`)
  werden über **deklarierte Fixture-Responses in der Spec** gemockt
  (`api.fixtures`): der Mock ist ein Modul mit derselben Signatur, das
  deterministisch Fixture-Daten liefert. Kein Verhaltens-Interpreter in P2.
  Specs ohne Fixtures → Status `mock_unavailable` (kein Fehler, analog
  `toolchain_missing`).
- **D2 — Keine State-Machine im API-Vertrag:** P2-Vertrag = **Props / Events /
  Slots** (+ Fixtures für logic). Der Schema-Key `behavior:` wird als
  **reserviert** dokumentiert (spätere optionale State-Machine), aber nicht
  implementiert. Begründung: Schema-Komplexität klein halten; der Composer
  braucht für Layout+Verdrahtung keine Verhaltenstreue.
- **D3 — Kein automatisches Durchreichen in Composites:** Eine
  Composite-Komponente re-exportiert Kind-APIs **nur über explizites Mapping**
  im eigenen `api:`-Block (`map_to` für Props, `wiring`-`emit` für Events).
  Kein implizites Prop-Forwarding/Event-Bubbling — die Composite-API bleibt
  dadurch ein echter, stabiler Vertrag.
- **D4 — Phase 7 (Visual-Regression-Vertiefung):** Substage **S4**
  (`screenshots[].tolerance`) **reitet auf dem P2-Schema-Bump mit** (Stage 1).
  Der Rest (S1–S3, S5–S7) bleibt optionales Backlog; der Phase-7-Plan wird
  nach `archive/` verschoben.
- **D5 — Spec-Schema-Versionierung:** Erster expliziter Bump seit Phase 0:
  neues Pflichtfeld `schema_version: 1` + versionierte Datei
  `schema/spec.v1.schema.json` (bisheriges `spec.schema.json` bleibt als v0
  liegen). v0-Specs **bleiben ladbar** — der Loader migriert in-memory
  (`inputs` → `api.props`, `events` → `api.events`), `speccify lint` validiert
  beide Versionen. Die 5 Referenz-Specs werden auf v1 gehoben.
- **D6 — Mocks sind lockfile-frei:** `speccify mock` rendert deterministisch
  aus den Spec-Bytes (Template-Pin analog Phase 1a, kein LLM, kein Netz) und
  schreibt nach `speccify_mocks/<target>/`. Kein Lockfile-Eintrag in P2 —
  Reproduzierbarkeit folgt aus Spec-Hash + Template-Version; Pinning wird erst
  relevant, wenn Mocks in Builds eingebettet werden (P4).

## Scope

**In Scope**
- Spec-Schema v1: `api:`-Block (Props/Events/Slots/Fixtures), `schema_version`,
  `screenshots[].tolerance`, Loader-Migration v0→v1, Lint für beide Versionen.
- `composition:`-Block + Typprüfung der Verdrahtung in `core/`.
- Neue Referenz-Specs: `@org/text-input` (Leaf), `@org/search-bar` (Composite).
- Deterministischer Mock-Codegen **React** (`speccify mock`, Core-API,
  MCP-Tool, Web-Endpoint).
- API-Conformance-Backend (TS-Harness aus `api:`, `tsc --noEmit` gegen Mock
  und LLM-Output).
- Doku (`docs/component-api-and-mocks.md`) + Site-Sync + CLI-Referenz.

**Out of Scope (Folge-Phasen)**
- Composer-UI (P3), `kind: app`/Routen/Builds (P4), Git-Quellen (P5).
- Mock-Codegen für SwiftUI/Angular (Follow-up nach P3-Erkenntnissen).
- State-Machine/`behavior:` (D2), automatisches Forwarding (D3).
- LLM-Codegen-Änderungen — der bestehende React/SwiftUI/Angular-Pfad bleibt
  unangetastet; nur der Conformance-Stack lernt den API-Vertrag kennen.

## Vertrags-Skizze (Detail-Design in Stage 1/2)

```yaml
# Leaf (v1): @org/button — inputs/events wandern unter api:
schema_version: 1
id: spec://button
kind: ui-component
api:
  props:
    - name: label
      type: string
      required: true
    - name: variant
      type: enum[primary, secondary, ghost]
      default: primary
  events:
    - name: pressed
      payload: {}
  slots:
    - name: icon_leading
      optional: true

# Composite (v1): @org/search-bar — Komposition + explizites Mapping (D3)
schema_version: 1
id: spec://search-bar
kind: ui-component
api:
  props:
    - name: placeholder
      type: string
      map_to: query_input.placeholder     # explizites Forwarding
  events:
    - name: submitted
      payload: { query: string }
composition:
  uses:
    query_input: spec://text-input@^0.1
    go_button: spec://button@^0.1
  tree:
    - node: query_input
    - node: go_button
      props: { label: "Search", variant: primary }
  wiring:
    - on: go_button.pressed
      emit: submitted
      with: { query: query_input.value }
```

Typprüfung (Stage 2): `map_to`-Ziele müssen existierende Kind-Props mit
kompatiblem Typ sein; `wiring.on` referenziert existierende Kind-Events;
`emit` referenziert eigene `api.events` mit kompatiblem Payload; `tree.props`
werden gegen die Kind-API geprüft (Typ + Pflichtfelder).

## Stages

### Stage 1 — Spec-Schema v1 (`api:` + `schema_version` + Tolerance)
- `schema/spec.v1.schema.json`; `SchemaValidator` versionsdispatchend
  (`schema_version` fehlt → v0-Pfad, unverändert).
- Loader-Migration v0→v1 in-memory (`inputs`→`api.props`, `events`→`api.events`,
  Constraints-Strings → `default`/`required`/`optional`-Felder).
- `screenshots[].tolerance` (Phase-7-S4, D4) als optionales Feld.
- 5 Referenz-Specs (specs/ + registry-fixtures/) auf v1 heben; `speccify lint`
  validiert v0- und v1-Dateien.
- **Achtung Replay-Cache:** Der Cache-Key bindet `spec_sha256` — das Heben der
  Fixture-Specs invalidiert den eingecheckten LLM-Cache. Mitigation prüfen:
  Cache-Key auf **kanonisierte v1-Form** rechnen oder Cache-Einträge einmalig
  per `scripts/record_llm_cache.py` neu aufnehmen (Maintainer-Aktion, wie
  Phase 5b Stage 2). Entscheidung als erster Schritt dieser Stage.
- **Done:** Alle bestehenden Tests grün; neue Validator-/Migrations-Tests;
  beide Drift-Checks grün.

### Stage 2 — `composition:` + Verdrahtungs-Typprüfung
- Schema-Erweiterung (`uses`/`tree`/`wiring`, nur `kind: ui-component` in P2).
- `core/`: `CompositionValidator` — löst Kind-Specs über das
  `Registry`-Protocol auf und prüft Mapping/Wiring/Props gegen deren
  `api:`-Blöcke (Fehler-UX mit Pfadangaben, analog `ResolverError`).
- Neue Specs `@org/text-input@0.1.0` (Leaf, mit `value`-Prop + `changed`-Event)
  und `@org/search-bar@0.1.0` (Composite) in `specs/` + `registry-fixtures/`.
- Resolver: `composition.uses` zählt wie `uses` als Dependency (MVS transitiv).
- **Done:** Positiv-/Negativ-Tests der Typprüfung (falscher Prop-Typ, fehlendes
  Kind-Event, Payload-Mismatch, unbekannter Node); `speccify lint` + `lock`
  über die Composite-Spec grün.

### Stage 3 — Mock-Codegen React (`speccify mock`)
- `core/`: `render_mock_for_target(spec, target)` — deterministische Templates
  (Jinja-frei, analog Phase-1a-Stub; Template-Pin `mock_template_version`).
  - **Leaf ui-component:** TSX-Komponente mit typisierten Props aus
    `api.props`, Events als Callback-Props (`onPressed`), Slots als
    `children`/benannte Props; generische, aber saubere Darstellung
    (Label, Variant-Badge, Event-Log im Dev-Modus).
  - **Composite:** rendert den `tree:` als Baum der Kind-Mocks inkl.
    `wiring`-Verdrahtung (Callback → Emit).
  - **logic-Kind:** Fixture-Modul aus `api.fixtures` (D1); ohne Fixtures →
    `mock_unavailable`.
- CLI: `speccify mock <spec_ref> --target react [--out ./speccify_mocks]`
  (Default-Out per D6); Multi-Spec via Manifest analog `pull`.
- **Done:** Snapshot-Tests (zwei Läufe byte-identisch); Mock-Baum der
  `search-bar` kompiliert via `tsc --noEmit` (nutzt vorhandene
  `ReactToolchainDriver`-Infrastruktur, `@conformance`-markiert); CLI-Referenz
  regeneriert (8 Command-Seiten).

### Stage 4 — API-Conformance-Backend
- `core/`: `ApiConformanceBackend` hinter dem bestehenden
  `ConformanceBackend`-Protocol — generiert aus `api:` einen
  **TS-Type-Assertion-Harness** (Props-Interface + Event-Signaturen) und prüft
  via `tsc --noEmit`, dass eine Implementierung ihn erfüllt.
- Läuft gegen **beide** Artefakte: Mock (Stage 3) und LLM-Output
  (Replay-Cache) — das ist der Austauschbarkeits-Beweis Mock ↔ echt.
- `speccify conformance` um Backend `api` erweitert; `@conformance`-Marker,
  Default-Exclude wie gehabt.
- **Done:** Harness-Tests für `button` + `search-bar` (Mock und LLM-Output
  grün); Negativ-Test (manipulierter Output mit falschem Prop-Typ failt).

### Stage 5 — MCP + Web + Cross-Consistency
- MCP-Tool `mock` (Tool-Count 6 → 7; Smoke + Skeleton-Test angepasst).
- Web-Backend: `POST /api/v1/mock` analog `/render` (`{spec_yaml, spec_id,
  version, target}` → `{files, mock_template_version}`) — Vorbau für die
  Composer-Palette in P3; Fehler-Codes wie gehabt (`spec_invalid`,
  `unknown_target`, neu `mock_unavailable`).
- Cross-Consistency: Mock-Pfad CLI ↔ MCP ↔ Web byte-identisch (neuer Test
  neben dem 60-Pfad-Sweep; Sweep selbst bleibt LLM-Render-Pfad).
- **Done:** Cross-Consistency-Test grün; `scripts/mcp_smoke.py` grün.

### Stage 6 — Doku + Wrap-up
- `docs/component-api-and-mocks.md` (Vertrag, Mock-Semantik, Komposition,
  D1–D6); Cross-Links in `conformance.md`/README; Site-Sync + CLI-Docs
  (`--check` grün).
- Phase-7-Plan nach `archive/` (D4-Vermerk: S4 in P2 gelandet, Rest Backlog).
- `agent.md`/`status.md`/`log.md` aktualisieren; diesen Plan archivieren.
- **Tag-Vorschlag an User:** `v0.12.0-p2-api-mocks`.
- **Done:** Volle Verifikation (Pytest + ruff + Drift-Checks + Smokes) grün
  dokumentiert; P3-Plan-Entwurf (Composer) als nächster Schritt notiert.

## Risiken

- **Replay-Cache-Invalidierung durch Spec-Bump (Stage 1)** — größtes
  operatives Risiko; deshalb als erste Entscheidung der Stage (kanonisierter
  Cache-Key vs. Maintainer-Re-Recording).
- **Constraint-String-Migration** (`constraints: ["default=md"]` → Felder) hat
  Ecken (z. B. `icon-name`-Pseudo-Typen); Migrations-Lint muss unbekannte
  Constraints sichtbar machen statt sie still zu verlieren.
- **Mock-Fidelity-Balance** (Pivot-Plan-Risiko): Mocks generisch halten —
  Styling-Anreicherung aus `ux.references` ist explizit **nicht** P2.
- **Typsystem-Umfang der Verdrahtung:** nur exakte/enum-kompatible Matches in
  P2, keine Koerzion, keine Expressions — Erweiterung erst nach
  P3-Erkenntnissen.
