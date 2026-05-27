# Conformance — Build-Smoke (Phase 5a)

Die Conformance-Suite prüft, dass der von Speccify generierte Code gegen die
echten Ziel-Toolchains **kompiliert**. Phase-5a-Scope ist *Build-Smoke* (kein
Linking, kein Bundle, keine Visual-Regression — letztere folgt in Phase 5b).

> **Konzept-Trennung**
>
> - **Unit-Codegen-Tests** (Default-Pytest): prüfen byte-identische Reproduzier-
>   barkeit der Renderer-Outputs gegen einen eingecheckten LLM-Replay-Cache.
> - **Build-Smoke** (Opt-in via `-m conformance`): füttert die gerenderten
>   Outputs in `tsc --noEmit` bzw. `swiftc -typecheck` und prüft, dass das
>   Resultat *typcheckt*. Catches LLM-Drift, Codegen-Bugs und Template-Regressionen.
> - **Visual-Regression** (Phase 5b): Screenshot-Vergleich gegen
>   Spec-`screenshots[]` — Out-of-Scope hier.

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
Conformance), Web-Backend, Registry-Backend.

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

## Phase-5a-Scope vs. Phase 5b

| Bereich                                   | Phase 5a | Phase 5b |
|-------------------------------------------|----------|----------|
| `tsc --noEmit` React (Button-Spec)        | ✓        |          |
| `tsc --noEmit` Angular (synthetic snippet)| ✓        |          |
| `swiftc -typecheck` SwiftUI (synthetic)   | ✓        |          |
| Cross-Spec × Target (5×3 = 15 Pfade)      |          | ✓        |
| Bedrock-Replay-Cache für SwiftUI/Angular  |          | ✓        |
| 75-Pfad-Cross-Consistency-Sweep           |          | ✓        |
| Visual-Regression (Spec-Screenshots)      |          | ✓        |
| Echtes `ng build` (statt nur `tsc`)       |          | ✓        |

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
