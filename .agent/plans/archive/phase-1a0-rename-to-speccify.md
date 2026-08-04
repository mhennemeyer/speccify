---
lifecycle: done
sessionId: session-260506-rename-speccify
---
# Phase 1a-0 — Rebrand „flowcation" → „speccify"

> **Status**: ✅ Done (2026-05-06)
> **Erstellt**: 2026-05-06
> **Update 2026-05-06**: Domains `speccify.io` und `speccify.de` durch Owner registriert (df.eu). `speccify.dev` ist beim aktuellen Anbieter (df.eu) **nicht verfügbar** — defensives Halten von `.dev` damit aufgeschoben (siehe Risiken-Sektion).
> **Vorgänger**: `archive/naming-plan.md` (Recherche & Entscheidung)
> **Nachfolger**: `phase-1a-resolver-lockfile.md` (echte Phase-1a-Implementierung)
> **Begründung der Phasen-Nummer „1a-0"**: Vor Phase 1a, weil CLI-Binary, Schema-`$id`, Manifest-Dateiname, Spec-ID-URI-Schema (`flow://` → `spec://`) und Python-Paketnamen umgestellt sein müssen, **bevor** Phase 1a Resolver/Lockfile/`add`/`pull` einführt — sonst doppelter Breaking-Change-Aufwand.

---

## Entscheidung

- **Neuer Name**: `speccify` (final, 2026-05-06).
- **Begründung**: Inhaltlich stärkster Kandidat (Spec→Verb, vgl. `Spotify`/`Shopify`), Owner-Vorbenutzung über `mhennemeyer/speccify`, npm/GH-Org/`.io`/`.dev` frei.
- **Domain-Strategie** (siehe `archive/naming-plan.md`):
  - `speccify.io` = kanonische Produkt-/Doku-URL (international). **✅ registriert (2026-05-06, df.eu)**.
  - `speccify.de` = DE-Marketing-Anker. **✅ registriert (2026-05-06, df.eu)**.
  - `speccify.dev` = defensiv geplant, aber **bei df.eu nicht verfügbar/anbietbar** — vorerst nicht registriert. Optional über Spezialanbieter (z. B. Google Domains-Nachfolger Squarespace, Namecheap, Cloudflare Registrar — `.dev` ist Google-betriebene gTLD und HTTPS-Pflicht via HSTS-Preload) nachziehen, falls aktiv benötigt.
  - `speccify.com` = aufschiebbar (geparkt seit 2022); ggf. später anfragen, Limit 500–3.000 USD.
  - `.ch`/`.at`/`.eu`/`.ai`/`.app` = nicht im Initial-Setup.

---

## Scope

### In Scope (diese Stage)

1. **Code-Rebrand im Repo** (Code + Doku, kein Hosting/keine Domains):
   - Python-Pakete `flowcation_core` → `speccify_core`, `flowcation_cli` → `speccify_cli`, `flowcation-mcp` → `speccify-mcp`.
   - Distribution-Namen `flowcation-core` → `speccify-core`, `flowcation-cli` → `speccify-cli`, `flowcation-mcp` → `speccify-mcp`.
   - Workspace-Name `flowcation-workspace` → `speccify-workspace`.
   - CLI-Binary `flowcation` → `speccify` (`[project.scripts]` in `cli/pyproject.toml`).
   - Manifest-Dateiname (Konvention, noch ungenutzt im Code) `flowcation.yaml` → `speccify.yaml`.
   - Lockfile-Dateiname (Konvention, kommt in Phase 1a) `flowcation.lock` → `speccify.lock`.
   - Spec-Datei-Suffix `*.flowcation.yaml` → `*.speccify.yaml` für die fünf Referenz-Specs unter `specs/`.
   - Schema-`$id` in `schema/spec.schema.json`: `https://flowcation.io/...` (oder vergleichbar) → `https://speccify.io/schema/spec/v0.json`.
   - Spec-ID-URI-Schema `flow://<name>@<semver>` → `spec://<name>@<semver>` (in Schema, Doku, Specs).
2. **Doku-Konsistenz**:
   - `README.md`, `AGENTS.md`, alle `*/README.md`, `.agent/agent.md`, `.agent/status.md`, `.agent/log.md`.
   - Aktive Pläne `phase-1a-resolver-lockfile.md` und `flowcation-plan.md` werden inhaltlich umgestellt; `flowcation-plan.md` wird zu `speccify-plan.md` umbenannt.
3. **Lokale Verifikation**: `uv sync` + `uv run pytest` + `uv run ruff check .` + `uv run ruff format --check .` + `uv run mypy core/src cli/src` + `uv run speccify lint specs/*.yaml` müssen grün sein.
4. **Conventional Commit + Tag**: `chore(rebrand): rename flowcation to speccify` + Tag `v0.0.1-speccify-rebrand`.

### Out of Scope (nachgelagert, separate Tasks)

- **Domain-Akquise** (`speccify.io`, `speccify.de`, `speccify.dev` registrieren, ggf. `.com` anfragen).
- **GitHub-Org `speccify`** anlegen + Repo-Migration (User-Aktion).
- **npm-Scope `@speccify`** reservieren (User-Aktion).
- **Social Handles** (X, BlueSky, Mastodon, LinkedIn).
- **Markenanmeldung DPMA/EUIPO `speccify`** (Wortmarke, ab 290 € DPMA / 850 € EUIPO/Klasse).
- **Repo-Verzeichnis-Rename auf Disk** (`/Users/.../Flowcation/` → `/Users/.../Speccify/`) — User entscheidet.
- **flowcation.com**: weiter halten als 301-Redirect auf `speccify.io`, oder verkaufen — Folgeentscheidung.

---

## Konkreter Umsetzungs-Ablauf

### Stage 1 — Pakete & Build-Metadaten

- [x] `pyproject.toml` (root): `name`, `description`, `[tool.uv.workspace.members]` (Pfade bleiben `core/cli/mcp`), `[tool.uv.sources]` (Schlüssel `flowcation-*` → `speccify-*`), Dev-Deps `flowcation-core/cli` → `speccify-core/cli`.
- [x] `core/pyproject.toml`: `name`, `description`, `[tool.hatch.build.targets.wheel].packages` (`src/flowcation_core` → `src/speccify_core`).
- [x] `cli/pyproject.toml`: `name`, `description`, `dependencies` (`flowcation-core` → `speccify-core`), `[project.scripts]` (`flowcation = ...` → `speccify = speccify_cli.__main__:main`), Hatch-Wheel-Pfad.
- [x] `mcp/pyproject.toml`: analog.

### Stage 2 — Python-Paket-Verzeichnisse

- [x] `core/src/flowcation_core/` → `core/src/speccify_core/` (`git mv`).
- [x] `cli/src/flowcation_cli/` → `cli/src/speccify_cli/` (`git mv`).
- [x] Importe + Symbole in den Quellen aktualisieren (`from flowcation_core ...` → `from speccify_core ...`).
- [x] Tests (`core/tests/`, `cli/tests/`): Importe + Fixtures.

### Stage 3 — Schema, Specs, Doku-Begriffe

- [x] `schema/spec.schema.json`: `$id` auf `https://speccify.io/schema/spec/v0.json` (oder vereinbarter Namespace), `title`, `description` neutralisieren oder umstellen.
- [x] `schema/README.md`: Begriffe.
- [x] `specs/*.flowcation.yaml` → `specs/*.speccify.yaml` (`git mv`); pro Spec interne `id`-Felder und Beispiele (falls `flow://` enthalten) auf `spec://` umstellen.
- [x] CLI-`lint`-Default-Glob (falls hardcoded auf `*.flowcation.yaml`) → `*.speccify.yaml`.

### Stage 4 — Doku & Pläne

- [x] `README.md` (root): Vision-Satz, Quickstart-Befehle (`flowcation` → `speccify`), Plan-Querverweise.
- [x] `AGENTS.md`: Vision, Repo-Layout-Tabelle (`flowcation-core/-cli/-mcp` → `speccify-core/-cli/-mcp`), Konventionen (Manifest, Lockfile, CLI-Binary, Spec-Identität), Phase-Verweis.
- [x] `core/README.md`, `cli/README.md`, `mcp/README.md`, `registry/README.md`, `schema/README.md`.
- [x] `.agent/agent.md` (Sprache/Onboarding bleibt; nur Begriff anpassen, falls auftaucht).
- [x] `.agent/status.md`: Begriffe + neue Phase „Phase 1a-0 abgeschlossen — Phase 1a aktiv" nach Abschluss.
- [x] `.agent/log.md`: Eintrag 2026-05-06 mit Rebrand.
- [x] `.agent/plans/flowcation-plan.md` → `.agent/plans/speccify-plan.md` (`git mv`); inhaltlich umstellen (Vision-Satz, IDs, CLI-Befehle).
- [x] `.agent/plans/phase-1a-resolver-lockfile.md`: alle Vorkommen `flowcation` (Manifest, Lockfile, Binary, Pakete, IDs `flow://`) auf `speccify` / `spec://` umstellen.

### Stage 5 — Verifikation

- [x] `uv sync` (kann Workspace-Re-Resolution erfordern, da Paketnamen sich ändern).
- [x] `uv run pytest` (12 Tests müssen grün bleiben).
- [x] `uv run ruff check .` + `uv run ruff format --check .`.
- [x] `uv run mypy core/src cli/src`.
- [x] `uv run speccify lint specs/*.speccify.yaml` (neuer Binary-Name, neuer Suffix).
- [x] CI-Workflow `.github/workflows/ci.yml`: Befehl `flowcation lint ...` auf `speccify lint specs/*.speccify.yaml` umstellen.

### Stage 6 — Commit + Tag

- [x] Conventional Commit: `chore(rebrand): rename flowcation to speccify`.
- [x] Annotated Tag: `v0.0.1-speccify-rebrand` (Markiert Punkt vor Beginn von Phase 1a unter neuem Namen).
- [x] `naming-plan.md` ist bereits archiviert; Querverweise im neuen Plan + status/log auf `archive/naming-plan.md` korrekt.

---

## Risiken / offene Punkte

- **uv-Workspace-Re-Sync**: Umbenannte Distribution-Namen können Lockfile (`uv.lock`) invalidieren. → `uv lock` neu erzeugen, Diff prüfen, mit committen.
- **Schema-`$id` ohne Live-URL**: `https://speccify.io/schema/spec/v0.json` zeigt momentan ins Leere — das ist ok für JSON-Schema (`$id` muss eindeutig sein, nicht zwingend abrufbar), die Doku sollte aber klarstellen, dass die URL aktuell nicht aufgelöst wird.
- **`flow://` in 5 Referenz-Specs**: Spezifikationen aus Phase 0 referenzieren sich evtl. gegenseitig oder verwenden `flow://`-IDs als Beispiel — beim Rebrand alle Vorkommen einfangen.
- **Externe Tester**: Falls Phase 0 von externen Personen ausprobiert wurde, sehen sie nach `git pull` einen Breaking Change. Tag `v0.0.0-phase0` bleibt als Wiederherstellungspunkt. Da Phase 0 aktuell nur intern, akzeptables Risiko.
- **Repo-Disk-Pfad** (`/Users/.../Flowcation/`): bleibt vorerst, da Rename des Working-Tree separat zu entscheiden ist.

---

## Done-Definition

- [x] Naming-Entscheidung dokumentiert (oben).
- [x] Alle Stages 1–6 abgehakt.
- [x] Tests grün.
- [x] Commit + Tag gesetzt.
- [x] Querverweise in `README.md`/`AGENTS.md`/`status.md` zeigen auf `phase-1a-resolver-lockfile.md` als nächstes aktives Plandokument unter neuen Namen.
- [x] Plan nach Abschluss → `.agent/plans/archive/`.
