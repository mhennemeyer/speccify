---
title: "Conformance — Build-Smoke (Phase 5a)"
description: "Die Conformance-Suite prüft, dass der von Speccify generierte Code gegen die echten Ziel-Toolchains **kompiliert**. Phase-5a-Scope ist *Build-Smoke* (kein Linking, kein Bundle); der Visual-Regression-Skeleton folgt in Phase 5c (siehe [`docs/visual-regression.md`](./visual-regression.md))."
---

{/* AUTOGENERIERT aus docs/ via scripts/sync_docs_to_site.py — nicht von Hand editieren. */}

Die Conformance-Suite prüft, dass der von Speccify generierte Code gegen die
echten Ziel-Toolchains **kompiliert**. Phase-5a-Scope ist *Build-Smoke* (kein
Linking, kein Bundle); der Visual-Regression-Skeleton folgt in Phase 5c
(siehe [`docs/visual-regression.md`](/conformance/visual-regression/)).

> **Konzept-Trennung**
>
> - **Unit-Codegen-Tests** (Default-Pytest): prüfen byte-identische Reproduzier-
>   barkeit der Renderer-Outputs gegen einen eingecheckten LLM-Replay-Cache.
> - **Build-Smoke** (Opt-in via `-m conformance`, Phase 5a): füttert die
>   gerenderten Outputs in `tsc --noEmit` bzw. `swiftc -typecheck` und prüft,
>   dass das Resultat *typcheckt*. Catches LLM-Drift, Codegen-Bugs und
>   Template-Regressionen.
> - **Visual-Regression** (Opt-in via `-m visual_regression`, Phase 5c
>   Skeleton): Pixel-Diff gegen committed Referenz-PNGs unter
>   `specs/screenshots/` via Playwright + pixelmatch. Siehe
>   [`docs/visual-regression.md`](/conformance/visual-regression/).

## Scope-Tabelle pro Phase

| Phase | Marker              | Scope                                  | Status |
| ----- | ------------------- | -------------------------------------- | ------ |
| 5a    | `conformance`       | Build-Smoke (tsc / swiftc)             | ✅     |
| 5b    | `conformance`       | 75-Pfad-Cross-Consistency-Sweep        | ✅     |
| 5c    | `visual_regression` | Visual-Regression-Skeleton (Playwright + pixelmatch, 1 Spec × React) | ✅ |

## Targets

| Target  | Driver                    | Toolchain                      | Plattform     |
|---------|---------------------------|--------------------------------|---------------|
| react   | `ReactToolchainDriver`    | `npm install` + lokales `tsc --noEmit` | Linux/macOS |
| angular | `AngularToolchainDriver`  | `npm install` + lokales `tsc --noEmit` mit `@angular/core`/`@angular/common` | Linux/macOS |
| swiftui | `SwiftUIToolchainDriver`  | `xcrun --sdk macosx swiftc -typecheck` | macOS only  |

Alle Toolchain-Versionen sind in `core/src/speccify_core/conformance_build_smoke.py`
explizit gepinnt (`REACT_TYPESCRIPT_VERSION`, `ANGULAR_CORE_VERSION`, etc.) —
deterministische Re-Runs sind das Ziel.

## Lokal ausführen

```bash
# Default-Pytest läuft Conformance NICHT (Marker via `addopts = -m "not conformance"`).
uv run pytest                                           # 325 grün, 3 deselected

# Opt-in für Build-Smoke (lokal, alle drei Targets):
uv run pytest -m conformance

# Nur ein Target:
uv run pytest -m conformance \
  core/tests/test_conformance_build_smoke.py::test_react_build_smoke_button_via_tsc
```

### Tool-Voraussetzungen (lokal)

- **React/Angular**: `npm` + `node` (z. B. via `brew install node` oder
  `nodenv install 20`). `npm install` legt die gepinnten devDeps in einem
  temporären `node_modules/` an — keine globalen Installs nötig.
- **SwiftUI**: `swiftc` + `xcrun` (mitgeliefert mit Xcode oder
  Command-Line-Tools). `xcrun --sdk macosx swiftc -typecheck` löst das
  SwiftUI-Framework automatisch über das macOS-SDK auf.

Fehlt eine Toolchain, **skippt** der zugehörige Test (kein Failure). Der
Backend-Status ist dann `toolchain_missing`.

## CI

Die Conformance-Jobs liegen in einem separaten Workflow
`.github/workflows/conformance.yml`, damit das Standard-CI nicht durch
Toolchain-Setup + Build-Smoke verlangsamt wird:

- **Trigger**: Path-Filter auf `core/src/speccify_core/conformance_build_smoke.py`,
  `core/src/speccify_core/codegen/**`, `core/tests/test_conformance_build_smoke.py`
  + Nightly-Cron (03:17 UTC) + `workflow_dispatch`.
- **Jobs**:
  - `conformance-react` (Ubuntu, Node 20)
  - `conformance-angular` (Ubuntu, Node 20)
  - `conformance-swiftui` (macOS, vorhandenes Xcode)

Default-CI (`ci.yml`) bleibt unverändert — Lint, Mypy, Pytest (ohne
Conformance), Web-Backend.

## Backend-API

Der Build-Smoke ist als `ConformanceBackend` implementiert und kann
programmatisch aufgerufen werden:

```python
from speccify_core import BuildSmokeBackend, Lockfile, LocalRegistry, ReplayCacheClient

backend = BuildSmokeBackend()  # nutzt React/Angular/SwiftUI-Default-Drivers
report = backend.run(
    lockfile=Lockfile(...),
    registry=LocalRegistry("registry-fixtures"),
    llm_client=ReplayCacheClient(cache=..., offline=True),
)
assert report.ok
```

Jedes `ConformanceResult` hat einen Status:

- `ok` — Build-Smoke war erfolgreich.
- `build_failed` — Toolchain hat das Re-Rendering nicht akzeptiert.
  `messages` enthält den getrimmten Stdout/Stderr.
- `render_failed` — Re-Render hat geworfen (Spec nicht ladbar, Cache miss, etc.).
- `toolchain_missing` — Driver nicht registriert oder Toolchain auf der
  aktuellen Plattform nicht verfügbar. Tests interpretieren das als „skip".

## Replay-Cache-Recording (Phase 5b Stage 1)

Die Phase-5a-Conformance-Tests für Angular/SwiftUI laufen über **synthetische
Mini-Snippets**, weil der eingecheckte Bedrock-Replay-Cache unter
`tests/fixtures/llm-cache/` nur React-Outputs enthält. Phase 5b Stage 1 macht
das Maintainer-Skript `scripts/record_llm_cache.py` **target-aware** —
Voraussetzung, um in Stage 2 echte Angular/SwiftUI-Fixtures aller
Phase-0-Specs zu committen.

```bash
# Voraussetzungen einmalig: Bedrock-Extra + AWS-Credentials (z. B. .env)
uv sync --extra bedrock

# Default-Verhalten ist unverändert (Phase 1b): nur React
uv run python scripts/record_llm_cache.py

# Phase 5b: alle Targets aufnehmen (5 Specs × 3 Targets = 15 Cache-Einträge,
# vorhandene werden idempotent geskippt):
uv run python scripts/record_llm_cache.py --target all

# Nur die fehlenden Phase-5b-Targets:
uv run python scripts/record_llm_cache.py --target angular,swiftui

# Cache-Eintrag erzwingen (z. B. nach Prompt-/Modell-Pin-Änderung):
uv run python scripts/record_llm_cache.py --target angular --force
```

Nach erfolgreichem Lauf landen neue JSON-Einträge unter
`tests/fixtures/llm-cache/<hash>.json` und müssen committed werden — der
Cache-Pfad ist target-unabhängig (Cache-Key bindet das Target implizit über
das Prompt mit ein).

> **Disziplin**: Recording-Läufe laufen **nicht** in CI — sie greifen aufs
> Netz zu und brauchen AWS-Credentials. Die Maintainer-Aktion ist Teil des
> Phase-5b-Stage-2-Übergangs.

## Echte Spec×Target-Build-Smokes (Phase 5b Stage 3)

Mit den in Stage 2 eingecheckten Angular/SwiftUI-Cache-Fixtures laufen die
Conformance-Tests jetzt über **alle fünf Phase-0-Referenz-Specs** statt über
synthetische Mini-Snippets. Pro Target eine `pytest.mark.parametrize`-Achse:

- `test_angular_build_smoke_spec_via_tsc[<spec>@<ver>]` — 5 Tests
- `test_swiftui_build_smoke_spec_via_swiftc[<spec>@<ver>]` — 5 Tests (macOS only)

`_render_spec(spec_id, version, target)` und `_lock_entry_for(...)` sind
target-agnostische Helfer in `core/tests/test_conformance_build_smoke.py`. Der
React-Test (`test_react_build_smoke_button_via_tsc`) bleibt unverändert; der
volle 75-Pfad-Cross-Consistency-Sweep ist Stage-4-Scope.

```bash
# Nur Angular (5 parametrisierte Zellen):
uv run pytest -m conformance \
  core/tests/test_conformance_build_smoke.py::test_angular_build_smoke_spec_via_tsc -v

# Eine einzelne Zelle:
uv run pytest -m conformance \
  "core/tests/test_conformance_build_smoke.py::test_swiftui_build_smoke_spec_via_swiftc[login-screen@0.1.0]"
```

## Cross-Consistency-Sweep (Local/CLI/MCP/Web)

Mit Stages 1–3 etabliert (Cache + echte Build-Smokes) liefert der Sweep den
vollen Cross-Consistency-Vergleich über alle Bezugsweg-Pfade:

| # | Pfad   | API                                                                           |
|---|--------|-------------------------------------------------------------------------------|
| 1 | Local  | `LocalRegistry.fetch` + `render_for_target` (Referenz)                        |
| 2 | CLI    | `speccify_cli.commands.lock.run_lock` + `speccify_cli.commands.pull.run_pull` |
| 3 | MCP    | `speccify_mcp.tools.pull.run_pull` (Function-Call-Level)                      |
| 4 | Web    | `speccify_web_backend.services.render.render_spec_from_yaml`                  |

Matrix: `5 Specs × 3 Targets = 15 Zellen`, pro Zelle alle 4 Pfade gegen den
Local-Pfad byte-verglichen → **60 byte-Vergleichsoperationen** pro Sweep-Lauf.

> Historie: Bis zum OSS-Pivot (P1, 2026-07-23) umfasste der Sweep 75 Pfade
> inkl. Remote-Registry-Roundtrip (Phase 5b Stage 4). Der Remote-Pfad ist mit
> dem Registry-Rückbau entfallen; der Git-basierte Nachfolger (`GitRegistry`,
> Phase P5) erweitert die Matrix wieder.

```bash
# Voller Sweep (läuft im Default-Pytest mit, keine Conformance-Marker):
uv run pytest apps/web/backend/tests/test_cross_consistency_sweep.py -v

# Einzelne Zelle:
uv run pytest \
  "apps/web/backend/tests/test_cross_consistency_sweep.py::test_cross_consistency_sweep_local_cli_mcp_web[button@0.1.0-react]"
```

Die Tests laufen im **Default-Pytest** (keine `@conformance`-Marker
nötig, da keine externe Toolchain involviert ist — alle Renderings nutzen den
Replay-Cache offline).

## Phase-5a-Scope vs. Phase 5b

| Bereich                                   | Phase 5a | Phase 5b |
|-------------------------------------------|----------|----------|
| `tsc --noEmit` React (Button-Spec)        | ✓        |          |
| `tsc --noEmit` Angular (synthetic snippet)| ✓        | ersetzt  |
| `swiftc -typecheck` SwiftUI (synthetic)   | ✓        | ersetzt  |
| Bedrock-Replay-Cache für SwiftUI/Angular  |          | ✓ (Stage 2) |
| Echte Spec×Target Build-Smokes (5 Specs × {Angular, SwiftUI}) |          | ✓ (Stage 3) |
| 75-Pfad-Cross-Consistency-Sweep           |          | ✓ (Stage 4) |
| Visual-Regression (Spec-Screenshots)      |          | out-of-scope |
| Echtes `ng build` (statt nur `tsc`)       |          | out-of-scope |

## Design-Entscheidungen (Stage 0)

1. **Toolchain-Pinning lokal, Docker-Matrix als Folge-Substage** —
   Versionen sind im Driver als Konstanten gepinnt, kein Container nötig.
2. **Speicherort `core/`** statt `codegen/<target>/conformance/` — die
   Codegen-Adapter liegen ohnehin in `core/src/speccify_core/codegen/`,
   Lokalitätsprinzip wird damit erfüllt.
3. **Marker-Default**: Conformance-Tests sind via `pyproject.toml` per
   `addopts = -m "not conformance"` aus dem Default-Lauf ausgeschlossen.
4. **`toolchain_missing` ≠ Failure**: Linux-CI ohne `swiftc` skippt,
   ohne den Default-Lauf zu brechen.
