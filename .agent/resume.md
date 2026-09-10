# Resume — Speccify Phase 5c abgeschlossen (Visual-Regression-Skeleton)

> Historischer Stand, kein aktueller Session-Einstieg. Lies [agent.md](agent.md),
> die [Playbooks](playbooks/weiterentwicklung.md) und das aktuelle Spec-Board.
> Die folgenden Angaben dokumentieren ausschließlich den damaligen Stand.

> Einstiegspunkt für die nächste Session. Letzte Aktualisierung: 2026-05-29 (Phase-5c-Final).

## Status

- **Phase 5c Stages 0–4 Done** (2026-05-29) — Visual-Regression-Skeleton
  produktiv:
  - `VisualRegressionBackend` + `VisualDiffDriver`-Protocol +
    `VisualDiffResult`-Dataclass in
    `core/src/speccify_core/conformance_visual.py`.
  - `PlaywrightPixelmatchDriver` für React + Angular via headless Chromium +
    `pixelmatch`+`pngjs` (gepinnt: `playwright@1.44.0`, `pixelmatch@5.3.0`,
    `pngjs@7.0.0`).
  - Pytest-Marker `visual_regression` in `pyproject.toml` mit Default-Exclude
    (`addopts = -m "not conformance and not visual_regression"`).
  - 13 Unit-Tests via Fake-Driver + 1 E2E-Test `test_visual_regression_button_react`
    in `core/tests/test_conformance_visual.py`.
  - CI-Workflow `.github/workflows/visual-regression.yml` (Ubuntu, Node 20,
    Playwright-Browser-Cache, Path-Filter, Nightly-Cron `17 4 * * *`).
  - `docs/visual-regression.md` (146 LOC) + Cross-Link + Scope-Tabelle in
    `docs/conformance.md` + README-Update.
  - Plan archiviert nach
    `.agent/plans/archive/phase-5c-visual-regression-skeleton.md`.
- **Kein aktiver Plan** in `.agent/plans/` (außer Master-Plan).
  **Tag-Vorschlag an User: `v0.10.0-phase-5c`** (selbst nicht gesetzt, vgl. `rules.md`).
- **Phase 5b** abgeschlossen; Tag-Vorschlag `v0.9.0-phase-5b` (offen).
- **Phase 5a** abgeschlossen; Tag `v0.8.0-phase-5a` **gesetzt** (Commit 7845844).
- **Phase 4** abgeschlossen; Tag-Vorschlag `v0.7.0-phase-4` (offen).

## Verifikation Phase 5c

- **Root-Pytest (Default)**: **346 passed** (+14 ggü. Phase 5b = 332),
  12 deselected (davon 1 neuer `visual_regression`-E2E-Test korrekt
  deselected via Default-Marker-Exclude).
- **Registry-Pytest**: **134 passed** (unverändert ggü. Phase 5b).
- **Gesamt regulär: 480 Tests grün.**
- `ruff check` → All checks passed. `ruff format --check` → 147 files already formatted.

## Stage-0-Entscheidungen (User-Antworten)

| OQ  | Frage                      | Entscheidung                                     |
| --- | -------------------------- | ------------------------------------------------ |
| 1   | Tooling                    | Playwright + pixelmatch                          |
| 2   | Targets Skeleton           | React + Angular                                  |
| 3   | Anzahl Ref-PNGs            | 1 (button-primary)                               |
| 4   | Default-Tolerance          | 10 % (`DEFAULT_VISUAL_TOLERANCE = 0.1`)          |
| 5   | CI-Strategie               | Eigener Workflow `visual-regression.yml`         |
| 6   | `--update-snapshots`-Flag  | Vertagt auf Folge-Phase                          |
| 7   | Schema-Bump `tolerance`    | Vertagt — kein Schema-Bump im Skeleton           |
| 8   | Tag-Vorschlag              | `v0.10.0-phase-5c`                               |

Hinweis: OQ6/OQ7 wurden initial mit „Jetzt" beantwortet, im Follow-up
mit den Konsequenzen aber explizit vertagt (Skeleton-Disziplin).

## Was Phase 5c geliefert hat

- **Backend + Protocol**: `VisualRegressionBackend.compare(files, reference, work_dir)`
  liefert `VisualDiffResult` mit `passed`, `diff_ratio`, `pixel_diff_count`,
  `diff_image_path`, `reason`. `toolchain_missing`-Sentinel analog
  Phase 5a → `pytest.skip`.
- **Konkreter Driver**: `PlaywrightPixelmatchDriver` schreibt eine Mini-HTML-
  Sandbox (`<pre>`-Render der Files), startet headless Chromium via
  Playwright, diffed via Node-`pixelmatch`+`pngjs` und liefert JSON-Output
  `{ "diff": int, "total": int }`. Echter Component-Mount ist Folge-Phase.
- **Pytest-Marker**: `visual_regression` registriert + im Default-Run
  excluded (analog `conformance` aus Phase 5a).
- **E2E-Test**: rendert Mini-React-Snippet, vergleicht gegen
  `specs/screenshots/button-primary.png`. Skip-Pfade für fehlendes
  `node`/Chromium/Referenz-PNG sauber implementiert.
- **CI**: Separater Workflow `.github/workflows/visual-regression.yml`,
  Default-CI (`ci.yml`) unverändert. Cache für Playwright-Browser unter
  `~/.cache/ms-playwright`.
- **Docs**: `docs/visual-regression.md` + Cross-Link aus `docs/conformance.md`
  + Scope-Tabelle (5a/5b/5c) + README-Block.

## Nächster Schritt — Phase-5d-Plan-Entwurf nach User-Tag

Phase 5c ist Skeleton-Scope. Nach dem User-Tag `v0.10.0-phase-5c` ist der
nächste Schritt ein Phase-5d-Plan-Entwurf. Kandidaten (aus Phase-5c-
Out-of-Scope-Liste + Phase-5b-Folge-Backlog):

1. **Volle Visual-Regression-Coverage** — `5 Specs × {react, angular}` mit
   Referenz-PNG-Snapshots; voller Sweep parametrisiert.
2. **Echter Component-Mount-Renderer** — statt `<pre>`-Sandbox eine
   React/Angular-Runtime, die den generierten Code wirklich mountet.
3. **`--update-snapshots`-Pytest-Flag** — Komfort für Maintainer-Workflow.
4. **Schema-Bump `screenshots[].tolerance`** — Per-Screenshot-Tolerance
   (eigene Schema-Migration-Phase v2→v3).
5. **SwiftUI-Visual-Regression** — Xcode-UI-Test-Harness, macOS-CI.
6. **Echtes `ng build`** statt `tsc --noEmit` (aus Phase 5b verschoben).
7. **Web-Backend Workspace-aware** (aus Phase 4 verschoben).

Vor Implementierung: Stage 0 = Open Questions an User (analog
Phase 3/4/5a/5b/5c-Disziplin).

## Befehle (Spickzettel)

```bash
# Hidden-Flag entfernen (jedes Mal nach uv sync nötig) — läuft auch automatisch via conftest.py
./scripts/fix-venv-hidden.sh

# Default-Tests (ohne Conformance + Visual-Regression)
uv run pytest

# Conformance-Tests (Opt-in, lokal mit npm + xcrun verifiziert)
uv run pytest -m conformance core/tests/test_conformance_build_smoke.py -v

# Visual-Regression-Tests (Opt-in, lokal mit npm + Playwright-Chromium)
npx --yes playwright@1.44.0 install --with-deps chromium   # einmalig
uv run pytest -m visual_regression core/tests/test_conformance_visual.py -v

# Registry-Tests
uv run pytest registry/

# Lint + Format
uv run ruff check .
uv run ruff format --check .
```

## Pflichtlektüre vor Code

1. `AGENTS.md` (Aktuelle Phase + Konventionen).
2. `.agent/agent.md` + `.agent/rules.md` (Sprache: Deutsch, Du; FP-Stil; Tests pflicht; Tags nur User).
3. `docs/conformance.md` (Phase-5a/5b-Doku, Scope-Tabelle).
4. `docs/visual-regression.md` (Phase-5c-Doku, Backend-API + Workflow).
5. `docs/workspaces.md` (Phase-4-Doku).
6. `.agent/plans/archive/phase-5c-visual-regression-skeleton.md` (Phase-5c-Plan).
