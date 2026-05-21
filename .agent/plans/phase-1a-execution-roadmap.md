---
sessionId: session-260506-140134-11a1
isActive: true
---

# Orientierung

## Wo stehen wir?

- **Phase 0** abgeschlossen (Tag `v0.0.0-phase0`): Schema v0, `speccify lint`, 5 Referenz-Specs, CI grün.
- **Phase 1a-0** (Rebrand `flowcation` → `speccify` in Code/Repo) abgeschlossen (Tag `v0.0.1-speccify-rebrand`).
- **Phase 1a** (Resolver + Lockfile + Stub-Codegen) ist **geplant, aber noch nicht implementiert**. Der Plan dazu liegt in [`.agent/plans/phase-1a-resolver-lockfile.md`](../plans/phase-1a-resolver-lockfile.md) und definiert bereits 5 wohldefinierte Delivery-Steps.
- Im **Master-Plan** [`speccify-plan.md`](../plans/speccify-plan.md) sind noch **11 `flowcation`-Erwähnungen** stehen geblieben (Domain, E-Mail, Differenzierungs-Tabelle, Federation-Hinweis, Pfad-Links). Der Code/Repo ist umbenannt, der Master-Plan-Text noch nicht.

## Was diese Plan-Iteration liefert

Eine **konsolidierte Roadmap**, die

1. zuerst den Master-Plan aufräumt (kleines, isoliertes Wording-/Domain-Update — sofort sichtbar konsistent),
2. dann **Schritt für Schritt die 5 Delivery-Steps aus `phase-1a-resolver-lockfile.md` ausführt** (1:1 übernommen, hier nochmal als Stages der Übersicht halber wiederholt),
3. und am Ende den **Übergang zu Phase 1b** anstößt (neuer Phasen-Plan + `.agent/status.md`-Update + `AGENTS.md` Sektion „Aktuelle Phase").

Nach diesen Stages ist Phase 1a abgeschlossen, der Master-Plan begrifflich konsistent, und Phase 1b hat einen sauberen Startpunkt.

## Was bewusst NICHT in Scope ist

- **Inhaltliche Änderungen am Master-Plan jenseits des Rebrand-Wordings** in Stage 1. Inhaltliche Anpassungen (React-first, Template-Generator-Pin, Phase-1-Sub-Spike-Struktur) gehören laut Phase-1a-Plan in Stage 6 (= bestehender Step 5 aus dem Phase-1a-Plan).
- **Echtes React-Codegen, MCP-Server, Browser-Playground.** Bleiben Phase 1b/1c/1d.
- **Remote-Registry, sigstore, 2FA, Federation.** Bleiben Phase 2+.
- **LLM-basierter Codegen** (Lockfile-Variante mit `model`/`prompt_version`/`seed`). In 1a wird ausschließlich `kind: template` mit `template_set`/`template_version` als Generator-Pin verwendet.

# Master-Plan-Cleanup

## Ziel

Im Master-Plan [`.agent/plans/speccify-plan.md`](../plans/speccify-plan.md) alle 11 verbliebenen `flowcation`-Erwähnungen durch das aktuelle Branding ersetzen, ohne inhaltliche Plan-Aussagen zu verändern.

## Konkrete Treffer (zu Beginn von Stage 1 erneut verifizieren)

 Zeile | Aktueller Text (Auszug) | Ersetzung |
---|---|---|
 6 | `[flowcation/package-manager-comparison.md](archive/package-manager-comparison.md)` | `[Package-Manager-Vergleich](archive/package-manager-comparison.md)` |
 32 | „Eine Komponente in flowcation ist eine **abgeschlossene Spezifikation**" | „Eine Komponente in Speccify ist eine **abgeschlossene Spezifikation**" |
 131 | `authors: [marc@flowcation.com]` (im YAML-Beispiel) | `authors: [marc@speccify.io]` |
 180 | „Vollständige Begründung der Designentscheidungen: [flowcation/package-manager-comparison.md]…" | „Vollständige Begründung der Designentscheidungen: [Package-Manager-Vergleich]…" |
 190 | Tabellenzelle „Go + flowcation-eigen" | „Go + Speccify-eigen" |
 200 | Überschrift „### flowcation-spezifisch (kein anderer PM hat das)" | „### Speccify-spezifisch (kein anderer PM hat das)" |
 214 | `resolved_via: "registry.flowcation.com"` (Lockfile-Beispiel) | `resolved_via: "registry.speccify.io"` |
 338 | Tabellen-Header „flowcation" | „Speccify" |
 396 | „Federation: …, flowcation.com indexiert (à la PyPI + private Indexe)." | „Federation: …, speccify.io indexiert (à la PyPI + private Indexe)." |
 407 | „Domain `flowcation.com` gesichert (Markenrecherche steht aus)" | „Domain `speccify.io` gesichert (Markenrecherche steht aus)" |
 408 | „Package-Manager-Designentscheidungen geklärt → [flowcation/package-manager-comparison.md]…" | „Package-Manager-Designentscheidungen geklärt → [Package-Manager-Vergleich]…" |

## Regeln für die Ersetzung

1. **Produktname** (`flowcation` als Wort, ohne Punkt-Domain): wird zu `Speccify` (Großschreibung, wenn als Eigenname; klein in Code-Bezeichnern wie Verzeichnis-Slugs ist nicht im Master-Plan-Text).
2. **Domain `flowcation.com`**: wird zu `speccify.io` (Annahme aus Klärung; falls Domain-Frage später anders entschieden wird, ist das ein einzeiliger Fix).
3. **E-Mail `marc@flowcation.com`**: wird zu `marc@speccify.io`.
4. **Registry-Hostname `registry.flowcation.com`**: wird zu `registry.speccify.io`.
5. **Pfad-Verweise wie `flowcation/package-manager-comparison.md`**: Das Präfix `flowcation/` ist ein altes Repo-relativer Pfad und nicht mehr korrekt — die Datei liegt nur unter `archive/`. Ersetzung: nur den Linktext umbenennen, das Linkziel `archive/package-manager-comparison.md` bleibt.
6. **Tabellen-Header in der Differenzierungs-Tabelle (Zeile 338)** und **Lockfile-Tabellen-Zelle (Zeile 190)**: einfach durch `Speccify` ersetzen.
7. **Status-/Datums-Felder oben im Master-Plan (Zeilen 3–8)**: `Update 2026-05-04` und `Arbeitsname` bleiben unverändert (`Arbeitsname: speccify` ist bereits korrekt). **Kein** neues Update-Datum in dieser Stage hinzufügen — das ist Sache von Stage 6 (inhaltlicher Master-Plan-Sync).

## Was Stage 1 NICHT macht

- **Keine** inhaltlichen Master-Plan-Änderungen (z. B. Phase 1 sub-spikes, React-first, Template-Pin). Diese Änderungen sind für Stage 6 reserviert (= Step 5 aus `phase-1a-resolver-lockfile.md`).
- **Keine** Änderungen an `AGENTS.md`, `.agent/status.md`, `.agent/plans/phase-1a-resolver-lockfile.md` — die enthalten ohnehin nur noch zwei legitime, historisch korrekte `flowcation`-Erwähnungen (Repo-Name `Flowcation`-Pfad bzw. Phase-1a-0-Rebrand-Beschreibung).

# Phase-1a-Ausführung

## Quelle der Wahrheit

Die operative Stage-Reihenfolge stammt 1:1 aus den **Delivery-Steps in [`.agent/plans/phase-1a-resolver-lockfile.md`](../plans/phase-1a-resolver-lockfile.md)** (Zeilen 328–381). Diese Plan-Iteration **wiederholt sie als Stages 2–6**, damit Du Fortschritt direkt am Delivery Plan ablesen kannst, ohne zwischen Dokumenten zu springen.

 Stage | entspricht Phase-1a-Plan | Outcome |
---|---|---|
 2 | Step 1 | Manifest-Loader + Pseudo-Registry + Beispiel-Projekt + 5 gespiegelte Specs |
 3 | Step 2 | MVS-Resolver mit Diamond-Auflösung + Tests |
 4 | Step 3 | Lockfile-I/O + `speccify lock` + `speccify add` |
 5 | Step 4 | Stub-Codegen + `speccify pull --target react` |
 6 | Step 5 | `speccify verify` + `lint`-Patch + CI-Step + Master-Plan-Sync + Archivierung |

## Zentrale technische Eckpunkte (aus dem Phase-1a-Plan)

- **MVS strikt nach Go-Vorbild**, nur `^X.Y` / `^X.Y.Z` und exakte Versionen (kein `~`, keine Pre-Releases).
- **Spec-Hash-Quelle**: Bytes der Original-Datei (nicht re-serialisiert) → stabile Hashes.
- **Generator-Pin**: ausschließlich `kind: template` mit `TEMPLATE_SET = "phase-1a-stub"` und `TEMPLATE_VERSION = "0.1.0"`.
- **Output**: Markdown (`<scope>/<name>.md`), nicht `.tsx`. Stub-Codegen ≠ React-Codegen — bewusst.
- **Pseudo-Registry-Layout**: `registry-fixtures/<scope>/<name>/<version>/spec.speccify.yaml`. IDs/`uses` von `spec://...` auf `@org/...` umschreiben (Schema erlaubt beide Formen).
- **Diamond-Akzeptanzkriterium**: `onboarding-wizard` braucht `button@^0.1`, `login-screen` braucht `button@^0.1.0` → MVS wählt `0.1.1`. Pflicht-Test in `core/tests/test_resolver.py`.
- **Determinismus-Tests**: `pull` zweimal aufrufen → identische Bytes; `verify` exit 0; manueller Drift in einer Output-Datei → exit 1 mit Pfad-Liste.

## File-Layout-Ziel nach Stage 5

```
core/src/speccify_core/
  manifest.py | registry.py | resolver.py | lockfile.py    # Stages 2–4
  codegen/__init__.py | stub.py | templates/stub.md.j2     # Stage 5
cli/src/speccify_cli/
  __main__.py                                              # registriert add/lock/pull/verify
  commands/__init__.py | add.py | lock.py | pull.py | verify.py
schema/
  spec.schema.json                                         # unverändert
  manifest.schema.json | lockfile.schema.json              # neu
registry-fixtures/org/<name>/<version>/spec.speccify.yaml  # 5 Specs als 0.1.0 + button@0.1.1
example-project/speccify.yaml                              # E2E-Smoke-Manifest
```

## Tests pro Stage

- **Stage 2**: `core/tests/test_manifest.py`, `core/tests/test_registry.py`.
- **Stage 3**: `core/tests/test_resolver.py` (Happy-Path, Diamond, Konflikt, fehlende Spec/Version, Pre-Release-Ignore).
- **Stage 4**: `core/tests/test_lockfile.py`, `cli/tests/test_lock.py`, `cli/tests/test_add.py`.
- **Stage 5**: `core/tests/test_codegen_stub.py`, `cli/tests/test_pull.py`.
- **Stage 6**: `cli/tests/test_verify.py` (Happy-Path + Drift in Output + Drift in Spec-Bytes), CI-Workflow-Update.

# Übergang Phase 1b

## Was Stage 7 liefert

Kein Code mehr in dieser Plan-Iteration — nur **Plan-Hygiene**, damit Phase 1b sauber starten kann.

1. **Neuer Phasen-Plan-Stub** unter `.agent/plans/phase-1b-react-codegen.md` (Arbeitstitel) mit:
   - **Scope**: echtes React-Codegen-Target (statt Markdown-Stub), `speccify init`, Konformitätstests, ggf. erste `speccify publish`-Vorbereitung.
   - **Out of Scope**: MCP-Server (= 1c), Browser-Playground (= 1d), Registry-Backend (= 2).
   - **Offene Fragen** (Round-1-Klärung mit Dir, sobald Phase 1b operativ wird): React-Stack-Variante (Vite vs. Next.js?), TypeScript-Default?, CSS-Strategie?, golden renders?
   - Nur ein **Skelett** — die Detail-Stages folgen in einer eigenen Plan-Iteration, sobald Phase 1a abgeschlossen ist.
2. **`.agent/status.md`** umstellen: Phase auf *Phase 1a abgeschlossen, Phase 1b aktiv*; Tag-Hinweis auf optional `v0.1.0-phase-1a`; nächste Schritte zeigen auf den neuen 1b-Stub.
3. **`AGENTS.md` Sektion „Aktuelle Phase"**: auf Phase 1b verweisen, alten 1a-Link entfernen / auf Archiv-Pfad zeigen.
4. **Archivierung** des Phase-1a-Plans nach `.agent/plans/archive/phase-1a-resolver-lockfile.md` (Status-Header `Done`).

## Abgrenzung zu Stage 6

- **Stage 6** macht Phase-1a operativ und inhaltlich fertig (CI grün, `verify` läuft, Master-Plan inhaltlich gesynct).
- **Stage 7** rollt nur die *Plan-/Doku-Ebene* nach: Phasenplan-Datei, Status, AGENTS.md, Archiv. Beide Stages sind kurz; sie könnten theoretisch zusammengelegt werden, sind aber bewusst getrennt, weil Stage 7 keine Code-Änderungen mehr enthält und gut als „Übergangs-Commit" lesbar ist.

# Risiken

## Risiken & Gegenmaßnahmen

 Risiko | Wahrscheinlichkeit | Mitigation |
---|---|---|
 **Domain-Annahme `speccify.io`** stellt sich in Stage 1 als falsch heraus | mittel | In Stage 1 nur ein einziges Fundstellen-Set; falls Domain anders heißt, ist die Korrektur ein 5-Minuten-Folge-Patch. Alternativ Domain-Frage vor Stage 1 final klären. |
 **MVS-Kantenfälle** (Pre-Releases, voller `^0.x.y`-Operator) | mittel | Bewusst auf `^X.Y` / `^X.Y.Z` / exakt eingeschränkt. Pre-Releases werden ignoriert mit `logging.getLogger(__name__).warning`. Test in Stage 3. |
 **Hash-Stabilität** über YAML-Round-Trip | mittel | Spec-Bytes der Original-Datei hashen (nicht re-serialisiert). Lockfile selbst nutzt deterministischen YAML-Dump (sortierte Keys, fixe Quotes). Round-Trip-Test in Stage 4. |
 **`speccify lint` ↔ neues `speccify.yaml`-Manifest** | hoch (ohne Patch bricht `lint`) | In Stage 6 erweitert: `lint` validiert Manifeste gegen `manifest.schema.json` oder überspringt sie (Suffix `.speccify.yaml` + `kind`-Feld unterscheiden Spec von Manifest). |
 **Spec-ID-Form** in Pseudo-Registry vs. Original-Specs (`spec://` vs `@org/`) | niedrig | Beim Spiegeln nach `registry-fixtures/` werden `id`/`uses` umgeschrieben (Schema erlaubt beide Formen). Test sichert Round-Trip. |
 **Master-Plan-Abweichungen** (React-first statt SwiftUI, Templates statt LLM) | niedrig (dokumentiert) | Stage 6 synchronisiert Master-Plan inkl. Begründung; Stage 1 macht den Master-Plan vorher konsistent, sodass die inhaltliche Diff in Stage 6 sauber lesbar ist. |
 **Plan zu lang** — 7 Stages am Limit | niedrig | Stages 6 und 7 sind kurz und könnten bei Bedarf zusammengezogen werden. Aktuell getrennt für klare Lesbarkeit der Übergangslogik. |

# Delivery Steps

###   Step 1: Stage 1: Master-Plan Rebrand-Cleanup (`flowcation` → `Speccify`)
`.agent/plans/speccify-plan.md` enthält keine `flowcation`-Erwähnungen mehr; alle 11 Treffer sind durch das Speccify-Branding ersetzt, ohne inhaltliche Plan-Aussagen zu verändern.

- In `.agent/plans/speccify-plan.md` die 11 bekannten `flowcation`-Treffer ersetzen (siehe Tab „Master-Plan-Cleanup" für die exakte Liste mit Zeilennummern).
- Produktnamen `flowcation` → `Speccify` (Eigenname, Großschreibung).
- Domain `flowcation.com` → `speccify.io`; E-Mail `marc@flowcation.com` → `marc@speccify.io`; Registry-Hostname `registry.flowcation.com` → `registry.speccify.io`.
- Pfad-Linktexte wie `[flowcation/package-manager-comparison.md]` umbenennen zu `[Package-Manager-Vergleich]`; Linkziel `archive/package-manager-comparison.md` bleibt unverändert.
- Tabellen-Header in der Differenzierungs-Tabelle (Zeile 338) und Lockfile-Tabellen-Zelle (Zeile 190) auf `Speccify` setzen.
- Verifikations-Suche nach `flowcation` (case-insensitive) im Master-Plan muss am Ende **0 Treffer** liefern; in den anderen Plan-Dokumenten (`phase-1a-resolver-lockfile.md`, `AGENTS.md`, `.agent/status.md`) verbleibende Treffer sind erlaubt (historisch korrekt: Phase-1a-0-Rebrand-Beschreibung, Repo-Pfad).
- **Keine** inhaltlichen Master-Plan-Änderungen (React-first, Template-Pin, Phase-1-Sub-Spike-Struktur) — die kommen in Stage 6.
- Commit nach Conventional Commits: `chore(plan): finalize speccify rebrand in master plan`.

###   Step 2: Stage 2: Manifest-Loader und Pseudo-Registry-Layer (Phase-1a Step 1)
`speccify.yaml`-Projektmanifest und das lokale Pseudo-Registry können geladen, validiert und durchsucht werden.

- `schema/manifest.schema.json` neu anlegen (Draft 2020-12) mit Feldern `schema_version`, `target`, `dependencies` (Map `id` → version-range), optional `registry.path`.
- `core/src/speccify_core/manifest.py` mit `ProjectManifest` als immutable `@dataclass(frozen=True)`; `load(path)` validiert gegen Schema, `write(path)` schreibt mit deterministischer Key-Reihenfolge.
- `core/src/speccify_core/registry.py` mit `LocalRegistry`: `list_versions(spec_id)` (sortiert nach SemVer) und `fetch(spec_id, version) -> Spec` gegen Layout `registry-fixtures/<scope>/<name>/<version>/spec.speccify.yaml`.
- `registry-fixtures/` mit den fünf Phase-0-Specs als `0.1.0` befüllen (IDs/`uses` von `spec://...` auf `@org/...` umschreiben), zusätzlich `org/button/0.1.1/` für den Diamond-Test in Stage 3.
- `example-project/speccify.yaml` als Minimal-Manifest mit zwei Deps (`@org/button`, `@org/onboarding-wizard`) für End-to-End-Smoke.
- Re-Exports in `core/src/speccify_core/__init__.py` ergänzen.
- Tests:
  - `core/tests/test_manifest.py`: Round-Trip (load → write → bytes-identisch), Schema-Fehler bei fehlendem Pflichtfeld, falscher Typ.
  - `core/tests/test_registry.py`: Lookup-Happy-Path, fehlende Version → `RegistryError`, Sortierung der Versionsliste.
- Commit: `feat(core): add project manifest loader and local registry`.

###   Step 3: Stage 3: MVS-Resolver mit transitiver Auflösung und Diamond-Test (Phase-1a Step 2)
`Resolver.resolve(manifest) -> ResolvedGraph` liefert deterministisch das transitive Auflösungsergebnis inkl. korrekter Diamond-Auflösung.

- `core/src/speccify_core/resolver.py` mit `Version`, `Range` (in 1a nur `^X.Y` / `^X.Y.Z` und exakt; `~` und Pre-Releases ausgeklammert), `Resolution`, `ResolvedGraph`, `Resolver`, `ResolverError`-Hierarchie (`ConflictError`, `MissingSpecError`, `MissingVersionError`).
- MVS-Algorithmus strikt nach Go-Vorbild: pro Spec-ID Maximum aller geforderten Mindestversionen wählen, das alle Ranges erfüllt; bei Verletzung → `ConflictError` mit Quell-Trace.
- Deterministische Sortierung der `resolutions` (alphabetisch nach `id`, dann SemVer-Tie-Break).
- Spec-Bytes-Hashing: `sha256` der **Original-Datei** (nicht re-serialisiert) als `Resolution.spec_sha256`.
- Pre-Release-Versionen im Registry werden ignoriert mit `logging.getLogger(__name__).warning`.
- Konfliktmeldungen mit Source-Trace (z. B. `<root> → @org/onboarding-wizard → @org/button`).
- Tests in `core/tests/test_resolver.py`:
  - Happy-Path mit zwei direkten Deps.
  - Transitiver `uses:`-Pfad → drei Resolutions.
  - **Diamond**: `wizard` braucht `button@^0.1`, `screen` braucht `button@^0.1.0` → erwartet `0.1.1`.
  - Konflikt zwischen unvereinbaren Major-Ranges (`^0.1` vs `^0.2`).
  - Fehlende Spec im Registry, fehlende Version, Pre-Release-Ignore.
- Commit: `feat(core): add MVS resolver with diamond resolution`.

###   Step 4: Stage 4: Lockfile-Format, `speccify lock` und `speccify add` (Phase-1a Step 3)
Lockfile kann gelesen, geschrieben und über die CLI mutiert werden; `speccify add` und `speccify lock` funktionieren End-to-End gegen `example-project/`.

- `schema/lockfile.schema.json` mit `schema_version: 1`, `specs[]` inkl. `id`, `version`, `sha256`, `resolved_via`, `target`, `generator{kind: template, template_set, template_version}`, `generated_files_sha256[]`.
- `core/src/speccify_core/lockfile.py` mit `Lockfile.load`/`write` (deterministischer YAML-Dump, sortierte Keys, alphabetisch nach `id`); `LockEntry`, `GeneratorPin`, `GeneratedFile` als immutable Dataclasses.
- `cli/src/speccify_cli/commands/lock.py`: lädt Manifest, ruft Resolver, schreibt Lockfile **ohne** Codegen-Aufruf (`generated_files_sha256` bleibt leer).
- `cli/src/speccify_cli/commands/add.py`: erwartet `<spec-id>[@<range>]`, fügt Eintrag in `speccify.yaml` ein (Default-Range `^<major.minor>` aus latest-Version im Registry), ruft intern `lock`.
- Beide Commands in `cli/src/speccify_cli/__main__.py` registrieren; `lint` bleibt unangetastet.
- Tests:
  - `core/tests/test_lockfile.py`: Round-Trip (bytes-identisch), Schema-Fehler, sortierte Reihenfolge bei zwei Einträgen.
  - `cli/tests/test_lock.py`: Smoke gegen `example-project/` + `registry-fixtures/`, Lockfile-Inhalt verifizieren.
  - `cli/tests/test_add.py`: leeres Manifest + `add @org/button` → Manifest enthält `"@org/button": "^0.1"`, Lockfile hat einen Eintrag mit korrektem Hash.
- Commit: `feat(cli): add lockfile, lock command and add command`.

###   Step 5: Stage 5: Stub-Codegen und `speccify pull --target react` (Phase-1a Step 4)
`speccify pull` rendert resolved Specs deterministisch nach Markdown und füllt Output-Hashes im Lockfile.

- `core/src/speccify_core/codegen/__init__.py` und `stub.py` mit Konstanten `TEMPLATE_SET = "phase-1a-stub"` und `TEMPLATE_VERSION = "0.1.0"` sowie Funktion `render(spec, target) -> dict[str, bytes]`.
- Jinja2-Template `core/src/speccify_core/codegen/templates/stub.md.j2`: Frontmatter (`target`, `id`, `version`), `# <title>`, Summary, Inputs/Outputs/Events/Acceptance als Markdown-Tabellen.
- `cli/src/speccify_cli/commands/pull.py`: liest Lockfile, fordert resolved Specs aus `LocalRegistry`, ruft Stub-Codegen, schreibt Dateien atomar (`tempfile` + `os.replace`) nach `--out`, ergänzt `generated_files_sha256` im Lockfile.
- Output-Pfad-Konvention: `<out>/<scope>/<name>.md` (z. B. `out/org/button.md`).
- `pull` ohne vorheriges `lock` → klarer CLI-Fehler „run `speccify lock` first".
- `jinja2` als Runtime-Dependency in `core/pyproject.toml` aufnehmen; `uv lock` aktualisieren.
- Tests:
  - `core/tests/test_codegen_stub.py`: Determinismus über zwei `render`-Aufrufe (bytes-identisch), korrekte Output-Pfade, Title/Acceptance im Output enthalten.
  - `cli/tests/test_pull.py`: E2E gegen `example-project/` (Output-Datei existiert, Hash im Lockfile aktualisiert), Pflicht `lock` vorher → klarer Fehler.
- Commit: `feat(cli): add stub codegen and pull command`.

###   Step 6: Stage 6: `speccify verify`, `lint`-Anpassung, CI-Step und inhaltlicher Master-Plan-Sync (Phase-1a Step 5)
`speccify verify` schließt den Reproduzierbarkeits-Kreis; CI führt End-to-End-Smoke gegen `example-project/`; Master-Plan ist inhaltlich auf den Phase-1a-Stand synchronisiert.

- `cli/src/speccify_cli/commands/verify.py`: re-resolved Manifest, re-rendered in Temp-Verzeichnis, vergleicht **beide** Hash-Sätze (Spec-Bundle und Output-Dateien); exit 0 nur bei vollständiger Übereinstimmung; bei Drift exit 1 mit Liste betroffener Pfade.
- `cli/src/speccify_cli/__main__.py` `lint`-Logik anpassen: `speccify.yaml` (kein `kind`-Feld) wird übersprungen oder gegen `manifest.schema.json` validiert, statt fälschlich gegen Spec-Schema. Bestehende `lint`-Tests bleiben grün.
- `.github/workflows/ci.yml` um Schritt erweitern: `cd example-project && uv run speccify lock && uv run speccify pull --target react --out ./out && uv run speccify verify`.
- Tests `cli/tests/test_verify.py`:
  - Happy-Path: nach `pull` läuft `verify` mit exit 0.
  - Drift in einer Output-Datei → exit 1 mit Pfad-Hinweis.
  - Drift in einer Spec-Bytes (manuell veränderte Spec im Registry) → exit 1.
- **Inhaltlicher** Master-Plan-Sync in `.agent/plans/speccify-plan.md`:
  - Zeile 285: erstes Codegen-Target von SwiftUI auf React umstellen, mit Begründung (Phase-1d-Browser-Playground).
  - Zeilen 215–222: Lockfile-Beispiel um Variante `kind: template` (mit `template_set`/`template_version`) ergänzen; LLM-Variante (`model`/`prompt_version`/`seed`) bleibt als spätere Option dokumentiert.
  - Zeilen 282–288: Phase 1 in Sub-Spikes aufteilen (1a = dieser Plan, 1b = echtes React-Codegen + `init`, 1c = MCP-Server, 1d = Browser-Playground).
  - Zeile 297: Phase 3 entsprechend umsortieren (SwiftUI + Angular oder Jetpack Compose als zweites/drittes Target).
- Commit-Folge: `feat(cli): add verify command`, `chore(ci): add example-project end-to-end step`, `docs(plan): sync master plan with phase 1a outcomes`.

###   Step 7: Stage 7: Phase-1b-Kickoff (Phasen-Plan-Stub, Status-Update, Archivierung)
Phase 1a ist dokumentarisch abgeschlossen; Phase 1b hat einen klaren Startpunkt mit Stub-Plan und aktualisiertem Projektstatus.

- Neuen Phasen-Plan-Stub `.agent/plans/phase-1b-react-codegen.md` (Arbeitstitel) anlegen mit:
  - **Scope**-Skizze: echtes React-Codegen-Target (statt Markdown-Stub), `speccify init`, ggf. erste `speccify publish`-Vorbereitung.
  - **Out of Scope**: MCP-Server (= 1c), Browser-Playground (= 1d), Registry-Backend (= 2).
  - **Offene Fragen** als Round-1-Klärungspunkte für den Beginn von Phase 1b: React-Stack-Variante (Vite vs. Next.js), TypeScript-Default, CSS-Strategie, Golden-Renders pro Target.
  - Nur Skelett — Detail-Stages folgen in einer eigenen Plan-Iteration zu Beginn von Phase 1b.
- `.agent/status.md` umstellen:
  - Phase: *Phase 1a abgeschlossen — Phase 1b aktiv*.
  - Tag-Hinweis: optional `v0.1.0-phase-1a` als Marker setzen (nach Bestätigung manuell).
  - „Nächste Schritte" auf den 1b-Stub verweisen.
  - „Aktueller Stand" um die Phase-1a-Ergebnisse ergänzen (Resolver, Lockfile, `add`/`lock`/`pull`/`verify`).
- `AGENTS.md` Sektion „Aktuelle Phase" auf Phase 1b umstellen; alte Verweise auf den 1a-Plan auf den Archiv-Pfad zeigen lassen.
- Phase-1a-Plan archivieren: `.agent/plans/phase-1a-resolver-lockfile.md` → `.agent/plans/archive/phase-1a-resolver-lockfile.md`; Status-Header auf `Done` setzen.
- Commit: `docs(plan): archive phase 1a, kickoff phase 1b stub`.