# Speccify Workspaces

> Cargo-Style Multi-Package-Layout für Speccify — ein Root-Manifest, mehrere
> Members, **ein** gemeinsames Root-Lockfile mit globaler MVS.

Phase 4 macht Workspaces produktiv: `lock`, `pull`, `add` und `verify` sind
workspace-aware; pro Member werden Outputs nach `<member>/speccify_generated/`
materialisiert; das Lockfile lebt **einmal** im Workspace-Root.

## Konzept

- **Workspace-Root**: ein Verzeichnis mit `speccify.yaml`, das einen
  `workspaces:`-Key enthält (Liste von Globs, z. B. `packages/*`).
- **Members**: jedes Verzeichnis unter den Globs mit eigener `speccify.yaml`
  (eigene `targets:` + `dependencies:`).
- **Root-Lockfile**: `speccify.lock` im Workspace-Root, aggregiert über alle
  Members per globaler MVS (Minimum Version Selection).
- **Detection**: das Vorhandensein des `workspaces:`-Keys im Root-Manifest
  schaltet automatisch den Workspace-Pfad ein — ohne extra Flag.

## Beispiel-Layout

```
my-workspace/
├── speccify.yaml                   # Root: enthält workspaces: + ggf. registry:
├── speccify.lock                   # aggregiert, einziger Lockfile-Speicher
└── packages/
    ├── ui/
    │   ├── speccify.yaml           # Member: targets + dependencies
    │   └── speccify_generated/     # von `speccify pull` materialisiert
    │       └── react/
    │           └── org/Button.tsx
    └── forms/
        ├── speccify.yaml
        └── speccify_generated/
            └── react/
                ├── org/Button.tsx          # transitiv aus forms-deps
                └── org/ContactForm.tsx
```

Root-`speccify.yaml`:

```yaml
schema_version: 2
workspaces:
  - packages/*
registry:
  path: ../registry-fixtures
dependencies: {}        # Root selbst kann, muss aber keine Deps haben
```

Member-`packages/ui/speccify.yaml`:

```yaml
schema_version: 2
targets:
  - react
dependencies:
  "@org/button": "^0.1"
```

## CLI-Walkthrough

Alle Befehle laufen aus dem Workspace-Root (oder mit `--project <root>`).

### `speccify lock`

Aggregiert alle Member-Dependencies, löst globale MVS und schreibt **ein**
`speccify.lock` in den Workspace-Root.

```bash
cd my-workspace
speccify lock
```

Konflikt-Beispiel (zwei Members fordern unvereinbare Ranges):

```
✗ speccify lock fehlgeschlagen: Konnte keine Version für '@org/button' finden,
die alle Constraints erfüllt.
  packages/a/speccify.yaml fordert ^0.1 (min 0.1.0);
  packages/b/speccify.yaml fordert ^0.2 (min 0.2.0).
  Verfügbar: [0.1.0, 0.1.1].
```

→ User muss die Ranges in den Member-Manifesten harmonisieren
(`add`/manuelle Bearbeitung); Speccify führt **keine** automatische
Konflikt-Auflösung durch (Cargo-Style: strikt fehlschlagen).

### `speccify pull`

Iteriert über alle Members und materialisiert pro Member nur die Lock-Entries,
die in dessen `dependencies:` referenziert sind. Outputs landen unter
`<member>/speccify_generated/<target>/`.

```bash
speccify pull
```

> **Hinweis**: `--target` ist im Workspace-Modus nicht zulässig — jedes Member
> deklariert seine eigenen Targets selbst.

### `speccify add`

Schreibt in den richtigen Member-`speccify.yaml` und triggert anschließend
automatisch einen Root-Re-Lock.

Mit explizitem `--member`-Flag:

```bash
speccify add @org/contact-form --member forms
```

Ohne Flag wird das Member aus der **aktuellen Working-Directory** abgeleitet
(CWD-Detection):

```bash
cd packages/forms
speccify add @org/contact-form
```

Im Workspace-Root ohne `--member` **und** ohne passenden CWD-Kontext schlägt
`add` mit klarem Hinweis fehl:

```
✗ speccify add fehlgeschlagen: Im Workspace-Root ohne `--member` und ohne
CWD-Member-Kontext: `speccify add` braucht `--member <name>` (verfügbar:
forms, ui).
```

### `speccify verify`

Hash-only-Verify (Phase-4-Decision):

1. Prüft pro Member, dass alle Member-Deps im Root-Lockfile vertreten sind.
2. Vergleicht die `generated_files_sha256`-Hashes mit den Dateien auf Disk
   unter `<member>/speccify_generated/<target>/`.
3. Kein Re-Render, kein LLM-Pin-Check (das passiert im Single-Project-Modus
   und bleibt dort).

```bash
speccify verify
```

## MCP-Integration

Die MCP-Write-Tools (`lock`, `pull`, `verify`) bekommen in Phase 4 einen
optionalen `workspace_root`-Parameter. Wird er gesetzt, schaltet das Tool
intern auf den Workspace-Aggregat-Pfad um.

```jsonc
// MCP-Aufruf, Workspace-Mode
{
  "tool": "pull",
  "args": {
    "out_dir": "/ignored",         // im Workspace-Mode irrelevant
    "workspace_root": "/path/to/my-workspace"
  }
}
```

Antwort enthält `workspace: true` und die Union der `files_written` über alle
Members.

Im **Single-Project-Mode** (kein `workspace_root` gesetzt) ist das Verhalten
strikt rückwärtskompatibel — ältere MCP-Clients sind nicht betroffen.

## Design-Entscheidungen (Stage 0)

1. **Root-only Lockfile** (Cargo-Style). Members haben kein eigenes Lockfile.
2. **Sichtbares Output-Verzeichnis**: `<member>/speccify_generated/` (nicht
   `.speccify/`) — explizit committable, leicht inspizierbar.
3. **`add` ohne `--member`**: CWD-Detection; Fallback auf Fehler im Root.
4. **MVS-Konflikt-Strategie**: strikt fehlschlagen mit diagnostischer Message
   (Member-Pfad + Range + verfügbare Versionen).
5. **Cross-Member-Aliases**: nicht unterstützt — Members sind entkoppelt,
   Aggregation passiert ausschließlich auf der Resolver-Schicht.
6. **`verify` Tiefe**: Hash-only (Member-Deps ⊆ Root-Lockfile + Disk-Hash),
   kein Rebuild-Smoke. Volle Re-Render-Verification bleibt Single-Project.
7. **MCP-Surface**: optionaler `workspace_root`-Parameter; Default unverändert.
8. **Web-Backend**: Phase-4-out-of-Scope, bleibt workspace-blind.
9. **Schema**: kein neuer Bump — Manifest v2 reicht.
10. **Detection-Heuristik**: Existenz des `workspaces:`-Keys im Root-Manifest.

## Fixture & Tests

- `example-workspace/` ist das kanonische Beispiel-Layout (`packages/{ui,forms}`,
  beide mit `@org/button`-Dependency → MVS-Diamond-Testfall).
- CLI-Tests: `cli/tests/test_workspaces.py` (lock / pull / add / verify).
- Core-Tests: `core/tests/test_workspace.py` (`Workspace.lock`,
  Konflikt-Pfad, leere Targets).
- MCP-Tests: `mcp/tests/test_tools_write.py::test_mcp_workspace_*`.
