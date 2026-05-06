# Log: Speccify

## 2026-05-06 (später)
- **Phase 1a Step 1 abgeschlossen** — Manifest- und Pseudo-Registry-Layer:
  - Neues JSON-Schema `schema/manifest.schema.json` (Draft 2020-12) für
    `speccify.yaml`-Projektmanifest: `schema_version=1`, `target`,
    optional `registry.path`, `dependencies` als Map `@scope/name → range`
    (Phase 1a: nur exakte Versionen oder Caret `^X.Y` / `^X.Y.Z`).
  - `speccify_core.manifest.ProjectManifest` als immutable `@dataclass(frozen=True)`
    mit `load`/`write` (deterministischer YAML-Dump, sortierte Dependency-Keys),
    `resolved_registry_path()` (relativ zum Manifest), `ManifestError`-Hierarchie.
  - `speccify_core.registry`: `Version` (`major.minor.patch`, Pre-Releases in 1a
    bewusst ausgeklammert), `Spec` (mit Original-Bytes für stabile Hashes),
    `LocalRegistry` (Layout `<root>/<scope>/<name>/<version>/spec.speccify.yaml`,
    `list_versions` sortiert, `fetch` mit Available-Versions-Hint im Fehler),
    `RegistryError`.
  - Re-Exports in `core/src/speccify_core/__init__.py` ergänzt.
  - `registry-fixtures/` mit den 5 Phase-0-Specs als `0.1.0` plus
    `org/button/0.1.1/` für den späteren Diamond-Test angelegt; IDs/`uses`
    von `spec://...` auf `@org/...` umgeschrieben. Diamond-Setup so gewählt,
    dass reines Go-MVS deterministisch `button@0.1.1` liefert: `login-screen`
    fordert `@org/button@^0.1.1`, `onboarding-wizard` bleibt `@org/button@^0.1`
    (Mindestversionen `0.1.1` vs. `0.1.0`, Maximum = `0.1.1`).
  - `example-project/speccify.yaml` als Minimal-Manifest (Deps: `@org/button`,
    `@org/onboarding-wizard`).
  - Tests: `core/tests/test_manifest.py` (Round-Trip, Default-Registry-Pfad,
    fehlende/ungültige Felder, unbekannte Top-Level-Felder) und
    `core/tests/test_registry.py` (Version-Parsing/Order, sortierte Liste,
    Fetch-Bytes-Stabilität, Available-Versions-Hint, ID-Format-Check,
    Root-Validierung, alle 5 Specs vorhanden).
  - Verifikation lokal grün: `uv run pytest` (34 Tests, alt: 12, neu: 22),
    `uv run ruff check`/`format --check`, `uv run mypy core/src cli/src`,
    `uv run speccify lint registry-fixtures/.../spec.speccify.yaml` (alle 6
    Fixtures gegen `spec.schema.json` valide).
  - Plan-Status: Phase 1a Step 2 (MVS-Resolver) ist als Nächstes dran.

## 2026-05-06
- **Phase 1a-0 (Rebrand) abgeschlossen**: Repository komplett von `flowcation` auf
  `speccify` umgestellt. Python-Pakete (`flowcation_core/cli/mcp` →
  `speccify_core/cli/mcp`), Distribution-Namen, Workspace-Name, CLI-Binary
  (`flowcation` → `speccify`), Schema-`$id` (`https://speccify.io/schema/spec/v0.json`),
  Spec-ID-URI-Schema (`flow://` → `spec://`), Spec-Datei-Suffix
  (`*.flowcation.yaml` → `*.speccify.yaml`), Manifest-/Lockfile-Konvention
  (`speccify.yaml`/`speccify.lock`), Master-Plan in `speccify-plan.md` umbenannt.
- Doku konsistent: `README.md`, `AGENTS.md`, alle `*/README.md`, `.agent/*.md`,
  `phase-1a-resolver-lockfile.md` umgestellt. CI-Workflow ruft jetzt
  `speccify lint specs/*.speccify.yaml`.
- Verifikation grün: `uv lock` + `uv sync --reinstall` + `uv run pytest`
  (12 Tests) + `ruff check`/`format --check` + `mypy core/src cli/src` +
  `speccify lint specs/*.speccify.yaml` (5 Specs).
- Plan `phase-1a0-rename-to-speccify.md` nach `archive/` verschoben (Status →
  Done). Annotated Tag `v0.0.1-speccify-rebrand` als Marker vor Phase 1a.
- Domain-Status: Owner hat `speccify.io` + `speccify.de` bei df.eu registriert.
  `speccify.dev` ist bei df.eu nicht verfügbar/anbietbar — defensives Halten
  von `.dev` aufgeschoben (optional später via Cloudflare Registrar / Namecheap /
  Squarespace). Status-Update in `phase-1a0-rename-to-speccify.md` (Header +
  Domain-Liste) und `archive/naming-plan.md` (Header-Update-Zeile) ergänzt.
- Naming-Entscheidung final: **`speccify`** (Begründung im archivierten
  `archive/naming-plan.md`: Spec→Verb, Owner-Vorbenutzung, npm/GH-Org/`.io`/`.dev`
  frei).
- Neuer Plan `phase-1a0-rename-to-speccify.md` angelegt (Code-Rebrand:
  Python-Pakete `flowcation_*` → `speccify_*`, CLI-Binary `speccify` → `speccify`,
  Schema-`$id`, Manifest-/Lockfile-Name, Spec-ID-Schema `spec://` → `spec://`,
  Doku-Querverweise; Stages 1–6 mit Verifikation und Tag `v0.0.1-speccify-rebrand`).
- `naming-plan.md` nach `archive/` verschoben (Entscheidung getroffen,
  Recherche-Plan erfüllt). `status.md` umgebogen: Phase 1a-0 als nächster
  Schritt vor Phase 1a.
- Naming-Plan: Abschnitt „Weitere TLDs (`.ch`/`.at`/`.eu`)" ergänzt —
  Empfehlung: **nicht ins Initial-Setup**, da kein dedizierter Marketing-Hub
  und kein akutes Defensiv-Risiko. Tabelle mit Kosten/Nutzen + Nachzieh-Trigger
  (CH/AT-Kunden, EU-Förderprogramme, Squatting). Header-Update-Zeile ergänzt.
- Naming-Plan: Domain-Strategie-Abschnitt für `speccify` ergänzt
  (`.io` international + `.de` DE-Markt als Setup, `.com` aufschiebbar/optional).
  Enthält: Begründung mit Dev-Tool-Präzedenzfällen (`pnpm.io`, `n8n.io`,
  `fly.io`, `sentry.io`, ...), `.com`-Vorteile-Tabelle, Konkretplan
  (Sofort-Sicherung der freien Assets, `.com`-Anfrage mit Limit 500–3k USD),
  Heuristik-Tabelle und bewusste Auslassungen (`.ai`, `.app`).
- Naming-Plan: zwei Owner-Eigenvorschläge (`speccify`, `zouop`) ergänzt + bewertet.
  - `speccify`: npm/GH-Org frei, `.dev`/`.io` frei, `.com` registriert (geparkt seit
    2022, kein Server). Plus: Owner hat OSS-Vorbenutzung
    (`mhennemeyer/speccify`). Inhaltlich stärkster Kandidat (Spec→Verb).
  - `zouop`: `.com` bereits in Owner-Besitz, npm + `.dev`/`.io` frei,
    aber GitHub-User `zOuOp` blockiert Org-Anlage und Wort hat keinen
    semantischen Bezug zum Produkt. Eingeordnet als Backup.
  - Persönlicher Kurzfavorit neu sortiert: 1) `speccify`, 2) `forgepkg`,
    3) `mosaicspec`, 4) `anvilspec`, 5) `zouop`.
- Plan-Hygiene durchgeführt: bestehende Pläne in `.agent/plans/` auf Status geprüft.
- Phase 0 final geclosed:
  - ADR-Light-Tabelle für Q1–Q5 in `phase-0-wrap-up.md` ergänzt
    (Q1 strikte `kind`-Enum ab Phase 1, Q2 Asset-Ref-Whitelist
    `relativ + asset:// + figma:// + https://`, Q3 Resolver in Phase 1a,
    Q4 `$schema`-Pin auf Draft 2020-12 + Validator-Check in Phase 1,
    Q5 Conformance-Runner erst Phase 3).
  - Handover-Sektion auf `phase-1a-resolver-lockfile.md` und Master-Plan-Phase-1
    ergänzt.
  - Status `Done` (2026-05-06) im Plan-Header gesetzt.
- Pläne archiviert (`git mv` nach `.agent/plans/archive/`):
  - `phase-0-wrap-up.md` (Wrap-up abgeschlossen).
  - `phase-0-closeout.md` (überholt durch wrap-up; nicht ausgeführt).
  - `phase-0-wrap-up-decisions.md` (in wrap-up integriert).
- Querverweise umgebogen: `README.md` zeigt auf Archiv-Pfade + Phase-1a-Plan;
  `AGENTS.md` *Aktuelle Phase* auf Phase 1a umgestellt.
- `status.md` aktualisiert: Phase = *Phase 0 abgeschlossen — Phase 1a aktiv*,
  nächster Schritt = Phase-1a-Plan + Naming-Entscheidung.
- Annotated Tag `v0.0.0-phase0` auf den Wrap-up-Commit gesetzt.

## 2026-05-05
- Projekt initialisiert
- Phase-0-Abschluss-Tooling ergänzt:
  - `ruff`, `mypy`, `types-PyYAML` als Dev-Deps in Workspace-`pyproject.toml` gepinnt
    (passt zur Tooling-Aussage in `AGENTS.md`).
  - Repo mit `ruff format` formatiert (2 Dateien angepasst:
    `cli/tests/test_lint.py`, `core/src/speccify_core/validator.py`).
  - GitHub-Actions-Workflow `.github/workflows/ci.yml` um Format-Check + Mypy
    erweitert (vorher nur `ruff check` + Tests + lint).
- Verifiziert lokal: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy core/src cli/src`, `uv run pytest` (12 Tests),
  `uv run speccify lint specs/*.yaml` — alle grün.
- Phase 0 inhaltlich vollständig (Stages 1–8 abgedeckt); offen sind nur die
  im Phase-0-Plan genannten Open Questions sowie der Übergang zu Phase 1.
- Phase-0-Abschluss formalisiert:
  - `phase-0-spec-schema-spike.md` abgehakt (Status `Done`, alle Stages mit ✅
    und Artefakt-Verweis, Validation-Block markiert).
  - Neuer Plan `.agent/plans/phase-0-wrap-up.md` angelegt (Open Questions +
    Phase-1-Übergabe + ADR-artige Entscheidungstabelle).
  - Phase-0-Plan via `git mv` nach `.agent/plans/archive/` verschoben.
  - Querverweise in `AGENTS.md` und `README.md` auf den archivierten Pfad
    bzw. den neuen Wrap-up-Plan umgebogen.
  - `status.md` auf *Phase 0 abgeschlossen — Wrap-up läuft* gesetzt.
