---
sessionId: session-260524-171600-3a
isActive: true
---

# Requirements

## Phase-3-Ziel: Zweites + drittes Codegen-Target + Conformance-Runner + Workspaces

Phase 1b hat **React** als erstes echtes Codegen-Target geliefert. Phase 2 hat den **Registry-MVP** gebaut (Publish/Fetch/Yank/Search/Web-UI/Resolver-Remote). In Phase 3 wird das Codegen-Ökosystem **multi-target**: aus einer `speccify.yaml`-Spec entstehen deterministisch Komponenten für **mindestens zwei weitere Targets** plus ein **Conformance-Runner**, der pro Target prüft, dass das generierte Artefakt die Akzeptanzkriterien der Spec tatsächlich erfüllt. Ergänzend zieht **Workspaces** aus Phase 2 nach: ein `workspaces: [...]`-Feld im Manifest erlaubt Mono-Repos mit mehreren Manifesten (Cargo-/pnpm-Parität).

Aus dem Master-Plan: „SwiftUI und Angular als Targets (oder Jetpack Compose, je nach Pilot-Use-Case). React ist bereits in Phase 1b geliefert. Conformance-Runner pro Target: Docker + Playwright + Snapshot-Tests."

## In Scope

- **Zweites Codegen-Target** (Pilot, Stack-Auswahl in Stage 0): voller Codegen-Pfad analog zu React — Renderer in `codegen/`, Template-/Prompt-Replay-Cache, Golden Renders pro Referenz-Spec, byte-identische Determinismus-Tests.
- **Drittes Codegen-Target**: zweiter Renderer im selben Pattern, um zu beweisen, dass die Codegen-Abstraktion „target-agnostisch" trägt (keine target-spezifische Sonderlogik in `speccify_core`).
- **Conformance-Runner pro Target**: dockerisierter Test-Harness, der pro Target das generierte Artefakt baut und gegen die `acceptance_criteria` der Spec prüft (Snapshot- und/oder interaktive Tests, je nach Target).
- **Workspaces**: `workspaces: [path/glob]` im Manifest; CLI-Commands (`lock`/`pull`/`verify`) iterieren über alle Member-Manifeste; Lockfile-Layout entscheidet Stage 0 (ein zentrales Root-Lockfile vs. ein Lockfile pro Member, analog Cargo/pnpm).
- **Multi-Target im Manifest**: heute `target: react`; künftig `targets: [react, swiftui]` oder Manifest-pro-Target — Stage 0 entscheidet.
- **CI**: Conformance-Runner-Jobs pro Target (Docker-basiert; Caching via GitHub Actions Cache).
- **Master-Plan-/AGENTS-Sync** + Phase-3-Archiv + Tag-Vorschlag `v0.6.0-phase-3` am Ende.

## Out of Scope (bewusst vertagt)

- **Federation / Marketplace** (`speccify.io`-Index, registry-gebundene Föderation) — Phase 4+.
- **Volle sigstore-Verifikation + Transparency-Log** (Phase 2 hat den Slot, die Signatur-Pipeline kommt später).
- **WebAuthn / Hardware-Keys** (Phase 2 = TOTP-only).
- **OAuth-Login** (Phase 2 = Device-Code, Phase 6 nach Master-Plan).
- **Desktop/Tauri-Tooling** (Phase 4 weiterhin on-hold).
- **Visuelles Authoring** (Phase 5+).
- **Echte Live-Domain / Hosted-Registry** (bleibt Phase 4 + Infra-Entscheidung).

## Erfolgskriterien

1. **Mindestens zwei neue Targets** liefern für die fünf Phase-0-Referenz-Specs ein deterministisches Artefakt (zwei `pull`-Aufrufe → byte-identisch).
2. **Conformance-Runner** läuft pro Target lokal (`uv run` / Docker) und in CI; Pflicht-Akzeptanzen aus der Spec werden geprüft.
3. **Workspaces**: ein Workspace mit ≥ 2 Member-Manifesten lässt sich locken, pullen und verifyen; `verify` schlägt zuverlässig bei Drift in **einem** Member fehl.
4. **Cross-Consistency** für jedes neue Target: CLI ↔ MCP ↔ Web (Render-Endpoint) liefern byte-identische Artefakte (analog Phase-1d-Vertrag).
5. **CI grün** auf allen neuen Jobs; bestehende Jobs unverändert.


# Architecture & Decisions

## Open Questions Round 1 (Stage 0 vor Code-Stages)

Bevor wir Delivery-Stages konkretisieren, müssen folgende Punkte mit dem User geklärt werden. Reihenfolge entspricht der Klärungspriorität: 1–4 sind blocker für jeglichen Code; 5–10 lassen sich später ohne Re-Work nachholen.

1. **Zweites Target (Pilot)** — SwiftUI, Angular oder Jetpack Compose? Auswahlkriterien: (a) Pilot-Use-Case, (b) Reichweite der Spec-Sprache (Inputs/Outputs/Events), (c) Test-Harness-Aufwand. Master-Plan-Tendenz: „SwiftUI **oder** Angular **oder** Jetpack Compose, je nach Pilot-Use-Case".
2. **Drittes Target** — die beiden anderen aus 1, oder zuerst nur **eines** voll fertig + Conformance-Runner und das dritte als Folge-Phase? Risiko-Tradeoff: Tiefe vs. Breite.
3. **Conformance-Runner-Stack** — Docker + Playwright (Web-Targets), Docker + Xcode-Simulator (SwiftUI), Docker + Espresso/Robolectric (Compose). Ein gemeinsames Harness-Konzept oder pro Target eigene Toolchain?
4. **Workspaces-Layout** — ein zentrales `speccify.lock` im Workspace-Root (Cargo-Stil) oder ein Lockfile pro Member (pnpm-Stil)? Auswirkungen auf Determinismus, Drift-Erkennung, `add`/`remove`-Semantik.
5. **Multi-Target im Manifest** — `targets: [react, swiftui]` (Liste, Cross-Product im Lockfile) **oder** ein Manifest pro Target (`speccify.yaml` + `speccify.swiftui.yaml`) **oder** Target erst zur `pull`-Zeit via Flag? Konsequenz für Lockfile-Schema (Phase-2-`schema_version: 2` → ggf. v3).
6. **Codegen-Modus pro Target** — `kind: template` (Jinja-Templates) wie React in Phase 1b, oder `kind: llm` mit Replay-Cache (analog Phase 1d Playground-Backend)? Pro Target getrennt entscheidbar.
7. **Golden-Renders pro Target** — `tests/fixtures/golden/<target>/<scope>/<name>.<ext>` als Snapshot-Quelle (Phase-1b-Pattern fortführen) oder Conformance-Runner-Output als Single-Source-of-Truth?
8. **Visuelles Referenz-Material in Specs** — Phase-0-Schema erlaubt `screenshots[]`. Sollen Conformance-Runner diese als Pflicht-Eingabe behandeln (z. B. Visual-Regression) oder bleibt das informativ? Master-Plan-Tendenz: Conformance-Runner = funktional, Visual-Regression später.
9. **Workspaces-Resolver-Semantik** — bei zwei Membern, die dieselbe Spec mit unterschiedlichen Versionen ziehen: globale MVS-Auflösung (eine Version für alle Member, Cargo-Stil) oder pro Member separat (pnpm-Stil mit potenziell mehreren Versionen koexistierend)?
10. **MCP-Tools für neue Targets** — bestehende Tools (`render`, `pull`, `verify`) target-agnostisch erweitern, **oder** pro neuem Target ein zusätzliches Convenience-Tool (`render_swiftui` etc.)? Master-Plan-Tendenz: bestehende Tools target-agnostisch belassen, Target via Argument.

## Decisions (werden in Stage 0 mit User-Antworten aufgefüllt)

> Stand: **offen** — Stage 0 = Klärung der 10 Open Questions. Round-2-Delivery-Steps (Stages 1ff.) folgen erst, wenn diese Entscheidungen dokumentiert sind.


# Delivery Stages

## Stage 0: Open Questions klären + Decisions festschreiben

- 10 Open Questions strukturiert mit User durchgehen.
- Antworten als `Decisions`-Block in „Architecture & Decisions" schreiben (kein Code).
- Round-2-Delivery-Steps (Stages 1ff.) konkretisieren — Reihenfolge, Test-Strategie pro Target, CI-Job-Skizze, Lockfile-Schema-Bump (falls nötig), Workspaces-CLI-Vertrag.
- Outcome: Plan-Datei mit klaren Delivery-Stages für die Code-Arbeit.

## Stage 1+: tbd nach Stage 0

> Skelett-Marker — wird in Stage 0 anhand der User-Decisions konkretisiert. Grobe erwartete Reihenfolge (kann sich nach Stage 0 ändern):
>
> 1. Codegen-Abstraktion härten (Renderer-Interface, Target-Registry in `speccify_core`).
> 2. Zweites Target (Stack aus Stage 0) — Renderer + Tests + Golden Renders.
> 3. Conformance-Runner-Skelett (gemeinsamer Harness oder erstes target-spezifisches Harness).
> 4. Drittes Target — Renderer + Tests + Golden Renders.
> 5. Conformance-Runner pro Target voll ausbauen + CI-Jobs.
> 6. Workspaces (`workspaces: [...]`-Feld, CLI-Iteration, Lockfile-Layout).
> 7. Cross-Consistency-Erweiterung CLI ↔ MCP ↔ Web auf alle drei Targets.
> 8. Master-Plan-Sync + AGENTS.md + Phase-3-Archiv + Tag-Vorschlag `v0.6.0-phase-3`.


# Status Tracker

| Stage | Outcome | Status |
|---|---|---|
| 0 | Open Questions geklärt, Decisions dokumentiert, Round-2-Delivery-Steps geschrieben. | Open |
| 1+ | tbd nach Stage 0. | tbd |


# Risks & Mitigations

| Risiko | Wahrscheinlichkeit | Mitigation |
|---|---|---|
| **Conformance-Runner-Stack zu komplex** (z. B. Xcode-Simulator in Docker auf CI) | hoch | Stage 0 klärt pro Target realistische Harness-Optionen; Fallback ist „nur Snapshot-Vergleich + Build-Smoke" statt vollwertige Interaktions-Tests. |
| **Multi-Target-Manifest bricht Phase-1b-Pull-Semantik** | mittel | Lockfile-Schema-Bump (v2 → v3) mit Backward-Compat-Migration (analog Phase-2-v1→v2-Migration). Stage 0 entscheidet das Layout vor Code. |
| **Workspaces-Resolver-Diamonds über Member** | mittel | Stage 0 fixiert Semantik (global MVS vs. per-member); ConflictError mit Source-Trace bleibt aus Phase 1a. |
| **Cross-Consistency mit 3 Targets × CLI/MCP/Web wächst quadratisch** | mittel | Parametrierte Pytest-Tests statt N×M handgeschriebene Pfade. |
| **Determinismus von LLM-Targets** (falls `kind: llm` für ein Target gewählt wird) | hoch | Replay-Cache-Pattern aus Phase 1d wiederverwenden; Offline-Mode-CI-Job ist Pflicht. |
| **Phase-3-Scope explodiert** | hoch | Stage 0 entscheidet 2 vs. 3 Targets in Phase 3 (Frage 2); Workspaces kann notfalls in eine Phase 3a/3b geteilt werden. |
