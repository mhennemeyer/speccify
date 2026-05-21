# Plan: Projekt „speccify.io/de" – Spec-First Komponenten-Plattform für AI-Agenten

> **Status**: 📋 Entwurf – Vorstellung im internen Team-Bereich
> **Erstellt**: 2026-04-29
> **Update 2026-04-29**: Entscheid für Desktop-Stack getroffen → **Tauri** (Rust + System-WebView). Gleichzeitig willkommene Gelegenheit, Rust im Team aufzubauen.
> **Update 2026-05-04 (Refinement)**: Fokus geschärft auf **CLI + MCP + Registry zuerst** („npm-artiger Workflow"). Desktop-App **geparkt** (Re-Aktivierungs-Kriterien siehe Phase 4). Browser-Playground läuft **parallel** zum CLI als minimale Demo-Oberfläche. Visuelles Tooling zerlegt: Asset-Refs in der Spec sofort, Galerie/Live-Preview/Figma nachgelagert. Package-Manager-Designentscheidungen siehe [Package-Manager-Vergleich](archive/package-manager-comparison.md).
> **Ziel**: Eine Plattform, auf der Komponenten nicht als Code in einem konkreten Framework, sondern als **präzise, sprach- und ökosystem-unabhängige Spezifikationen** entwickelt, refined, gesucht und geteilt werden. Ein AI-Agent kann anhand einer Spezifikation und einem stabilen Identifier (`<comp-id>`) die Komponente in beliebigen Ziel-Stacks (SwiftUI, Angular, React, Flutter, Jetpack Compose, Backend-Services, CLI-Tools …) deterministisch umsetzen. Distribution zuerst über CLI + MCP-Server + Website/Playground; Desktop-App optional und nachgelagert.
> **Arbeitsname**: `speccify` (Flow + Specification)

---

## Vision in einem Satz

> *„npm für Spezifikationen statt für Code – Komponenten beschreiben, nicht implementieren. Der AI-Agent ist der Compiler in das Ziel-Framework."*

---

## Das Problem

Heutige Komponenten-Ökosysteme (npm, Maven, Cocoapods, pub.dev …) sind **fragmentiert pro Sprache und Framework**:
- Eine React-Komponente lässt sich nicht in SwiftUI nutzen.
- Ein Angular-Service nicht in einer Flutter-App.
- Bibliotheken müssen N-mal neu geschrieben werden – jedes Team erfindet Login-Flows, Datentabellen, Onboarding-Wizards immer wieder neu.
- Wissen über *wie eine Komponente sich verhalten soll* steckt in Code, nicht in einer abstrakten, wiederverwendbaren Form.

Mit AI-Agenten verschiebt sich der Engpass: **Code zu generieren ist billig geworden, eine präzise Beschreibung des Gewollten ist der eigentliche Wert.**

---

## Die Idee – ausgeschmückt

Eine Komponente in Speccify ist eine **abgeschlossene Spezifikation**, die alles enthält, was ein AI-Agent braucht, um sie in einem beliebigen Stack korrekt umzusetzen:

- Eindeutige Identität (`spec://login-with-otp@1.4.0` oder `@org/login-with-otp`)
- Maschinenlesbares Manifest (YAML/JSON-Schema)
- Menschen- und LLM-lesbare Beschreibung (Markdown mit definierter Struktur)
- Akzeptanzkriterien & Beispielinteraktionen (Given/When/Then, Test-Cases)
- Visuelle Referenzen (Screenshots, Wireframes, Figma-Embeds, Bilder von „so soll es aussehen / nicht aussehen")
- Inputs/Outputs/Events mit Typen (sprachunabhängig, ähnlich JSON Schema / Protobuf)
- Abhängigkeiten zu anderen Komponenten (`uses: [spec://otp-input@^1, spec://api-call@^2]`)
- Stilistische Constraints (Accessibility, Performance-Budget, Security-Anforderungen)
- Referenzimplementierungen pro Framework (optional, vom Agent generiert, vom Menschen validiert) als „Conformance-Tests"

### Drei Komponenten-Klassen

1. **UI-Components** – Buttons, Inputs, Dialoge, ganze Screens
2. **Logic-Components** – Validatoren, State-Maschinen, API-Clients, Datenmodelle
3. **Workflow-Components** – Kompositionen aus 1+2 (z. B. „Onboarding-Wizard mit OTP-Login und Profil-Setup")

Workflows referenzieren andere Komponenten per ID → **Komposition statt Copy-Paste**.

### Was ein AI-Agent damit macht

```
speccify pull spec://login-with-otp@1.4.0 --target swiftui --out ./Sources
```
oder im Editor:
> „Bau mir einen Onboarding-Flow mit `spec://login-with-otp` und `spec://profile-setup`, Ziel: Angular 18, Style: Tailwind."

Der Agent
1. Resolved die Spec(s) inkl. transitiver Abhängigkeiten,
2. mappt sprachunabhängige Typen auf Ziel-Stack-Typen,
3. generiert idiomatischen Code im Ziel-Framework,
4. erzeugt Conformance-Tests aus den Akzeptanzkriterien,
5. meldet Lücken/Mehrdeutigkeiten in der Spec zurück (→ Refinement-Loop).

---

## Kernprinzipien

1. **Spec-First, Code-Second** – die Spec ist das Artefakt, Code ist Ausgabe.
2. **Determinismus durch Präzision** – je vollständiger die Spec, desto reproduzierbarer der Output verschiedener Agenten.
3. **Stable Identity** – `<comp-id>` ist unveränderlich; Änderungen = neue Version.
4. **Composability** – Komponenten referenzieren Komponenten, transitiv auflösbar.
5. **Verifiability** – jede Spec hat ausführbare Akzeptanzkriterien; Conformance-Tests laufen pro Ziel-Stack.
6. **Human + AI Co-Authoring** – Specs werden gemeinsam mit AI refined, mit klaren Diff-/Review-Workflows.
7. **Open Core** – Spec-Format und CLI Open Source; Hosting/Collaboration/Search als Service.

---

## Produkt-Oberfläche

> **Reihenfolge nach Refinement (2026-05-04)**: CLI + MCP-Server + Website/Playground bilden den Kern. Desktop-App ist **geparkt**. Visuelles Tooling kommt schrittweise nach echter Nutzung.

### ✅ CLI (`speccify`) – primäre Nutzungs-Oberfläche
- MVP-Befehle (Phase 1): `init`, `add`, `pull --target`, `lock`, `verify`, `publish`, `yank`, `search`, `lint`.
- Spätere Befehle (Phase 2+): `diff`, `why`, `outdated`, `workspace`.
- Integration in CI: `speccify verify` prüft Spec- *und* Output-Hashes (siehe Lockfile unten).
- Teilt Resolver-/Codegen-Logik mit dem MCP-Server (eine Implementierung, zwei Schnittstellen).

### ✅ Agent-API / MCP-Server – gleichberechtigt mit CLI, ab Phase 1
- MCP-Server, der jede Coding-Agent-Umgebung (Claude Code, Junie, Cursor, Aider) ans Registry anbindet:
  - `resolve(id)`, `search(query)`, `render(id, target)`, `validate(code, id)`, `lock`, `verify`.
- Macht „Agent ist der Compiler" erst erlebbar: derselbe Workflow für Menschen (CLI) und Agenten (MCP).
- **Bewusst in Phase 1**, nicht spät in Phase 5 (wie im ursprünglichen Plan).

### ✅ Website
- Discovery: Volltext + semantische Suche, Tags, Kategorien, Trending.
- Komponenten-Detailseite: Spec, Beispiele, Bildergalerie (Asset-Refs aus Spec), „Used by", Versionen, Forks.
- Profile, Organisationen, Teams (öffentlich / privat / unlisted).
- Refinement-Diskussionen pro Spec (issue-zentriert auf Spec-Ebene) — *Phase 5, nach echter Nutzung*.
- **Browser-Playground (Phase 1, parallel zum CLI)**: Spec eingeben → Live-Generierung in Ziel-Framework. Fast Abfallprodukt der Codegen-Pipeline + Website; beste Demo- und Onboarding-Oberfläche.
- Marketplace-Komponente (später): bezahlte/lizensierte Specs.

### 🅿️ Desktop-App (geparkt)
- Stack-Entscheidung **Tauri 2** bleibt dokumentiert, Bau aber **on-hold**.
- **Re-Aktivierungs-Kriterien**: ≥ 30 aktive Spec-Autoren *und* dokumentierter UX-Bedarf, der sich aus echter CLI-/Web-Nutzung herauskristallisiert (z. B. wiederkehrende Wünsche nach lokalem Multi-Target-Preview, Offline-Editor, Asset-Drag&Drop).
- Frühe Adopter (Engineers in Editor/Terminal/CI) brauchen die App nicht; Designer/PO werden erst sinnvoll co-authoren, wenn der Spec-Workflow belastbar ist.
- Tauri-/Rust-Lerngelegenheit fürs Team bleibt bestehen, nur eben nicht jetzt.

### Visuelles Tooling – nach Stufen sortiert
| Stufe | Was | Wann |
|---|---|---|
| a) Asset-Referenzen *in der Spec* (Screenshots, Wireframes als Bild-Links, Negativ-Beispiele) | **Phase 0** (Schema v0) | jetzt — trivial, gehört in Schema v0 |
| b) Visuelle Diff-/Galerie-Ansicht auf der Website | **Phase 5** | nachgelagert, nach echter Nutzung |
| c) Live-Preview / Multi-Target-Renderer im Editor | **Phase 5** | nachgelagert |
| d) Figma-Integration | **Phase 6+** | deutlich nachgelagert |

---

## Spec-Format (Entwurf)

```yaml
id: spec://login-with-otp
version: 1.4.0
kind: ui-workflow            # ui-component | logic | workflow
title: Login mit Einmal-Passwort
summary: >
  Login-Flow per E-Mail/Telefon und 6-stelligem OTP, inkl. Resend, Lockout
  nach 5 Fehlversuchen, Accessibility AA.
authors: [marc@speccify.io]
license: MIT

inputs:
  - name: identifier
    type: string
    constraints: [email | e164-phone]
outputs:
  - name: session
    type: ref://flow/session@^1
events:
  - name: otp_sent
  - name: login_failed
    payload: { reason: enum[invalid_otp, expired, locked] }

uses:
  - spec://otp-input@^1.0
  - spec://rate-limiter@^2

acceptance:
  - given: User gibt gültige E-Mail ein
    when: Submit gedrückt
    then: otp_sent emittiert, OTP-Eingabe erscheint binnen 300 ms
  - given: 5 falsche OTPs in Folge
    then: login_failed mit reason=locked, 15 min Sperre

ux:
  references:
    - figma://file/abc123?node=4:12
    - asset://screenshots/happy-path.png
    - asset://screenshots/error-locked.png   # Negativ-Beispiel
  a11y: WCAG-2.2-AA
  i18n: required (de, en)

non_functional:
  performance: "TTI < 2s auf 3G"
  security: ["keine OTPs im LocalStorage", "Rate-Limit serverseitig"]

conformance:
  fixtures: ./fixtures/*.json     # Input/Output-Paare, framework-agnostisch
  golden_renders:                  # optionale visuelle Snapshots pro Target
    swiftui: ./golden/swiftui/
    react: ./golden/react/
```

---

## npm-artiger Workflow konkret

> Vollständige Begründung der Designentscheidungen: [Package-Manager-Vergleich](archive/package-manager-comparison.md). Hier die Zusammenfassung als Vertrag für CLI, Registry und MCP.

### Was wir aus existierenden PMs übernehmen

| Designachse | Entscheidung | Vorbild |
|---|---|---|
| Identität | `@scope/name@version` + `sha256`-Pin | npm-Scopes + OCI-Digest |
| Namensschutz | reservierte/verifizierte Scopes, **registry-gebundene** Scopes (gegen Dependency Confusion) | npm + PyPI-Lehre |
| Versionierung | SemVer pflicht, **kein** Caret-Default | (negativ) npm |
| Resolver | **MVS – Minimum Version Selection**, deterministisch, kein Backtracking | Go |
| Lockfile | Hashes pflicht **+ Generator-Pin** (`model`, `prompt_version`, `seed`) **+ Output-Hashes** | Go + Speccify-eigen |
| Immutability | unveränderlich, nur `yank` mit Begründung | Maven + Cargo |
| Trust | sigstore-artige Signaturen, Transparency Log, 2FA pflicht | npm/PyPI 2024+ + Go |
| Distribution | Federation, registry-gebundene Scopes | Maven + PyPI-Lehre |
| Workspaces | nativ ab Phase 2 | Cargo + pnpm |

### Was wir bewusst NICHT übernehmen

Caret-Default (`^1.2.3`), `unpublish` < 72h, flat Namespace ohne Scope, Backtracking-Resolver mit Solver-Magie, Cargo-Regel „eine Version pro Build", Maven-Range-Syntax, Lockfile ohne Hashes.

### Speccify-spezifisch (kein anderer PM hat das)

1. **`--target`** als first-class-Bürger jeder Operation (`pull`, `verify`, `lock`).
2. **Generator-Pin** im Lockfile → reproduzierbarer *Output*, nicht nur reproduzierbare Auflösung.
3. **Conformance-Tests pro Target** als Vertrag (statt API-Kompatibilität).
4. **MCP-Resolver** gleichberechtigt zur CLI.
5. **Doppelter Hash** im Lockfile: Spec-Bundle UND generierte Dateien.

### `speccify.lock` (Auszug)

Generator-Pin in zwei Varianten:

```yaml
# Variante A (Phase 1a, deterministisch ohne API-Keys): Template-Pin
- id: "@org/button"
  version: 0.1.0
  sha256: "sha256:…spec-bundle-digest…"
  resolved_via: "registry-fixtures"
  target: react
  generator:
    kind: template
    template_set: phase-1a-stub
    template_version: 0.1.0
  generated_files_sha256:
    - path: org/button.md
      sha256: "sha256:…"

# Variante B (Phase 1b+, sobald LLM-Codegen stabil ist): Modell-Pin
- id: "@org/login-with-otp"
  version: 1.4.0
  sha256: "sha256:…spec-bundle-digest…"
  resolved_via: "registry.speccify.io"
  target: react
  generator:
    kind: llm
    model: claude-sonnet-4.5-2026-03
    prompt_version: 7
    seed: 1234
  generated_files_sha256:
    - path: src/Login/LoginView.tsx
      sha256: "sha256:…"
```

Begründung: deterministische Templates sind in CI ohne API-Keys reproduzierbar; das Lockfile-Format ist so gestaltet, dass der LLM-Pin nahtlos hinzukommt, sobald der Resolver/Lockfile-Vertrag stabil ist.

### So fühlt sich der Workflow an

```bash
# Initialisieren
speccify init my-app --target swiftui

# Spec hinzufügen (schreibt in speccify.yaml + speccify.lock)
speccify add @org/login-with-otp@1.4.0

# Code generieren
speccify pull --target swiftui --out ./Sources

# Lockfile reproduzierbar prüfen (CI)
speccify verify

# Eigene Spec publishen (immutable, signiert)
speccify publish

# Aus einem Coding-Agent heraus (MCP):
#   resolve(@org/login-with-otp@^1) → render(target=swiftui) → validate(code, id)
```

### Offene Punkte (vor Phase 2 zu klären)

Yank-Politik im Detail (Grace-Period, Auto-Yank bei CVE), Pre-Release-Workflow, Modell-Drift bei EOL-Modellen, Diamond-Specs in MVS, konkrete Mechanik der registry-gebundenen Scopes — siehe Vergleichsdokument, Sektion 6.

---

## Technologie-Stack

| Komponente | Technologie | Begründung |
|---|---|---|
| Spec-Format | YAML + JSON-Schema + Markdown-Sektionen | Lesbar, validierbar, diff-bar |
| Backend / Registry | Django + Postgres + S3 (Assets) | Bestehende Erfahrung im Team, schneller Start |
| Search | OpenSearch + Embeddings (FAISS) | Volltext + semantisch |
| Web-Frontend | Next.js / SvelteKit | Modernes SSR, Playground im Browser |
| 🅿️ **Desktop-App** *(geparkt)* | **Tauri 2** (Rust + System-WebView: WKWebView/WebView2/WebKitGTK) | Stack-Entscheidung dokumentiert; Bau aufgeschoben, siehe Phase 4 |
| 🅿️ Desktop-Frontend-Stack *(geparkt)* | SvelteKit oder Next.js (statisch) + CodeMirror/Monaco | Editor-/Diff-/Renderer-Komponenten 1:1 mit der Website teilen |
| 🅿️ Desktop-Backend (Rust) *(geparkt)* | `serde_yaml`, `jsonschema`, `git2`, `tokio`, Tauri-Plugins (`fs`, `dialog`, `updater`, `stronghold`, `sql`) | Schnelle, sichere lokale Validation, Git-Sync, Secrets, Auto-Update |
| Agent-Bridge | MCP-Server (Python/Node) | Standard-Protokoll für Coding-Agents |
| Code-Generierung | Claude/GPT + framework-spezifische Prompts | Best-of-Breed pro Target |
| Conformance-Runner | Docker + Playwright + Snapshot-Tests | Pro Target ein Container |
| Auth | OAuth (GitHub/GitLab) | Niedrige Hürde |
| Hosting | AWS (analog Agent-Fundamentals) | Vorhandene DevOps-Pipeline |

---

## Phasen-Roadmap

> **Refinement 2026-05-04**: Phasen umsortiert. CLI + MCP + ein Codegen-Target + Browser-Playground bilden zusammen Phase 1. Desktop-App (alte Phase 4) **geparkt**. Visuelles Tooling und Refinement-Diskussionen erst nach echter Nutzung.

### Phase 0: Spec-Schema v0 + Lint
- Spec-Schema v0 finalisieren, JSON-Schema veröffentlichen.
- Asset-Refs (Screenshots/Wireframes/Negativ-Beispiele) als first-class im Schema.
- 5 Referenz-Specs handgeschrieben (1 Button, 1 Form, 1 API-Client, 1 Workflow, 1 Screen).
- Validator-CLI (`speccify lint`).

### Phase 1: CLI-MVP + MCP + ein Codegen-Target + Playground

Phase 1 ist im Refinement 2026-05-06 in vier Sub-Spikes zerlegt worden, damit jeder Vertrag (Resolver/Lockfile, echtes Codegen, MCP, Playground) für sich validierbar bleibt:

- **Phase 1a** (Resolver/Lockfile/Stub-Codegen, abgeschlossen 2026-05-06): MVS-Resolver, `speccify.yaml`/`speccify.lock`, deterministisches Stub-Codegen (Template-Pin), CLI `lock`/`add`/`pull`/`verify`, lokales Pseudo-Registry. Plan: [`.agent/plans/phase-1a-resolver-lockfile.md`](phase-1a-resolver-lockfile.md).
- **Phase 1b** (React-LLM-Codegen + `speccify init`, abgeschlossen 2026-05-13): LLM-basierter React-Codegen (TSX mit Props/Types pro Spec) statt Stub-Markdown. Modell-Pin `bedrock/eu.anthropic.claude-opus-4-7` via AWS Bedrock `converse`; Reproduzierbarkeit über Replay-Cache (`tests/fixtures/llm-cache/`, Cache-Key über `spec_sha256 + target + model + prompt_version + seed`). Lockfile-Generator-Pin um `kind: llm` erweitert (`provider`, `model`, `prompt_version`, `seed`, `cache_key`). `pull`/`verify` mit `--offline/--cache-dir` Flags; CI läuft komplett offline gegen den eingecheckten Cache (E2E-Smoke: `example-project` + frischer `init`+`add`+`lock`+`pull`+`verify`-Pfad). Live-Aufnahme via `scripts/record_llm_cache.py` (Maintainer-Tool). Erstes Ziel-Framework ist React (statt SwiftUI), weil der Phase-1d-Browser-Playground mit React-Output direkt live geht; SwiftUI bleibt zweites Target in Phase 3. Plan: [`.agent/plans/phase-1b-react-codegen.md`](phase-1b-react-codegen.md). Tag-Vorschlag: `v0.2.0-phase-1b`.
- **Phase 1c** (MCP-Server `speccify-mcp`, abgeschlossen 2026-05-16): Dünner Adapter über `speccify-core`, der `speccify-cli`-Workflows ans Model-Context-Protocol bindet. Transport ausschließlich `stdio` (HTTP/SSE erst in Phase 2). **Tools** (spiegeln CLI 1:1, byte-identische Outputs via Cross-Consistency-Test): `lint(spec_path)`, `resolve(manifest_path?)`, `render(spec_id, target, offline?, cache_dir?)`, `lock(manifest_path?)`, `pull(manifest_path?, out_dir, offline?, cache_dir?)`, `verify(manifest_path?, out_dir, offline?, cache_dir?)`. `verify` liefert strukturiert `{ok, problems}` (Drift ist Antwort, kein MCP-Error). **Resources**: `speccify://manifest`, `speccify://lockfile` (Hint-Kommentar wenn Datei fehlt), Template `spec://{scope}/{name}@{version}` (YAML-Bytes via `LocalRegistry.fetch`). **Prompts**: `add-spec(spec_ref, out_dir=./src/components)` rendert `resolve` → `lock` → `pull` → `verify`-Anleitung. **Defaults**: `--offline` aktiv, Cache-Pfad via `SPECCIFY_CACHE_DIR` (Default eingecheckter Repo-Cache); Project-Root via `--project`/`SPECCIFY_PROJECT_ROOT` als Startup-Argument, Server stateless zwischen Calls. **Smoke** (`scripts/mcp_smoke.py`, CI-Step `speccify-mcp smoke (stdio, offline)`): MCP-Handshake + `tools/list` + `tools/call render` + `resources/read manifest`, alle Bedrock-Creds gestrippt. Plan: [`phase-1c-mcp-server.md`](phase-1c-mcp-server.md). Tag-Vorschlag: `v0.3.0-phase-1c`.
- **Phase 1d** (Browser-Playground `apps/web/`, abgeschlossen 2026-05-19): FastAPI-Backend `speccify-web-backend` (in-process über `speccify-core`, offline gegen den eingecheckten Replay-Cache) + Next.js 15 / React 19 / TypeScript-Frontend (pnpm@10.33.3, Node ≥22 LTS) mit Spec-Picker, Monaco-YAML-Editor, Render-Output (TSX + `generator_pin`-Detail) und Error-Panel (`cache_miss`-Hint). **Tool-Vertrag `/api/v1/...`**: `GET /api/v1/specs` → Liste `{id, version, title, yaml}` aus der lokalen Pseudo-Registry (Default `<repo>/registry-fixtures/`, override via `SPECCIFY_REGISTRY_PATH`); `POST /api/v1/render` mit Body `{spec_id, version, spec_yaml, target}` → `{files, generator_pin}` aus `speccify_core.render_for_target` mit `ReplayCacheClient(offline=True)`. **Fehler-Codes** (identisch zu CLI/MCP): `cache_miss` (422, mit Maintainer-Hint auf `scripts/record_llm_cache.py`), `spec_invalid` (400, YAML-/Schema-Fehler), `unknown_target` (400), `bad_request` (400). **Cross-Consistency** als Vertrag: `apps/web/backend/tests/test_cross_consistency.py` rendert `@org/button@0.1.0` über `speccify_cli.commands.pull.run_pull`, `speccify_mcp.tools.run_pull` und `speccify_web_backend.services.render.render_spec_from_yaml` und vergleicht `org/Button.tsx`-Bytes byte-identisch — damit ist das Dreieck CLI ↔ MCP ↔ Web geschlossen. **Limitierungen**: nur Target `react`, ausschließlich offline gegen den eingecheckten Replay-Cache (kein Live-LLM), keine Persistenz, keine Auth, kein Upload (Editor zeigt Cache-Miss-Pfad bewusst als Demo). **CI**: zwei neue Jobs `apps/web backend (offline)` (`uv run pytest apps/web/backend/tests`) und `apps/web frontend build` (`pnpm install --frozen-lockfile` + `pnpm typecheck` + `pnpm build`); Playwright-E2E bewusst nicht eingebaut (Aufwand vs. Mehrwert gegenüber Cross-Consistency-Test, bleibt für Phase 2 offen). Plan: [`phase-1d-browser-playground.md`](archive/phase-1d-browser-playground.md). Tag-Vorschlag: `v0.4.0-phase-1d`.

- **CLI-MVP**: `init`, `add`, `pull --target`, `lock`, `verify`, `publish`, `yank`, `search`, `lint`.
- **MCP-Server** (gleiche Resolver-/Codegen-Logik wie CLI): `resolve`, `search`, `render`, `validate`, `lock`, `verify`.
- **`speccify.lock`** mit Hashes + Generator-Pin (Phase 1a: `kind: template`; ab 1b zusätzlich `kind: llm` mit Modell/Prompt-Version/Seed) + Output-Hashes.
- Demo: Junie/Claude Code zieht `@org/...` via MCP und baut eine React-Komponente.

### Phase 2: Registry-MVP
- Django-Backend: Komponenten anlegen, versionieren, suchen, `yank`.
- Web-UI: Detailseite, Suche, Profile, Versionen.
- Workspaces (Cargo-/pnpm-artig) nativ.
- Vorbereitung sigstore-Signaturen + Transparency Log; 2FA pflicht für Publish.
- Federation vorgesehen, registry-gebundene Scopes.

### Phase 3: Zweites + drittes Codegen-Target, Conformance-Runner
- SwiftUI und Angular als Targets (oder Jetpack Compose, je nach Pilot-Use-Case). React ist bereits in Phase 1b geliefert.
- Conformance-Runner pro Target: Docker + Playwright + Snapshot-Tests.
- Conformance-Tests aus `acceptance` automatisch generieren.

### Phase 4: 🅿️ Desktop-App – Tauri (geparkt)
- **Re-Aktivierungs-Kriterien**: ≥ 30 aktive Spec-Autoren *und* dokumentierter UX-Bedarf aus echter Nutzung.
- Stack-Plan (Tauri 2 + Rust + SvelteKit/Next.js, Plugins, Cross-Platform-Builds, Code-Signing, Rust-Lernpfad) bleibt unverändert dokumentiert; nur die Umsetzung ist on-hold.
- Plan B (SwiftUI-Shell + WebView) ebenfalls weiter dokumentiert, falls Tauri sich später als ungeeignet erweist.

### Phase 5: Visuelles Tooling + Refinement-Workflows (nach echter Nutzung)
- Visuelle Diff-/Galerie-Ansicht auf der Website.
- Live-Preview / Multi-Target-Renderer im (Web-)Editor.
- Co-Authoring im Editor, AI-„Lückenfinder", Diff-Tool zwischen Spec-Versionen.
- Refinement-Diskussionen pro Spec (issue-zentriert).
- Kriterium für den Start: ≥ 20–50 echte Specs aus produktivem CLI-/MCP-Einsatz, damit visuelles Tooling sich an realen Lücken orientiert.

### Phase 6: Community & Discovery
- Tags, Kategorien, „Used by", Forks, Likes.
- Semantische Suche (Embeddings über Spec-Inhalt).
- Erste 100 öffentliche Specs als Saatgut.
- Figma-Integration (deutlich nachgelagert).

### Phase 7: Polish & Launch
- Dokumentation, Quickstart-Videos, Beispiel-Apps in 3 Stacks.
- Beta-Programm, Launch auf HN / X / LinkedIn.

---

## Erfolgsmetriken

- **Determinismus**: Wie ähnlich sind Outputs verschiedener Agenten für dieselbe Spec? (Strukturelle Diff-Distanz)
- **Coverage**: Anteil Specs, deren Conformance-Tests in ≥3 Targets grün laufen
- **Time-to-Component**: Sekunden von „speccify pull" bis lauffähiger Code
- **Refinement-Loop-Länge**: durchschnittliche Iterationen, bis eine Spec „agent-ready" ist
- **Community-KPIs**: aktive Autoren, neue Specs/Woche, Pulls/Woche

---

## Differenzierung

| | Speccify | npm/Maven | Storybook | Figma | OpenAPI |
|---|---|---|---|---|---|
| Sprach-/Framework-unabhängig | ✅ | ❌ | ❌ | ✅ (nur UI) | ✅ (nur APIs) |
| Inkl. UX, Logik, Workflow | ✅ | – | UX | UX | Logik |
| AI-Agent als „Compiler" | ✅ Kern | ❌ | ❌ | ❌ | teilweise (Codegen) |
| Komposition über IDs | ✅ | ✅ | – | – | ✅ |
| Visuelle + textuelle Refs | ✅ | ❌ | ✅ | ✅ | ❌ |

---

## Risiken & offene Fragen

- **Determinismus zwischen LLM-Versionen**: Wie sichern wir, dass eine Spec auch in 2 Jahren noch zu konsistentem Code führt? → Conformance-Tests + gepinnte Modelle pro Spec-Version.
- **Spec-Komplexität vs. Schreibhürde**: Wie verhindern wir, dass Specs schreiben *aufwendiger* wird als Code schreiben? → AI-Co-Author + Templates + „minimal viable spec".
- **Visuelle Referenzen rechtssicher**: Hosting-Strategie für Bilder/Figma-Embeds.
- **Lizenz-Modell**: MIT/Apache für Specs? Dual-Lizenz für Marketplace?
- **Wer „besitzt" eine Komponente?**: Forking-Modell (à la GitHub) vs. zentrales Registry.
- **Naming**: `speccify` final? Domain-Check, Markenrecht.
- **Plattform-Strategie**: SaaS-only oder self-hosted Edition?
- **Rust-Lernkurve im Team / WebKitGTK / Mac-Native als Fallback**: Durch das Parken der Desktop-App (Phase 4) aktuell entschärft. Bleibt für die Re-Aktivierung dokumentiert.
- **UI-lastige Komponenten ohne visuelle Refs**: Im CLI-/MCP-only-Workflow reichen Asset-Refs in der Spec eventuell nicht für stark visuelle Komponenten. → Bewusst akzeptierter Trade-off in der Frühphase; visuelles Tooling kommt in Phase 5, sobald reale Lücken bekannt sind.
- **Modell-Drift bei gepinntem LLM**: Wenn ein in `generator.model` gepinntes Modell EOL geht, brauchen wir ein Migrations-Tool. Offener Punkt aus dem PM-Vergleich.

---

## Was sich am ehesten zuerst lohnt zu bauen (Spike-Vorschlag)

> Geschärft im Refinement 2026-05-04: ein Codegen-Target statt drei, dafür CLI **und** MCP, damit „Agent ist der Compiler" sofort erlebbar ist.

1. Spec-Schema v0 (YAML + JSON-Schema), inkl. Asset-Refs.
2. **Eine** handgeschriebene Spec für eine nicht-triviale Komponente (z. B. Date-Range-Picker mit i18n, a11y, Edge-Cases).
3. **Eine** Codegen-Pipeline: SwiftUI (Entscheidung im Refinement).
4. CLI-MVP (`init`, `add`, `pull --target`, `lock`, `verify`) mit `speccify.lock` inkl. Generator-Pin.
5. **MCP-Bridge**, die dieselbe Resolver-/Codegen-Logik exponiert.
6. Conformance-Test-Runner für die SwiftUI-Pipeline.
7. Demo: aus Junie/Claude Code heraus per MCP `resolve → render(target=swiftui) → validate` → lauffähige Komponente → **interner Pitch**.

Wenn dieser Spike die Hypothese stützt („Spec + Agent = reproduzierbarer Code, vom Menschen wie vom Agent ausgelöst"), lohnt sich Phase 2 ff.

---

## Inspirationen / verwandte Arbeiten

- **OpenAPI / AsyncAPI** – Spec-First für APIs, hat Code-Gen-Tooling etabliert
- **JSON Schema, Protobuf, GraphQL SDL** – sprachunabhängige Typsysteme
- **Storybook** – komponenten-zentriertes Authoring (aber framework-gebunden)
- **Figma + Tokens Studio** – visuelle Spezifikation, fehlt Verhalten/Logik
- **Penpot, Plasmic** – Design-zu-Code, aber framework-spezifisch
- **MCP (Model Context Protocol)** – Standard, um Agenten Werkzeuge bereitzustellen
- **Spec-Driven Development** (z. B. Cursor Rules, AGENTS.md, AGENT_SPEC) – wachsender Trend, noch ohne zentrales Registry

---

## Neue Ideen / Brainstorm (offen)

- **Spec-Linting durch LLM-Jury**: 3 verschiedene Modelle bewerten Spec-Qualität, Score 0–100.
- **Visuelle Diff-Ansicht** zwischen Spec-Versionen (gerenderte Vorschauen nebeneinander).
- **„Trust Score" pro Spec** basierend auf: Conformance-Tests grün in N Targets, Anzahl produktiver Nutzungen, Reviews.
- **Federation**: jedes Team hostet eigenes Registry, speccify.io indexiert (à la PyPI + private Indexe).
- **Spec-Templates pro Domäne**: E-Commerce, Finanzen, IoT … vorgefertigte Kompositionen.
- **„Generative UI"-Pfad**: Spec liefert nicht nur Code, sondern zur Laufzeit gerenderte UI über einen Runtime-Interpreter (für Prototyping).
- **Time-Machine**: ältere Spec-Version mit aktuellem Modell neu generieren → wird sie besser?
- **Reverse-Mode**: bestehenden Code → Kandidaten-Spec extrahieren („spec-ify this component").
- **Education**: kostenlose Kurse „Wie schreibt man eine gute Komponenten-Spec?" → Funnel.

---

## Vorarbeiten / Klären, bevor wir loslegen

- [x] Domain `speccify.io` gesichert (Markenrecherche steht aus)
- [x] Package-Manager-Designentscheidungen geklärt → [Package-Manager-Vergleich](archive/package-manager-comparison.md)
- [ ] Repo anlegen (eigenständig, getrennt vom Agent-Fundamentals-Projekt)
- [ ] Spec-Schema v0 als JSON-Schema veröffentlichen (Phase 0)
- [ ] CLI-/MCP-Spike (siehe Spike-Vorschlag) – Go/No-Go für Phase 2 ff.
- [ ] 3–5 Use-Cases als Saatgut definieren (Team / Kundenprojekte)
- [ ] Pitch-Deck (8–10 Slides) auf Basis dieses Plans
- 🅿️ *Geparkt mit Desktop-App*: Tauri-Spike, Rust-Lernpfad fürs Team, Plan B (SwiftUI-Shell)
