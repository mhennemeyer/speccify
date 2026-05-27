---
sessionId: session-260527-084420-cdqd
isActive: false
---

# Status — Phase 4 abgeschlossen (2026-05-27)

**Alle 9 Steps Done.** Tag-Vorschlag an User: `v0.7.0-phase-4` (selbst nicht gesetzt, vgl. `rules.md`).

### Was geliefert wurde

- **Stage 0**: 10 Open Questions vom User beantwortet, Decisions im Plan verankert (siehe Block unten).
- **Stage 1**: `Workspace.lock(registry) -> Lockfile` in `core/src/speccify_core/workspace.py` — kanonischer Workspace-Aggregat-Pfad; 3 neue Tests in `core/tests/test_workspace.py` (Happy-Path, leere-Targets-Error, Range-Konflikt).
- **Stage 2**: `cli/src/speccify_cli/commands/lock.py` delegiert im Workspace-Modus an `workspace.lock()` (Duplikat-Logik entfernt).
- **Stage 3**: `cli/src/speccify_cli/commands/pull.py` workspace-aware; materialisiert pro Member nach `<member>/speccify_generated/<target>/`. `--target` im Workspace-Modus verboten. Helper `_render_lock_entry_into()` aus Single-Project-Schleife extrahiert.
- **Stage 4**: `cli/src/speccify_cli/commands/add.py` mit `--member/-m`-Flag + CWD-Detection (`_resolve_workspace_target_dir`); nach Member-Update wird `Workspace.lock()` auf Root neu ausgeführt.
- **Stage 5**: `cli/src/speccify_cli/commands/verify.py` mit `_run_workspace_verify()` — Hash-only Verify (Member-Deps ⊆ Root-Lockfile + Disk-Hash-Vergleich gegen `<member>/speccify_generated/<target>/`). Kein Re-Render, kein LLM-Pin-Check.
- **Stage 6**: Bestehende `ResolverError`-Diagnose (Spec-Id + Member-Pfade + Ranges + verfügbare Versionen) ist bereits exzellent; Snapshot-Test pinnt das Message-Format. **MCP-Bridge**: alle drei Write-Tools (`lock`/`pull`/`verify`) bekommen optionalen `workspace_root`-Parameter; im Workspace-Modus delegieren `pull` und `verify` an die CLI-Implementierungen (Single-Source-of-Truth). 2 neue MCP-Tests (`test_mcp_workspace_lock_pull_verify_smoke`, `test_mcp_workspace_pull_rejects_target_arg`).
- **Stage 7**: `docs/workspaces.md` (193 LOC) mit vollständigem CLI-Walkthrough, Konflikt-Beispiel, MCP-Integration, Design-Entscheidungen + Tests-Verweisen. README um Workspaces-Link + Phase-3/4-Archivlinks ergänzt.
- **Stage 8**: Plan-Archivierung (diese Datei → `archive/phase-4-workspaces.md`), AGENTS.md + resume.md aktualisiert.

### Verifikation

- **Root-Pytest**: **312 passed** (+19 ggü. Phase 3 = 293).
- **Registry-Pytest**: **119 passed** (unverändert).
- **Gesamt: 431 Tests grün.**
- `ruff check` → All checks passed.
- `ruff format --check` → 141 files already formatted.

# Übersicht

### Ziel

Phase 4 macht **Cargo-Style Workspaces** produktiv. Die Grundstruktur (`Workspace.load`, `WorkspaceMember`, `aggregated_targets`, `aggregated_dependencies`, `example-workspace/packages/{forms,ui}`) existiert seit Phase 3 — Phase 4 baut den vollständigen Iterations-Workflow drumherum: `lock` aggregiert Root-Lockfile mit globaler MVS, `pull` materialisiert pro Member, `add` schreibt in den richtigen Member, `verify` validiert cross-member, plus klare Conflict-Resolution-UX bei Versionskonflikten.

### Scope (per User-Entscheid)

- **In Scope**: Workspace-Iteration (`add`/`lock`/`pull`/`verify`) cross-member, Conflict-Resolution-UX, Multi-Member-Lockfile-Aggregation, Doku + Tests.
- **Out of Scope** (verschoben in Phase 5+): Conformance-Backends Build-Smoke + Visual-Regression, 75-Pfad-Cross-Consistency-Sweep mit echtem Bedrock-Cache, Tauri/Desktop (per AGENTS.md weiterhin on-hold).

### Plan-Stil

Wie Phase 3: **Stage 0 = Open Questions** zuerst; Stages 1–N folgen erst, wenn die Decisions geklärt sind. Daher unten nur ein Stages-Skelett — die endgültige Stage-Reihenfolge und Details werden nach Stage-0-Beantwortung im Plan-Dokument festgeschrieben.

### Tag-Gate

Phase 4 endet mit Tag-Vorschlag **`v0.7.0-phase-4`** (User setzt selbst, vgl. `rules.md`).

# Bestand (Investigation)

### Existierender Code aus Phase 3

- `core/src/speccify_core/workspace.py` (146 LOC) — `WorkspaceMember`, `Workspace.load(root)`, `aggregated_targets()`, `aggregated_dependencies()`. **Bereits implementiert**: Member-Discovery via Glob (`workspaces: - packages/*`), Target-Union, Dep-Union mit Range-Intersection (= globale MVS-Vorstufe).
- `cli/src/speccify_cli/commands/_workspace.py` (45 LOC) — `WorkspaceContext.load(project_dir, registry_override)`. **Single-Member-Sicht**; aggregiert noch nicht über Member.
- `cli/src/speccify_cli/commands/{add,lock,pull,verify}.py` — Single-Member-Aware (lesen `WorkspaceContext`), aber **noch nicht** Multi-Member-aggregierend.
- `example-workspace/speccify.yaml` (Root mit `workspaces: [packages/*]`) + `example-workspace/packages/{forms,ui}/speccify.yaml` (Members mit eigenem `targets:` + `dependencies:`). Beide Members deklarieren `@org/button` — der natürliche Aggregations-Testfall.

### Was noch fehlt (= Phase-4-Scope)

1. **Root-Lockfile-Aggregation**: `speccify lock` im Root soll **ein** `speccify.lock` mit globaler MVS über alle Member-Deps generieren (Cargo-Style). Aktuell schreibt jedes Member sein eigenes Lockfile.
2. **Pull pro Member**: `speccify pull` im Root materialisiert pro Member in dessen `<member>/.speccify/` (oder Äquivalent), liest aber den Root-Lockfile.
3. **`add` ⇒ Member-Targeting**: `speccify add <spec> --member <name>` (oder via CWD-Detection) schreibt in den richtigen Member-`speccify.yaml`, dann Root-Re-Lock.
4. **Cross-Member `verify`**: prüft, dass jeder Member den Root-Lockfile respektiert + dass `aggregated_dependencies()` konfliktfrei auflöst.
5. **Conflict-Resolution-UX**: heute wirft `aggregated_dependencies()` bei leerer Range-Intersection nur eine Exception. Phase 4 soll diagnostische Fehlermeldungen liefern (welche Member, welche Ranges).
6. **Tests + Doku**: Multi-Member-Integration-Tests, Workspace-Quickstart-Doku in `docs/`, `example-workspace/` als getestetes Beispiel.

# Stage 0 — Decisions (2026-05-27, vom User bestätigt)

1. **Lockfile-Topologie**: Root-only `speccify.lock` (Cargo-Style). Members haben kein eigenes Lockfile.
2. **Output-Verzeichnis pro Member**: `<member>/speccify_generated/` — sichtbar, explizit committable.
3. **`add`-Default ohne `--member`**: CWD-Detection; im Root ohne Flag → Fehler mit klarem Hinweis auf `--member`.
4. **MVS-Konflikt-Strategie**: Strikt fehlschlagen (Cargo-Style); `WorkspaceError` mit diagnostischer Message (Member + Ranges).
5. **Cross-Member-Aliases**: Nein — Members sind entkoppelt, Aggregation nur über Resolver/Registry (keine Path-Deps).
6. **`verify` Tiefe**: Hash-only — Member-Deps ⊆ Root-Lockfile + Hash-Vergleich materialisierter Outputs. Kein Rebuild-Smoke.
7. **MCP-Tool-Surface**: Tools akzeptieren `workspace_root` + `member` als **optionale** Args; Default-Verhalten bleibt member-lokal.
8. **Web-Backend-Sicht**: Out-of-Scope Phase 4 — Web bleibt Workspace-blind.
9. **Schema-Bump**: Kein Bump nötig — Manifest v2 mit `workspaces: list[str]` reicht.
10. **Workspace-Detection**: Existenz des `workspaces:`-Keys im Root-Manifest aktiviert den Workspace-Pfad; sonst Single-Project.

# Stages-Skelett

Konkrete Stages folgen nach Stage-0-Antworten. Grobes Skelett (zur Orientierung — nicht final):

- **Stage 0**: Open Questions klären → Decisions im Plan-Dokument verankern.
- **Stage 1**: Root-Lockfile-Aggregation in `core/`: `Workspace.lock(targets, registry)` → ein Lockfile über alle Members; Tests gegen `example-workspace/`.
- **Stage 2**: CLI `speccify lock` Workspace-aware: Detection `workspaces:`-Key, ruft `Workspace.lock`; Single-Project-Pfad bleibt unverändert.
- **Stage 3**: CLI `speccify pull` Workspace-aware: materialisiert pro Member in dessen Output-Verzeichnis (laut Stage-0-Entscheid).
- **Stage 4**: CLI `speccify add <spec> [--member <name>]` mit CWD-Detection + Root-Re-Lock.
- **Stage 5**: CLI `speccify verify` cross-member: Hash-Vergleich pro Member gegen Root-Lockfile + diagnostische Conflict-Reports.
- **Stage 6**: Conflict-Resolution-UX (`WorkspaceError`-Renderer in CLI: welche Member, welche Ranges, Vorschläge).
- **Stage 7**: Doku — `docs/workspaces.md` + Workspace-Quickstart im README; `example-workspace/` als getestetes Fixture.
- **Stage 8**: Plan-Archivierung + AGENTS-/Status-Update; Tag-Vorschlag `v0.7.0-phase-4`.

# Delivery Steps

###   Step 1: Stage 0 — Open Questions & Decisions
Phase-4-Plan-Dokument `.agent/plans/phase-4-workspaces.md` mit `isActive: true` anlegen und die 10 Open Questions (siehe Plan-Tab) mit dem User klären; Decisions im Plan verankern, danach Stages 1–8 final ausschreiben.

- Plan-Dokument anlegen analog `archive/phase-3-codegen-targets.md` (Stage-0-Block, Stages 1–8-Skelett, Tag-Vorschlag `v0.7.0-phase-4`).
- 10 Open Questions strukturiert an User stellen (Lockfile-Topologie, Output-Dir, `add`-Default, MVS-Konflikt-Strategie, Cross-Member-Aliases, `verify`-Tiefe, MCP-Surface, Web-Backend-Sicht, Schema-Bump, Migration).
- Antworten als Decisions ins Plan-Dokument einarbeiten.
- `AGENTS.md` „Aktuelle Phase" + `.agent/status.md` auf Phase 4 aktiv umstellen.

###   Step 2: Stage 1 — Workspace.lock() in core
`core/src/speccify_core/workspace.py` bekommt eine `Workspace.lock(targets, registry)`-Methode, die genau ein Root-Lockfile über alle Members mit globaler MVS erzeugt.

- Neue Methode `Workspace.lock(...)` → `Lockfile`, baut auf `aggregated_dependencies()` + Resolver auf.
- Pro Member werden die Lock-Entries mit `member`-Tag (oder via `consumers: list[str]`) annotiert, damit `pull` pro Member filtern kann.
- Tests `core/tests/test_workspace_lock.py`: Lockfile gegen `example-workspace/` (`forms` + `ui`, gemeinsamer `@org/button`-Dep) — ein Entry pro Spec, beide Members als Consumers.
- Konflikt-Pfad: zwei Members mit unauflösbaren Ranges → `WorkspaceError` mit diagnostischer Message (Member-Name + Range-Liste).

###   Step 3: Stage 2 — CLI `speccify lock` Workspace-aware
`cli/src/speccify_cli/commands/lock.py` erkennt Workspace-Roots und delegiert an `Workspace.lock`; Single-Project-Pfad bleibt byte-identisch.

- Detection: `workspaces:`-Key im Manifest ⇒ Workspace-Pfad; sonst bestehender Single-Project-Pfad.
- Root-`speccify.lock` schreiben; Members bekommen **kein** eigenes Lockfile (laut Stage-0-Decision Root-only).
- Tests in `cli/tests/test_workspace_lock_cli.py`: `speccify lock` gegen `example-workspace/` schreibt ein Root-Lockfile mit beiden Members; Single-Project-Tests bleiben grün.

###   Step 4: Stage 3 — CLI `speccify pull` Workspace-aware
`cli/src/speccify_cli/commands/pull.py` materialisiert pro Member in dessen Output-Verzeichnis und liest den Root-Lockfile als Source of Truth.

- Iteration über `Workspace.members`; pro Member werden nur die Lock-Entries gerendert, die in dessen `dependencies:` referenziert sind.
- Output-Layout laut Stage-0-Decision (z. B. `<member>/.speccify/<target>/`).
- Tests: `pull` im Workspace-Root erzeugt Outputs in beiden Members, byte-identisch zu erwartetem Snapshot.

###   Step 5: Stage 4 — CLI `speccify add --member` + CWD-Detection
`speccify add <spec> [--member <name>]` schreibt in den richtigen Member-`speccify.yaml` und triggert anschließend `Workspace.lock` für ein konsistentes Root-Lockfile.

- `--member <name>`-Flag in `add.py`; ohne Flag CWD-basierte Member-Detection (Stage-0-Default).
- Im Workspace-Modus nach Member-Update automatisch Re-Lock auf Root-Ebene.
- Tests: `add @org/button --member ui`, `add @org/contact-form` aus `packages/forms/`-CWD.

###   Step 6: Stage 5 — CLI `speccify verify` cross-member
`speccify verify` im Workspace-Root prüft cross-member, dass jeder Member-Manifest gegen den Root-Lockfile konsistent ist und dass `aggregated_dependencies()` konfliktfrei auflöst.

- Pro Member: Member-Deps ⊆ Root-Lockfile + Hashes der materialisierten Outputs (falls Stage-0-Decision das fordert).
- Reporting: Tabellarisch pro Member „OK" / „MISMATCH" mit Detail-Block.
- Tests: synthetisch verfälschtes Lockfile-Entry → klar lesbarer Fehlerbericht.

###   Step 7: Stage 6 — Conflict-Resolution-UX
Bei `WorkspaceError` (leere Range-Intersection o. ä.) liefert die CLI eine diagnostische Fehlermeldung mit Member-Liste, Range-Liste und Lösungsvorschlag.

- `WorkspaceError`-Subclasses für die häufigen Fälle (Range-Conflict, Registry-Conflict pro Member, fehlender Member).
- Renderer in CLI (analog `ScopeRegistryConflictError`-Pattern aus Phase 2).
- Tests pro Fehlerklasse: Exception-Pfad rendert deterministisch + lesbar.

###   Step 8: Stage 7 — Doku + example-workspace als Fixture
`docs/workspaces.md` + Workspace-Quickstart im README; `example-workspace/` wird als getestetes Fixture in CI eingebunden.

- `docs/workspaces.md`: Konzept, Manifest-Beispiel, `lock`/`pull`/`add`/`verify`-Walkthrough, Konflikt-Beispiel.
- README-Abschnitt „Workspaces" mit Link auf `docs/workspaces.md`.
- CI-Test: `speccify lock && speccify pull && speccify verify` gegen `example-workspace/` als Smoke-Test.

###   Step 9: Stage 8 — Plan-Archivierung + Tag
Phase-4-Plan nach `.agent/plans/archive/`, `isActive: false`; AGENTS.md + `.agent/status.md` auf Phase 4 abgeschlossen; Tag-Vorschlag `v0.7.0-phase-4` an User.

- `.agent/plans/phase-4-workspaces.md` → `archive/`.
- AGENTS.md „Aktuelle Phase"-Block + `.agent/status.md` aktualisieren.
- Test-Counts + Verifikation (`ruff check`, `ruff format --check`, Root- + Registry-Pytest grün) im Plan-Dokument festhalten.
- Tag-Vorschlag `v0.7.0-phase-4` an User dokumentieren (setzt User selbst).