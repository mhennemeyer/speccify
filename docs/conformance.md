# Conformance — Build-Smoke

> Phase-5a-Feature: Beweist, dass generierter Code nicht nur byte-identisch
> reproduzierbar ist (das prüft der `static-validate`-Backend aus Phase 3),
> sondern dass er auch durch die echte Toolchain des Ziel-Frameworks
> kompiliert.

## Konzept

Der `BuildSmokeBackend` (`core/src/speccify_core/conformance_build_smoke.py`)
implementiert das in Phase 3 etablierte
[`ConformanceBackend`](../core/src/speccify_core/conformance.py)-Protocol:

1. Pro Lockfile-Eintrag wird die Spec aus der Registry geladen,
2. mit dem passenden Codegen-Adapter (`react_llm`, `angular_llm`,
   `swiftui_llm`) re-gerendert,
3. die generierten Files werden in ein temporäres Arbeitsverzeichnis
   geschrieben,
4. die target-spezifische **Toolchain** (`tsc --noEmit` / `swiftc -typecheck` /
   …) wird darüber laufen gelassen,
5. ein `ConformanceResult` mit `status ∈ {ok, build_failed, render_failed,
   toolchain_missing}` zurückgegeben.

`toolchain_missing` ist explizit *kein* Failure — der Status existiert, damit
Tests/CI auf Plattformen ohne lokale Toolchain (z. B. minimaler Linux-Container
ohne `swiftc`) sauber skippen, statt fälschlich zu failen.

## Pluggable Driver pro Target

Jedes Target hat einen eigenen Driver, der das `ToolchainDriver`-Protocol
erfüllt:

```python
class ToolchainDriver(Protocol):
    target: str

    def is_available(self) -> bool:
        """True, wenn die Toolchain auf dem System verfügbar ist."""

    def build(self, *, files: dict[str, bytes], work_dir: Path) -> tuple[int, str]:
        """Schreibt `files` in `work_dir`, ruft den Build auf,
        liefert `(returncode, combined_stdout_stderr)`."""
```

`BuildSmokeBackend` führt eine Driver-Registry (`drivers: dict[str,
ToolchainDriver]`); fehlt ein Driver für ein bestimmtes Target, wird
`toolchain_missing` zurückgegeben.

## React (Phase 5a)

Der `ReactToolchainDriver` legt im Arbeitsverzeichnis ein minimales
TypeScript-Projekt an:

| Datei | Inhalt |
|---|---|
| `package.json` | `devDependencies: typescript@5.4.5, @types/react@18.2.79` |
| `tsconfig.json` | `strict=true`, `jsx=react-jsx`, `noEmit=true`, `moduleResolution=Bundler` |
| `<rel_path>` | Bytes aus `TargetRender.files` (z. B. `org/Button.tsx`) |

Dann wird:

```bash
npm install --no-audit --no-fund --silent --prefer-offline --no-package-lock
./node_modules/.bin/tsc --noEmit --project tsconfig.json
```

ausgeführt. Bewusste Designentscheidung: `npm install` statt
`npx --package=typescript`, weil letzteres die Pakete nur in den globalen
`npx`-Cache zieht — `tsc` findet `@types/react` dann nicht über die normale
Modulauflösung und schlägt mit `TS7026` fehl.

**Versionen sind hart gepinnt** in `conformance_build_smoke.py`
(`REACT_TYPESCRIPT_VERSION`, `REACT_TYPES_VERSION`). Updates erfolgen
explizit per Code-Change, nicht automatisch.

## Angular & SwiftUI (Phase 5b)

Out-of-Scope für Phase 5a, weil für die Referenz-Specs noch kein
Bedrock-Replay-Cache für `angular`/`swiftui` existiert (`@org/button` ist
nur als React-Output gecached). Phase 5b zieht zuerst den Cache nach und
implementiert dann die Driver analog zum React-Pattern.

Voraussichtliche Strategie:

- **Angular**: `npm install` mit `@angular/core` + `@angular/common` als
  Typings, `tsc --noEmit` über die generierten `.ts`-Files. Echtes `ng
  build` als Stretch (langsam, braucht eine `angular.json`).
- **SwiftUI**: `swiftc -typecheck <files>`, kein Package-Manifest nötig
  (Swift kompiliert direkt auf File-Ebene). macOS-only — Linux-Runner
  liefern `toolchain_missing`.

## Lokal ausführen

Conformance-Tests sind via Pytest-Marker `conformance` opt-in. Der
Default-Lauf schließt sie über `addopts = '-m "not conformance"'` aus,
damit die Unit-Suite unter 5 s bleibt und kein `npm install` triggert.

```bash
# Default — Unit-Suite, kein npm install
uv run pytest

# Opt-in — alle Conformance-Tests (lädt typescript@5.4.5 via npm)
uv run pytest -m conformance

# Nur die React-Build-Smoke
uv run pytest core/tests/test_conformance_build_smoke.py -m conformance
```

Voraussetzungen für den React-Conformance-Test:

- `node` + `npm` auf dem `PATH` (jede LTS-Version ab v18).
- Internet-Zugang oder bereits-gefüllter `~/.npm`-Cache für
  `typescript@5.4.5` + `@types/react@18.2.79`.

Fehlt etwas davon, **skipped** der Test sauber (kein Failure).

## CI (Phase 5b)

Phase 5a verzichtet bewusst auf einen CI-Job — sinnvoll wird das erst,
sobald Angular + SwiftUI im selben Workflow-Block stehen. Phase 5b sieht
vor:

- Matrix-Job `conformance` mit Pfad-Filter `paths: [codegen/**,
  core/src/speccify_core/conformance*.py]`.
- Ubuntu-Runner für React + Angular, macOS-Runner für SwiftUI.
- `schedule: [cron nightly]` + `workflow_dispatch` für Bedarfsläufe.

## Architektur-Verweise

- Protocol-Definition: [`conformance.py`](../core/src/speccify_core/conformance.py)
  (`ConformanceBackend`, `ConformanceReport`, `ConformanceResult`).
- Build-Smoke-Implementierung: [`conformance_build_smoke.py`](../core/src/speccify_core/conformance_build_smoke.py).
- Tests: [`test_conformance_build_smoke.py`](../core/tests/test_conformance_build_smoke.py).
- Phase-Plan: [`phase-5a-conformance-backends.md`](../.agent/plans/archive/phase-5a-conformance-backends.md).
