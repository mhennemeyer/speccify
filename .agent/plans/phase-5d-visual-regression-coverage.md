---
sessionId: session-260529-200900-phase5d
---

# Requirements

### Overview & Goals

Phase 5d baut auf dem **Visual-Regression-Skeleton** aus Phase 5c auf und liefert die **volle Visual-Regression-Coverage** über alle UI-Specs (4 von 5 Phase-0-Referenz-Specs; `http-api-client` ist headless und ausgeschlossen) × `{react, angular}` = **8 Pfade**. Phase 5c hat die Infrastruktur geliefert (`VisualRegressionBackend`, `PlaywrightPixelmatchDriver`, Pytest-Marker, CI-Workflow), aber nur einen einzelnen E2E-Test mit einer einzelnen Referenz-PNG (`button-primary.png`), die zudem noch nicht committed ist. Phase 5d schließt diese Lücke: committed Referenz-PNGs für alle 8 Pfade + parametrisierte Sweep-Tests + ein produktiv nutzbarer Workflow zum (Re-)Generieren der Snapshots.

Disziplin analog Phase 5b (Phase 5a → 5b war derselbe Schritt für Build-Smoke: Skeleton → Voller Sweep):

- **Kein** Schema-Bump in dieser Phase (`screenshots[].tolerance` bleibt vertagt — eigene Schema-Phase).
- **Kein** echter Component-Mount-Renderer in dieser Phase — die `<pre>`-Sandbox aus Phase 5c bleibt; ein „echter" Renderer ist eigener Folge-Phase-Kandidat (siehe Out-of-Scope).
- **Kein** SwiftUI-Visual-Regression in dieser Phase — bleibt eigene Phase (Xcode-UI-Tests).
- **Kein** `--update-snapshots`-Pytest-Flag in dieser Phase (Recorder-Script reicht, analog Phase-5c-OQ6-Vertagung).
- Snapshot-Recording-Disziplin: analog Phase-5b-Replay-Cache → die committed Referenz-PNGs sind „Maintainer-Hoheit"; ein klar dokumentierter Workflow via Recorder-Script erlaubt dem User, sie deterministisch nachzuziehen.

### Stage-0-Audit der Phase-0-Specs (Referenz-Screenshots)

| Spec                | `references` Screenshots         | UI?  | Im Sweep? |
|---------------------|----------------------------------|------|-----------|
| `button`            | `button-primary`, `button-loading` | ja | ja        |
| `contact-form`      | `empty`, `error`, `success`      | ja   | ja        |
| `login-screen`      | `happy-path`, `error-locked`, `otp-expired` | ja | ja  |
| `onboarding-wizard` | `step1`, `step2`, `step3`        | ja   | ja        |
| `http-api-client`   | — (keine, headless)              | nein | **nein**  |

Phase-5d-Sweep deckt **den ersten Screenshot** pro UI-Spec × 2 Targets = **8 Pfade** ab. Die zusätzlichen Screenshots pro Spec sind out-of-scope für 5d und werden in einer Folge-Phase adressiert.

### Scope

**In Scope**

- **Referenz-PNGs** für 4 UI-Specs × `{react, angular}` = **8 PNGs** in `specs/screenshots/<spec-name>-<target>.png` (flache Namens-Konvention, z. B. `button-primary-react.png`, `contact-form-empty-angular.png`).
- **Parametrisierter Sweep-Test** `core/tests/test_visual_regression_sweep.py` mit `@pytest.mark.visual_regression`, Matrix-Parametrisierung `4 UI-Specs × 2 Targets = 8 Tests`.
- **Snapshot-Recorder-Script** `scripts/record_visual_snapshots.py` (analog `scripts/record_llm_cache.py` aus Phase 5b): nimmt `--spec/--target/--all` entgegen, ruft den `PlaywrightPixelmatchDriver` direkt im Render-Modus auf (Single-Source-of-Truth — der Driver bekommt eine standalone `render()`-Methode oder ein bereits vorhandenes Helper-Pendant), schreibt die PNG nach `specs/screenshots/`. Idempotent, deterministische Viewport-Pins + mittlere Determinismus-Härte (siehe unten).
- **Determinismus-Härte (mittel)**: zusätzlich zum Viewport-Pin aus Phase 5c (320 × 240) jetzt: `prefers-reduced-motion: reduce`, `prefers-color-scheme: light`, fixe Font-Family-Stack (`monospace`-Fallback in der HTML-Sandbox).
- **Skip-Strategie** verfeinern: pro Pfad ein dedizierter Skip-Reason (Chromium fehlt / Referenz-PNG fehlt / Node-Toolchain fehlt) für CI-Sichtbarkeit; `http-api-client` taucht **nicht** in der Sweep-Matrix auf.
- **CI-Workflow** `.github/workflows/visual-regression.yml` erweitern: ein einziger Job, der den vollen Sweep über 8 Pfade in einem Process ausführt (npm install + Chromium-Install nur einmal); Path-Filter + Nightly-Cron aus Phase 5c bleiben unverändert.
- **Globaler Default-Tolerance 10 %** für alle 8 Pfade — keine per-Pfad-Overrides (KISS, kein Schema-Bump).
- **Docs**: `docs/visual-regression.md` erweitern um Sweep-Doku + Recording-Workflow + Troubleshooting (Font-/OS-Nondeterminismus); README-Update; `specs/screenshots/README.md` aktualisieren.
- **Tag-Vorschlag** `v0.11.0-phase-5d` an User nach Abschluss (Minor-Inkrement-Strategie analog 5a/5b/5c).

**Out of Scope**

- **Schema-Bump** `screenshots[].tolerance` (eigene Schema-Phase).
- **Echter Component-Mount-Renderer** statt `<pre>`-Sandbox (eigene Phase; nicht in 5d, da hoher Aufwand + eigene Open Questions wie Webpack/Vite-Pipeline, React-Renderer-Wahl, Angular-AOT).
- **SwiftUI-Visual-Regression** (eigene Phase; Xcode-UI-Tests, macOS-only).
- **`--update-snapshots`-Pytest-Flag** (Recorder-Script genügt; Flag in Folge-Phase mit höherem Sweep-Volumen).
- **Mehrere Screenshots pro Spec** (button hat 2, andere haben 3) — Phase 5d deckt nur den ersten; Folge-Phase erweitert.
- **`http-api-client` Visual-Regression** — semantisch nicht sinnvoll (headless API-Client).
- **Web-Backend Workspace-aware**, **echtes `ng build`** (eigene Kandidaten).

### User Stories

- **Maintainer:** Ich kann `python scripts/record_visual_snapshots.py --all` ausführen und bekomme deterministisch 8 PNGs in `specs/screenshots/`, die ich diffen + committen kann.
- **CI:** Bei jedem PR, der `core/`, `codegen/` oder `specs/` ändert, läuft der Visual-Regression-Sweep über 8 Pfade und meldet jede Pixel-Diff-Überschreitung > 10 %.
- **Spec-Autor:** Ich kann eine neue UI-Spec hinzufügen und mit einem Befehl die Referenz-PNGs für `{react, angular}` generieren, ohne den Driver-Code zu kennen.

### Acceptance Criteria

1. `specs/screenshots/` enthält **8 committed PNGs** nach flacher Namens-Konvention `<spec-name>-<target>.png`.
2. `uv run pytest -m visual_regression` liefert 8 grüne Tests lokal mit installiertem Chromium; skippt sauber ohne (pro Pfad expliziter Skip-Reason).
3. `python scripts/record_visual_snapshots.py --all` regeneriert alle 8 PNGs idempotent (zweimal hintereinander → byte-identisch).
4. Default-Pytest-Lauf (`uv run pytest`) bleibt unverändert grün; Sweep ist via `-m "not conformance and not visual_regression"` deselected.
5. CI-Workflow `visual-regression.yml` läuft den Sweep als **ein Job** grün auf Ubuntu (Path-Filter + Nightly-Cron unverändert aus Phase 5c).
6. `ruff check` + `ruff format --check` clean.
7. Plan archiviert nach `.agent/plans/archive/phase-5d-visual-regression-coverage.md`; AGENTS.md + `.agent/resume.md` aktualisiert; Tag-Vorschlag `v0.11.0-phase-5d` an User.

---

# Stage 0 — Open Questions ✅ ABGESCHLOSSEN (2026-05-29)

Alle 8 OQs entschieden (User-Antworten + Agent-Favoriten nach explizitem User-Mandat „entscheide selbst wenn klarer Favorit"). Audit ergab zusätzlich: `http-api-client` ist headless → 8 Pfade statt 10.

| OQ  | Thema                          | Entscheidung                                                                                       | Quelle    |
|-----|--------------------------------|----------------------------------------------------------------------------------------------------|-----------|
| OQ1 | Namens-Konvention              | (a) flach `<spec-name>-<target>.png` (z. B. `button-primary-react.png`)                            | Agent     |
| OQ2 | Screenshots pro Spec           | Erster Screenshot pro UI-Spec × 2 Targets = **8 Pfade**; `http-api-client` ausgeschlossen          | User      |
| OQ3 | Recorder-Strategie             | (a) `PlaywrightPixelmatchDriver` direkt aufrufen (Single-Source-of-Truth)                          | Agent     |
| OQ4 | Determinismus-Härte            | (b) Mittel: Viewport + `reduce-motion` + `color-scheme: light` + `monospace`-Font-Stack            | Agent     |
| OQ5 | CI-Job-Topologie               | (a) **Ein Job**, voller Sweep in einem Process (npm/Chromium-Install nur 1×)                       | Agent     |
| OQ6 | `--update-snapshots`-Flag      | (b) **Vertagen** — Recorder-Script reicht; Flag in Folge-Phase                                     | Agent     |
| OQ7 | Diff-Toleranz                  | (a) **Globaler Default 10 %** für alle 8 Pfade — keine Overrides                                   | Agent     |
| OQ8 | Tag-Vorschlag                  | (a) `v0.11.0-phase-5d` (Minor-Inkrement-Strategie)                                                 | Agent     |
| ZQ1 | `http-api-client` Behandlung   | **Aus Sweep ausschließen** (taucht nicht in Matrix auf — semantisch keine UI)                      | User      |

---

# Plan-Stages (finalisiert)

**Stage 1 — Driver-Render-API + Recorder-Script.**
- `PlaywrightPixelmatchDriver` bekommt eine standalone `render(html: str, viewport, ...) -> bytes` Methode (oder Refactor des bestehenden Diff-Pfads, sodass der Render-Schritt einzeln aufrufbar ist). Determinismus-Härte mittel (Viewport + `prefers-reduced-motion` + `prefers-color-scheme: light` + monospace-Font-Stack) wandert in einen geteilten Helper, der von Diff- und Render-Pfad gleichermaßen genutzt wird.
- `scripts/record_visual_snapshots.py`:
  - CLI: `--spec <name>`, `--target {react,angular}`, `--all`, `--out specs/screenshots/`.
  - Per Default UI-Specs aus Phase-0-Spec-Liste (hardcoded oder via Loader); `http-api-client` ist explizit ausgeschlossen.
  - Idempotent: zweimaliger Lauf → byte-identische PNGs.
- Verifikation: `python scripts/record_visual_snapshots.py --all` zweimal in Folge → `git diff` zeigt nichts.

**Stage 2 — Initiale 8 PNGs generieren & in `specs/screenshots/` committen.**
- Maintainer-Hoheit (User committed, analog Phase 5b Replay-Cache-Fixtures). Agent generiert lokal und übergibt; User reviewt + committed.
- `specs/screenshots/README.md` wird in Stage 6 aktualisiert.

**Stage 3 — Parametrisierter Sweep-Test `core/tests/test_visual_regression_sweep.py`.**
- `@pytest.mark.visual_regression`, `@pytest.mark.parametrize` über `(spec_name, target) ∈ {button, contact-form, login-screen, onboarding-wizard} × {react, angular}` = 8 Tests.
- Skip-Strategie pro Pfad: `pytest.skip("chromium not installed")` / `pytest.skip("reference PNG missing: <path>")` / `pytest.skip("node toolchain missing")` mit dedizierten Reasons.
- Default-Tolerance 10 % als Konstante im Test-Modul.

**Stage 4 — (entfällt; OQ6 vertagt).**

**Stage 5 — CI-Workflow `visual-regression.yml` an Sweep anpassen.**
- Ein Job (kein Matrix-Fan-out), der den vollen Sweep ausführt. Path-Filter + Nightly-Cron aus Phase 5c bleiben.
- Bei Failure: Artifact-Upload der actual-PNGs + Diff-PNGs (Standard-Playwright-Pattern), damit Maintainer ohne lokales Setup reviewen können.

**Stage 6 — Docs + Archivierung.**
- `docs/visual-regression.md` erweitern: Sweep-Doku, Recording-Workflow (`python scripts/record_visual_snapshots.py --all`), Troubleshooting-Sektion (Font-Rendering, OS-Drift, Tolerance-Tuning).
- README: Tabelle mit Coverage-Stand aktualisieren (5c: 1 Pfad → 5d: 8 Pfade).
- `specs/screenshots/README.md`: Workflow + Naming-Schema + Verweis aufs Recorder-Script.
- Plan archivieren nach `.agent/plans/archive/phase-5d-visual-regression-coverage.md`.
- AGENTS.md + `.agent/resume.md` aktualisieren (neuer „Phase 5d abgeschlossen"-Block).
- Tag-Vorschlag `v0.11.0-phase-5d` an User (selbst nicht setzen, vgl. `rules.md`).

---

# Verifikations-Checkliste (am Ende)

- `uv run pytest` Default-Lauf grün (Visual-Regression deselected).
- `uv run pytest -m visual_regression` 8/8 grün (mit Chromium) bzw. 8/8 skipped (ohne, mit dedizierten Skip-Reasons).
- `uv run pytest registry/` grün.
- `ruff check .` + `ruff format --check .` clean.
- `python scripts/record_visual_snapshots.py --all` idempotent (zweimal in Folge → byte-identisch).
- CI-Workflow `visual-regression.yml` grün auf Ubuntu (ein Job, voller Sweep).
