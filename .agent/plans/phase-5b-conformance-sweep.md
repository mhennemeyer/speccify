# Phase 5b — Conformance Sweep, Replay-Cache-Recording & echte Spec×Target-Coverage

> Status: **Stages 1–3 Done** (Stage 2 durch User-Recording am 2026-05-29 abgeschlossen; Stage 3 am 2026-05-29 geliefert). Stages 4–6 offen.
> Vorgänger: Phase 5a abgeschlossen (Build-Smoke-Driver für React/Angular/SwiftUI, synthetische Snippets). Tag `v0.8.0-phase-5a` gesetzt.
> Disziplin: Erst nach Beantwortung der Open Questions wird ein Stage-1+-Implementierungsplan geschrieben (analog Phase 3/4/5a).
>
> **User-Antwort auf Stage 0 (2026-05-27)**: „folge deinen Empfehlungen" →
> alle OQs auf A. Scope = Substages 1 + 2 + 3 (Cache-Recording → echte
> Build-Smoke → 75-Pfad-Sweep), kein Visual-Regression, kein `ng build`.
> Web-Pfad bleibt im Sweep (OQ5=A); falls Angular/SwiftUI dort blockieren,
> fallback auf OQ5=B (xfail mit Phase-5c-Verweis).

---

## Kontext

Phase 5a hat den **Driver-Pfad** für alle drei Targets produktiv gemacht, aber:

- Angular- und SwiftUI-E2E-Tests laufen über **synthetische Mini-Snippets**, weil der Bedrock-Replay-Cache nur für React-Spec-Outputs existiert.
- Der **Cross-Consistency-Sweep** deckt aktuell nur `5 Specs × React × 5 Pfade = 25 Pfade` ab. Der volle 75-Pfad-Sweep `5 Specs × 3 Targets × 5 Pfade` aus dem Phase-3-Plan ist offen.
- Visual-Regression (Screenshot-Vergleich gegen `screenshots[]`) und echtes `ng build` (statt nur `tsc --noEmit`) sind Stretch-Kandidaten.

Phase 5b soll diese Lücken in **klar geschnittenen Substages** schließen, mit Phase-5a-Driver-Infrastruktur als Basis.

---

## Kandidaten (aus resume.md + Phase-5a-Stage-0-Decisions)

1. **Replay-Cache-Recording** — `BEDROCK_RECORD=1` für `5 Specs × {angular, swiftui}` triggern, Cache-Fixtures committen.
2. **75-Pfad-Cross-Consistency-Sweep** — `5 × 3 × 5` parametrisierte Pytest-Matrix.
3. **Echte Spec×Target-Build-Smoke-Erweiterung** — Angular/SwiftUI durch alle 5 Referenz-Specs statt synthetisch.
4. **Visual-Regression-Skeleton** *(Stretch)* — Screenshot-Vergleich gegen Spec-`screenshots[]`.
5. **Echtes `ng build`** *(Stretch)* — über `tsc --noEmit` hinaus für Angular.
6. **Web-Backend Workspace-aware** — eigentlich Phase-5c-Kandidat, hier nicht eingeplant.

---

## Open Questions an User (Stage 0)

### OQ1 — Scope-Schnitt: Welche Substages sollen Phase 5b umfassen?

- **A** *(empfohlen)*: Substages 1 + 2 + 3 (Cache-Recording → echte Build-Smoke → 75-Pfad-Sweep). Klar zusammenhängend, ohne Stretch.
- **B**: Nur 1 + 3 (Cache + echte Build-Smoke), 75-Pfad-Sweep in eigene Phase 5b-2.
- **C**: A + Visual-Regression-Skeleton (4) als zusätzliche Stage.
- **D**: A + echtes `ng build` (5).
- **E**: Alle 5 Substages — maximaler Sweep.

### OQ2 — Replay-Cache-Recording: Wer triggert die Aufnahme?

Der Bedrock-Replay-Cache braucht echte LLM-Calls für Angular/SwiftUI-Outputs aller 5 Specs.

- **A** *(empfohlen)*: **User** läuft lokal `BEDROCK_RECORD=1 .venv/bin/python -m pytest <recording-test>` mit AWS-Credentials und committet die generierten Fixtures. Ich liefere den Recording-Helper-Test + Doku.
- **B**: Ich generiere einen Recording-Script-Stub, der Bedrock mockt — kein echter LLM-Roundtrip, dafür reproduzierbar in CI. **Risiko**: Mock-Outputs sind nicht echtes LLM-Verhalten, Cross-Consistency-Test wird schwächer.
- **C**: Du gibst mir temporäre AWS-Credentials, ich record selbst. *(Nur falls explizit gewünscht — Default ist A.)*

### OQ3 — Cache-Speicherort & Naming

- **A** *(empfohlen)*: Bestehende Konvention `tests/fixtures/llm-cache/<spec-id>-<version>-<target>.json` weiterführen (analog React).
- **B**: Pro Target eigener Unterordner: `tests/fixtures/llm-cache/<target>/<spec-id>-<version>.json`.

### OQ4 — 75-Pfad-Sweep: Parametrisierungs-Granularität

Die 5 Pfade sind: Local-Registry, Remote-Registry, CLI (`speccify pull`), MCP, Web-Backend.

- **A** *(empfohlen)*: Volle `5×3×5`-Parametrisierung in einer Test-Datei mit `@pytest.mark.parametrize`. Failures pro Zelle identifizierbar, klassischer Sweep.
- **B**: Pro Target eine eigene Datei (3 Dateien à 25 Tests) — bessere Output-Lesbarkeit, mehr Boilerplate.
- **C**: Nur die "neuen" 50 Pfade (Angular/SwiftUI × 5 Pfade) hinzufügen; React-25 bleiben wie heute. **Risiko**: Test-Architektur driftet.

### OQ5 — Web-Pfad im Sweep: aktuell verfügbar?

Phase 1d hat das Web-Backend gebaut, Phase 4 hat es **explizit out-of-scope** gelassen für Workspaces. Ist der Web-Pfad heute target-agnostisch für Angular/SwiftUI nutzbar, oder muss ich ihn aus dem Sweep ausklammern?

- **A** *(empfohlen falls heute schon target-agnostisch)*: Im Sweep mitlaufen lassen.
- **B**: Web-Pfad nur für React im Sweep; Angular/SwiftUI als `xfail` markieren mit klarer Begründung, Fix in Phase 5c.
- **C**: Web-Pfad komplett aus dem 75-Pfad-Sweep ausklammern → `5×3×4 = 60 Pfade` für Phase 5b.

### OQ6 — Conformance-Marker für die neuen Tests

Die echten Build-Smoke-Tests (alle 5 Specs × {Angular, SwiftUI} via Driver) brauchen `npm install` / `xcrun` — analog Phase 5a teuer.

- **A** *(empfohlen)*: `@pytest.mark.conformance` → Default-Exclude, nur in dediziertem `conformance.yml`-Workflow.
- **B**: Eigener Marker `@pytest.mark.conformance_sweep` für weitere Differenzierung.

### OQ7 — CI-Strategie für die echten Build-Smokes

Der neue conformance-Workflow läuft heute nightly (`17 3 * * *`) + path-filter + manual.

- **A** *(empfohlen)*: Bestehende `conformance.yml`-Jobs erweitern (gleiche Trigger). 5× mehr Specs pro Job → Laufzeit-Anstieg ~5× (akzeptabel nightly).
- **B**: Neuer separater Workflow `conformance-sweep.yml` nur nightly, manueller `conformance.yml` bleibt schlank.

### OQ8 — Visual-Regression (Stretch): Tooling-Wahl

Nur relevant falls OQ1=C.

- **A** *(empfohlen)*: `pixelmatch` (Node) + headless Browser (Playwright) für React/Angular; SwiftUI ausklammern (kein Headless-Renderer ohne Xcode-UI-Test-Setup).
- **B**: Reines Bytestream-Diff (`Pillow` + `PIL.ImageChops`) als Skeleton, ohne echtes Rendering — nur Vergleichsinfrastruktur.

### OQ9 — Schema-Bump?

Falls für Visual-Regression neue Spec-Felder gebraucht werden (z. B. `screenshots[].tolerance`).

- **A** *(empfohlen)*: Kein Schema-Bump in Phase 5b — falls nötig, in separater Schema-Phase.
- **B**: Minor-Bump (`v0` → `v0.1`) mit Backcompat.

### OQ10 — Tag-Strategie nach Phase 5b

- **A** *(empfohlen)*: `v0.9.0-phase-5b`.
- **B**: Nach jeder Substage einen eigenen Sub-Tag (`v0.9.0-phase-5b-1` etc.) — feiner aber lauter.

---

## Vorgeschlagene Stage-Gliederung (vor User-Antwort, vorläufig)

Unter Annahme **OQ1=A** (Substages 1+2+3):

- **Stage 0** ✅ Done: dieses Dokument + User-Antwort „folge deinen Empfehlungen".
- **Stage 1** ✅ Done (2026-05-27): `scripts/record_llm_cache.py` ist
  target-aware (`--target react|angular|swiftui|all|<csv>`, Default `react` =
  Phase-1b-Backcompat); Unit-Tests `core/tests/test_record_llm_cache_script.py`
  (8 Tests, kein Netz); Walkthrough in `docs/conformance.md` (Abschnitt
  „Replay-Cache-Recording (Phase 5b Stage 1)") + README-Verweis bleibt
  unverändert (zeigt auf das Skript). User-Action: lokal
  `uv run python scripts/record_llm_cache.py --target angular,swiftui` mit
  AWS-Credentials, generierte JSONs unter `tests/fixtures/llm-cache/` committen.
- **Stage 2** ✅ Done (2026-05-29 durch User): Replay-Cache-Fixtures für
  `5 Specs × {angular, swiftui}` unter `tests/fixtures/llm-cache/` committed
  (12 neue Einträge: 6 angular + 6 swiftui inkl. button@0.1.1).
- **Stage 3** ✅ Done (2026-05-29): Synthetische Mini-Snippets in
  `core/tests/test_conformance_build_smoke.py` durch echte parametrisierte
  Tests über alle 5 Referenz-Specs ersetzt. `_render_spec(spec_id, version,
  target)`/`_lock_entry_for(...)` als target-agnostische Helfer; React-Test
  unverändert (`test_react_build_smoke_button_via_tsc`). Neue Tests:
  `test_angular_build_smoke_spec_via_tsc[*]` und
  `test_swiftui_build_smoke_spec_via_swiftc[*]` mit je 5
  Parametern (button/contact-form/http-api-client/login-screen/onboarding-wizard).
  **Verifikation: 11 Conformance-Tests passed in 8.66 s lokal**
  (1 React + 5 Angular + 5 SwiftUI); Default-Pytest weiter 332 grün.
- **Stage 4**: 75-Pfad-Cross-Consistency-Sweep parametrisiert.
- **Stage 5**: CI-Update (`conformance.yml` erweitern), Docs (`docs/conformance.md` + `docs/sweep.md` neu?).
- **Stage 6**: Plan-Archivierung, AGENTS.md / `resume.md` Update, Tag-Vorschlag.

---

## Verifikations-Erwartung (Phase 5b Definition of Done)

- Default-Pytest: weiterhin `-m "not conformance"`; Test-Count steigt um den Sweep (~50 neue Tests).
- Conformance-Pytest: 3 → `3 + 10 = 13` (5 Specs × 2 neue Targets via Driver) + bestehende 3.
- Cross-Consistency: 25 → 75 Pfade.
- `ruff check` + `ruff format --check` clean.
- `docs/conformance.md` + ggf. `docs/sweep.md` aktuell.
