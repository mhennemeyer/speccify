# Projektstatus: Speccify

## Meta
- **Typ:** Code
- **Phase:** **Neuausrichtung auf Workflow-Playbooks abgeschlossen (2026-08-06)** — W1–W5 geliefert: Rückbau des Codegen-Zweigs, Playbook-Schema (Neustart bei `schema_version: 1`), Playbooks als Bundles, `speccify check` gegen Verrottung, read-only Viewer mit Workflow-Diagramm, Kontext-Brücke zum Agenten (`viewer_selection` / `playbook_propose`), Außendarstellung komplett auf Playbooks und Englisch. Offen nur noch BO-Aktionen (Repo öffentlich, Index säen, Doku-Site deployen, IAP-Playbook gegenlesen). Plan archiviert: [`plans/archive/neuausrichtung-workflow-playbooks.md`](./plans/archive/neuausrichtung-workflow-playbooks.md). Branch: `feat/oss-pivot`. Historie der Komponenten-Ära (P1–P6.1) in [`plans/archive/pivot-open-source-git-composer.md`](./plans/archive/pivot-open-source-git-composer.md).
- **Priorität:** Hoch (aktiver Umbau)
- **Zuletzt aktualisiert:** 2026-08-21

## Nächste Schritte
- **AKTIVER PLAN: [`plans/skills-und-tools.md`](./plans/skills-und-tools.md)**
  (Definition, 2026-08-20). Speccify wird **Skill- und Tool-Manager**: Skills
  definieren **Tool-Specs** (`tools/<name>/TOOL.md` — Inputs/Outputs als JSON
  Schema, Effekte, Anforderungen, **Beispiele als Vertrag**), die der Agent vor
  Ort ausprogrammiert statt fertige Skripte zu teilen (Python-Version,
  macOS/Linux/Windows waren die Hürde). Benutzung in drei ggf. iterativen
  Phasen **Expand → Execute → Evaluate**, getragen vom mitgelieferten
  Speccify-Skill; Speccify liefert `expand`, `tool check`, den
  Expansions-Nachweis. **`.agent/` ist das Zuhause** (BO 2026-08-21): `.agent/skills/` normale,
  expandierte Skills, `.agent/tools/` Implementierungen je Plattform, alles committet;
  `.claude/skills` verweist nur. Expand = Normalisierung (`uses` aufgelöst, Metadaten
  abgestreift, nur ergänzt). Kein Exec-MCP.
  Meilensteine T1 (Format) → T2 (Expand) → T3 (Evaluate) → **M2 Testlauf**.
  **T1 geliefert (2026-08-21)**: `tool.py`, Tool-Befunde in `check`/`lint`, drei Specs
  im Repo, `tool_get` im MCP (11 Tools), Viewer-Tools-Karte. **Nächstes Ziel: T2**
  (Symlink-Probe, Cache-`pull`, `expansions.yaml`, `speccify expand`, Umzug nach
  `.agent/skills/`).
- **M1 geliefert (2026-08-13)** nach [`plans/archive/skills-als-format.md`](./plans/archive/skills-als-format.md):
  `SKILL.md` ist das Format, zehn Skills in `skills/`, `pull` nach
  `.claude/skills/`, `check`/`lint`, MCP auf zehn Tools, Viewer/Backend auf
  Skills. Die Produktdefinition dort (ein Nutzer, drei Orte, W-A–W-H, D1–D6)
  gilt weiter. Außendarstellung (README, docs, Website) erzählt noch Playbooks.
- **Vorheriger Planstand (2026-08-11)**: [`plans/archive/skills-als-format.md`](./plans/archive/skills-als-format.md)
  (Produktdefinition, 2026-08-11). **Playbook heisst jetzt Skill** — der Begriff
  war artifiziell fuer etwas, das im Kern ein Agent Skill mit Metadaten ist. Das
  Besondere ist Organisation, Lookup, Kombination.
  **Nutzer: eine Person mit mehreren parallelen Projekten** (kein Team). Problem:
  Wissen und Setup wandern nicht zwischen den eigenen Projekten.
  **Rollen**: Skills verwaltet der Agent (MCP), Werkzeuge und Umgebung der Mensch
  (Desktop-UI). **Ablauf als Daten**, nicht im Programm — uebernehmen heisst Repo
  ziehen, anpassen heisst forken.
  Sechs Workflows durchgespielt (W-A bis W-F), Nicht-Ziele festgehalten, sechs
  Entscheidungsvorschlaege und drei offene Fragen. **Erst definieren, dann bauen**
  — auf BO-Wunsch nach drei Richtungswechseln in einer Woche.
  Zwei Funde: fremde Repos mit vielen Skills existieren schon
  (`anthropics/skills` = 17) ⇒ **Kaltstart-Problem entfaellt**; und Speccify
  liefert einen Skill mit, der Agenten beibringt Speccify zu benutzen ⇒ es wirkt,
  ohne dass man es jedem Projekt erklaert.
- **VERÖFFENTLICHT (2026-08-07)**: Repo ist öffentlich unter
  <https://github.com/mhennemeyer/speccify>, `main` ist Default. Der 2009er
  RSpec-Klon gleichen Namens bleibt unangetastet unter `master` — nichts
  verloren, alte Links funktionieren.
  **Website live**: <https://mhennemeyer.github.io/speccify/> (21 Seiten), per
  `pages.yml` bei jedem Push auf `main`. `public/CNAME` trägt speccify.io; die
  Domain wird aktiv, sobald der BO DNS setzt und die Custom-Domain in den
  Pages-Einstellungen einträgt (Werte in `docs/launch.md`).
  **Release-Pipeline gelaufen (BO-Auftrag)**: Tag `v0.2.0`, Build grün,
  Entwurfs-Release mit `.dmg` + `.app.tar.gz` (je 23 MB). Bundle geprüft —
  arm64, vier Sidecars, Engine mit 4 Wheels, Viewer-SPA, alle 10 Playbooks,
  Signatur `adhoc`. **Entwurf noch nicht veröffentlicht.** Erster Lauf war rot:
  Tauri prüft die **Existenz** von `APPLE_CERTIFICATE`, nicht den Inhalt — ein
  leeres Secret ließ `security import` scheitern. Anmeldedaten werden jetzt
  gestaged und nur bei Inhalt exportiert. Auslöser auf `v[0-9]+.[0-9]+.[0-9]+`
  verengt (`v*` hätte die zwölf Phasen-Tags getroffen).
  **Erster CI-Lauf überhaupt** (es gab nie ein Remote) hat sechs echte Fehler
  freigelegt, alle behoben: Playwright 1.44 kennt Ubuntu 24.04 nicht
  (`libasound2` → `libasound2t64`), Node 20 vs. Astros >= 22.12 (jetzt eine
  Quelle: `.nvmrc`), `ruff format` lief lokal nie mit, ein Typfehler in
  `search.py` — **weil mypy lokal kaputt war**: `.venv/bin/mypy` hatte einen
  Shebang auf die venv eines fremden Projekts, von iCloud hierher
  synchronisiert. lychee ohne `--root-dir` (450 Scheinfehler), danach ein
  echter: fehlendes `favicon.svg` auf allen Doku-Seiten. Dabei fiel die letzte
  alte Beschreibung auf („npm für Spezifikationen") — sie stand in
  `astro.config.mjs`, nicht in Markdown, deshalb hatte W5 sie übersehen.
  **Achtung iCloud**: Das Repo liegt unter `~/Desktop` und wird synchronisiert;
  70 Konfliktkopien (`datei 2.ext`) lagen im Arbeitsverzeichnis und haben die
  lokale Testzahl still verfälscht (253 statt 157). Per `.gitignore`
  ausgesperrt — das eigentliche Problem bleibt der Ablageort.
- **W1 GELIEFERT (2026-08-06)**: Schnitt und Fundament stehen — Rückbau des
  Codegen-Zweigs (Archiv-Branch `archive/pre-playbook-pivot`), neues
  Playbook-Schema (Neustart bei `schema_version: 1`), Playbooks als **Bundles**
  (Verzeichnis + `assets/`, Bundle-Hash im Lockfile), CLI (`init`/`search`/
  `add`/`lock`/`pull`/`verify`/`show`/`lint`), MCP (`playbook_list`/
  `playbook_get`/`playbook_step`/`search`/`lock`/`pull`/`verify`), Web-Routen,
  read-only **Viewer** statt Editor, zwei echte Referenz-Playbooks
  (macOS-Notarisierung + Developer-ID-Zertifikat als Child), `docs/playbooks.md`
  und `docs/viewer.md`. Alles produktseitig auf Englisch.
  **Verifikation: 115 Pytest, 1/1 Playwright, MCP-stdio-Smoke, Viewer-Build,
  Doku-Site (32 Seiten), ruff clean.**
- **W2 GELIEFERT (2026-08-06)**: `speccify check` — Struktur + Quellen-Alter
  offline, Link-Erreichbarkeit hinter `--links` (Marker `links`, opt-in weil
  Netz); MCP-Tools `playbook_asset` + `playbook_check` (9 Tools). Der
  Agent-Vertrag ist per Test gepinnt: list → get → Child-Playbook → Schritt →
  Asset, nur über Tools. **130 Pytest, `-m links` grün.**
- **W3 GELIEFERT (2026-08-06)**: Viewer-Ausbau — Workflow-Diagramm (SVG ohne
  Lib), Markdown im `detail` und inline in Prerequisites/Pitfalls/verify,
  Quellen-Alter mit derselben 180-Tage-Schwelle wie `speccify check`, ein
  Filterfeld für Bibliothek und Index-Suche zugleich, Index-Treffer direkt
  öffenbar. **130 Pytest, 1/1 Playwright (Smoke deckt Filter, Diagramm,
  Markdown, Alter und Index ab), Viewer-Build 323 kB.**
- **IAP-REFERENZ-PLAYBOOK GESCHRIEBEN (2026-08-06)**: `@speccify/iap-trial-then-unlock`
  (9 Schritte, 9 Quellen, 3 Assets) + Child `@speccify/storekit-sandbox-testing`,
  destilliert aus zwei eigene, nicht öffentliche Apps (beide nur gelesen). Kern: **Apple
  hat für Einmalkäufe keinen Testzeitraum** — Free Trials sind Introductory
  Offers und damit abo-only; die eigentliche Arbeit ist, wo der Trial-Start
  liegt (UserDefaults/Keychain/iCloud kombinieren, frühester Start gewinnt).
  **Wartet auf BO-Korrektur.**
- **W4 GELIEFERT (2026-08-06)**: Kontext-Brücke zum Agenten —
  `viewer_selection` liefert die Auswahl **aufgelöst** (Playbook, Schritt samt
  `detail`/`verify`/Quellen, Asset-Inhalt), `playbook_propose` nimmt einen
  kompletten neuen YAML-Text, das Backend validiert sofort, der Viewer zeigt
  einen Diff mit Apply/Discard. Nichts landet ohne Klick auf der Platte;
  Git-Quellen sind schreibgeschützt. **11 MCP-Tools. 144 Pytest, 1/1
  Playwright (Smoke geht klicken → Auswahl prüfen → Vorschlag → Diff →
  anwenden durch).**
- **W5 GELIEFERT (2026-08-06)**: Außendarstellung auf Playbooks und (D6) auf
  Englisch — README, Landing-Page, `docs/launch.md`, `docs/local-dev-e2e.md`,
  `docs/git-sources.md`, `index/README.md`, `mcp/README.md`, CONTRIBUTING,
  Getting-Started und MCP-Referenz. `/try-it/` gelöscht (bewarb einen
  Playground, den es seit W1 nicht mehr gibt).
  **Dabei gefunden: der Desktop-Build war kaputt** — `build_engine_payload.sh`
  kopierte `registry-fixtures/` und `tests/fixtures/llm-cache/`, beide beim
  Rückbau entfernt, und `lib.rs` setzte `SPECCIFY_REGISTRY_PATH`, das das
  Backend nicht mehr liest. Beides auf `playbooks/` gezogen. Dazu
  `apps/web/frontend` (Playground gegen entfernte Routen), `record-llm-cache.sh`,
  das `bedrock`-Extra und `Settings.cache_dir` entfernt; `gen_cli_docs.py`
  löscht jetzt verwaiste Befehlsseiten (`build`/`mock`/`conformance` waren noch
  auf der Doku-Site).
  **144 Pytest, 1/1 Playwright, 18/19 Desktop-Tests, ruff clean, Doku-Sync +
  CLI-Doku ohne Drift, Marketing-Build 21 Seiten, keine toten internen Links,
  `speccify check playbooks/` 0 Fehler.**
  **Als Nächstes**: kein offener Entwicklungsschritt — die Neuausrichtung ist
  komplett. Was bleibt, sind BO-Aktionen aus `docs/launch.md`.
- **NEUAUSRICHTUNG (BO, 2026-08-06)**: Der Komponenten-Ansatz ist vom
  Fortschritt bei Coding-Agents überholt. Neue Richtung: **eine Spec ist ein
  Playbook für einen komplexen, wiederkehrenden Workflow** (Schritte, Quellen,
  Assets, Fallstricke) — Wissen, das ein Agent sich sonst jedes Mal neu
  erarbeiten müsste. Der Composer wird **Viewer + kontextsensitiver Chat**
  (kein Edit-Modus). Git-Quellen, Discovery, MCP/Server und die Desktop-App
  bleiben und wachsen.
  **Plan abgeschlossen und archiviert: [`plans/archive/neuausrichtung-workflow-playbooks.md`](./plans/archive/neuausrichtung-workflow-playbooks.md)**
  — D1–D8 entschieden (Rückbau des Codegen-Zweigs, Chat über MCP statt eigenem
  LLM-Client, kein Edit-Modus, Schema-Neustart statt Migration, Playbooks als
  Bundles, alles produktseitig englisch, Vokabular „Playbook",
  Granularitäts-Prüfstein). W1–W5 alle geliefert.
- **Vorherige Roadmap abgeschlossen und archiviert**:
  [`plans/archive/pivot-open-source-git-composer.md`](./plans/archive/pivot-open-source-git-composer.md)
  (P1–P5 geliefert, P6.1 Doku-Site + Launch-Vorbereitung). Was daraus trägt —
  Git-Quellen, Discovery, MCP-Vertrag, Determinismus-Stack, Desktop-App —
  läuft im neuen Plan weiter; der Codegen-Zweig steht zum Rückbau an.
- **P6.1 Doku-Site (2026-08-05)**: Sync um API/Mocks, Composer, Projekt-Builds
  und Git-Quellen erweitert, Registry-Abschnitt (Pivot-Altlast) entfernt,
  Stub-Seiten gefüllt (Installation, Erste Spec, Spec-Format, MCP, Targets),
  Landing + README auf die Git-Geschichte gezogen; generierte Seiten tragen
  ihren Hinweis jetzt als HTML-Kommentar statt als sichtbaren Text.
  **Verifikation: 523 Pytest, Doku-Sync + CLI-Doku ohne Drift, Site baut 29
  Seiten (vorher 24), ruff clean.**
- **P5.5 Index-Suche in der Palette (2026-08-05)**: Specs aus einem
  Index-Repo suchen, einfügen und ziehen; `GET /api/v1/spec?source=` löst
  beliebige Quellen auf, die Detail-Antwort trennt `id` (deklarierter Name)
  und `source` (Ref für `composition.uses`).
  **Verifikation: 523 Pytest, 6/6 Playwright (+1 Discovery-E2E gegen ein
  echtes Git-Repo), Composer-Build 486 kB, ruff clean.**
- **P5 Git-Quellen + Discovery abgeschlossen (2026-08-04/05)**: Spec-Ids
  `git+<url>[#<pfad>]`, Tags als Versionen (`v1.2.0` bzw. `<pfad>/v1.2.0`),
  Bare-Clone-Cache (`SPECCIFY_GIT_CACHE`), Lockfile v4 mit `source_commit`-Pin,
  `--offline` auch für Git; Discovery über Index-Repos (eine Datei pro
  Spec-Repo, `schema/index-entry.schema.json`, Vorlage in `index/`) mit
  `speccify search`, MCP-Tool `search` und `GET /api/v1/index`; eine
  `MultiRegistry`-Fassade bringt Git-Quellen in Komposition, Mocks und Builds.
  Doku [`docs/git-sources.md`](../docs/git-sources.md).
  **Verifikation: 521 Pytest grün (+52 gegenüber P4), 5/5 Playwright,
  `-m app_build` grün, ruff clean.** Tag-Vorschlag: `v0.20.0-p5-git-quellen`.
- **P4 Projekt-Builds abgeschlossen (2026-08-04)**: `kind: app` mit `app:`-Block
  (Routen/Theme/Env) und dritter Wiring-Aktion `navigate:`; Core-Codegen
  `codegen/app_react.py` erzeugt ein Vite-React-Projekt (Hash-Router ohne
  Router-Dependency, ein Zustandsknoten für Wiring + Route, Theme-Tokens als
  CSS-Variablen, `app.env` über `import.meta.env`); Füllung wahlweise Mocks
  (mit Re-Export als sichtbarem Import-Swap) oder generierte Implementierungen;
  Adapter `speccify build` / MCP-Tool `build` / `POST /api/v1/build`
  byte-identisch; Beispiel-App `@org/demo-app` (4 Screens). Doku
  [`docs/app-builds.md`](../docs/app-builds.md).
  **Verifikation: 470 Pytest, `pytest -m app_build` grün (echter `tsc` +
  `vite build` + Browser-Durchlauf, 67 s), ruff clean.**
  Tag-Vorschlag: `v0.19.0-p4-app-builds`.
- **P3 Verfeinerung Runde 2 (2026-08-04)**: Canvas rendert die **generierte
  Mock-Closure** (neuer Endpoint `POST /api/v1/mock/draft` für ungespeicherte
  Entwürfe + Browser-Kompilat via sucrase in `apps/composer/src/mockRuntime.ts`)
  statt den API-Contract nachzuzeichnen; zweiter Canvas-Modus „Vorschau"
  (Dokument-Mock am Stück, Verdrahtung im generierten Code); **Drag & Drop**
  (Palette → Canvas/Slot, Knoten am Griff umhängen; Desktop-Fenster mit
  `disable_drag_drop_handler()`). **Verifikation: 426 Pytest, 5/5 Playwright,
  Composer-Typecheck + Build (484 kB), 18 Desktop-Tests, clippy/fmt, ruff
  clean.** Tag-Vorschlag: `v0.18.0-p3-composer-mock-bundle`.
- **R5 Distribution abgeschlossen (2026-08-02)** — [`plans/archive/r5-distribution.md`](./plans/archive/r5-distribution.md):
  **R5.1 ✅** MCP-Binaries als Tauri-Sidecars im `.app` (kein `cargo install`
  mehr nötig; Auflösung mitgeliefert > PATH, Quelle im Server-Tab sichtbar).
  **R5.2 ✅** Python-Engine ohne Repo: Payload (eigene Wheels + gehashte
  Pins aus `uv.lock` + Composer-SPA + Fixtures, 612 KB) im Bundle, venv-Bau
  per `uv` aus dem Umgebungs-Tab, Composer läuft wahlweise gegen Repo (D3)
  oder gebündelte Engine; `speccify-mcp` wird auf die Engine-venv aufgelöst.
  Offen in R5.2: `uv` selbst mitliefern.
  **R5.3 ⏸ vorbereitet (2026-07-31)**: `bundle.macOS` (Hardened Runtime,
  minimumSystemVersion 10.15; Identity bewusst nur über Env),
  `scripts/release_macos.sh` (Preflight → Build → Signatur-/Gatekeeper-/
  Staple-Verifikation inkl. jedes Sidecars) und [`docs/release.md`](../docs/release.md).
  **Blockiert auf BO-Aktion:** Developer-ID-Zertifikat + App-Specific
  Password, dann `./scripts/release_macos.sh` — erst dieser Lauf beweist,
  dass Signatur und Notarisierung durchgehen. Danach R5.4 Updater, R5.5
  Download-Seite + dotagent archivieren.
  **R5.4 ⏸ verdrahtet (2026-08-01)**: `tauri-plugin-updater` eingebunden,
  aber inert bis ein `pubkey` in `tauri.conf.json` steht — **BO-Aktion:**
  `tauri signer generate -w ~/.speccify/updater.key`, Public Key eintragen.
  **R5.5 ✅ (2026-08-02)**: Download-Seite `/download/` in `apps/marketing`
  (dmg-Link nur bei gesetztem `PUBLIC_DOWNLOAD_URL`, sonst Selbstbau-
  Anleitung), Doku zur dotagent-Ablösung entschärft; offen bleibt dort nur
  die **BO-Aktion** „dotagent-Repo archivieren" (fremdes Repo, README-Text
  liegt im Plan bereit).
  Außerdem: `./scripts/dev.sh` baut/startet die App idempotent in einem
  Kommando. **Tag-Vorschlag: `v0.17.0-r5-bundling`.**
- **Toolkit-Vollausbau ABGESCHLOSSEN (2026-07-27)** — [`plans/archive/toolkit-discovery-terminal.md`](./plans/archive/toolkit-discovery-terminal.md) T0–T8 ✅: Rust-MCPs Exec (:8765, Kontrakt-Harness 28/28), Parallels (:8766), Discovery (:8767, `mcp_list` mit client_config), desktop-ui (:8768, `ask_bo`); Toolbox (TOML, 3 Quellen), Settings/Working Dir, Agent-Terminal (PTY + Autostart, Copy/Paste), ask_bo-Sidebar (Tastatur, robuste Zustellung), Server-Tab nativ (Supervisor-Start/Stop). Doku: [`docs/toolkit.md`](../docs/toolkit.md). **Tag-Vorschlag: `v0.16.0-toolkit-discovery-terminal`.**
- **Offene Anschlüsse**: (a) iKanbanAi an Discovery/ask_bo anbinden (drüben); (b) Rust-Plan-Reststufen R3 System-CLI / R5 Distribution ([`plans/archive/rust-neustart-toolkit-mcps.md`](./plans/archive/rust-neustart-toolkit-mcps.md)) nach Dogfooding; (c) danach zurück zur Produkt-Roadmap: Composer/Specs schärfen (P3-Rest: Mock-Bundle-Rendering, Drag&Drop; P4 Builds; P5 Git-Quellen). BO-Empfehlung fürs Dogfooding: `cargo install --path crates/{exec,discovery,parallels}-mcp`, dann Server-Tab.
- Desktop-App: A0+A1 abgenommen ([`plans/archive/desktop-app-und-composer.md`](./plans/archive/desktop-app-und-composer.md) abgeschlossen); Composer-Walkthrough für BO-Test weiter offen: [`docs/composer-tristate-walkthrough.md`](../docs/composer-tristate-walkthrough.md).
- **Rumprobieren im Composer** (User: „dann verfeinern wir"): `./scripts/dev-up.sh` → <http://localhost:5173>. Erkenntnisse fließen in die nächste Verfeinerungs-Runde.
- Offen aus P2: Stage 4 (voller API-Conformance-Harness) nachziehen. Aus P4 bewusst offen: nur Target `react`, Routen ohne Parameter/Guards, `app:`-Routen noch nicht visuell im Composer editierbar.
- Tag-Vorschläge an User: `v0.12.0-p2-api-mocks`, `v0.13.0-p3-composer-mvp`, `v0.14.0-p3-composer-verfeinerung-1` (selbst nicht gesetzt, vgl. `rules.md`).

## Phase 1d (Steps 1–6 abgeschlossen, 2026-05-19)
- **Step 1 erledigt** — Backend-MVP läuft offline gegen Replay-Cache: `/api/v1/specs`, `/api/v1/render` mit Fehler-Mapping (`cache_miss` 422, `spec_invalid`/`unknown_target`/`bad_request` 400). 7 Backend-Tests.
- **Step 2 erledigt** — Frontend-Skeleton unter `apps/web/frontend/` als Next.js 15 / React 19 / TS (pnpm@10.33.3, Node ≥22 LTS, strict TS, `@/*`-Alias). `next.config.ts` rewriteet `/api/v1/*` → `http://localhost:8000`. `lib/api.ts` mit typed fetch + zod-Schemas + `ApiError`-Klasse. Komponenten: `SpecPicker`, `SpecEditor` (Monaco dynamic ssr:false), `RenderOutput` (Tabs + Copy + `generator_pin`-Disclosure), `ErrorPanel` (cache_miss-Hint).
- **Step 3 erledigt** — Render-Flow + Output-Panel: „Render React"-Button, „Spec edited — cache miss expected"-Indikator, RenderOutput zeigt TSX (Monaco readonly) + Copy + Pin-Detail, ErrorPanel branchet auf `cache_miss`. Playwright-Smoke explizit auf Step 5 (CI-Job) verschoben.
- **Step 4 erledigt** — Cross-Consistency-Test `apps/web/backend/tests/test_cross_consistency.py` rendert `@org/button@0.1.0` über `speccify_cli.commands.pull.run_pull`, `speccify_mcp.tools.run_pull` und `speccify_web_backend.services.render.render_spec_from_yaml` und vergleicht `org/Button.tsx`-Bytes byte-identisch. `pyproject.toml` Dev-Group um `speccify-mcp` erweitert (war vorher nur transitiv für mcp-Tests verfügbar); `uv sync --reinstall` nötig (bekanntes editable-Side-Quest). `apps/web/README.md` um Cross-Consistency-Abschnitt erweitert; Top-Level-`README.md` um „Browser-Playground (`apps/web/`)"-Abschnitt + Plan-Verweise (1a/1b/1c archiviert, 1d aktiv).
- **Verifikation**: **183 Pytest grün** (182 + 1 Cross-Consistency-Test), `ruff check` + `ruff format --check` clean. Frontend `pnpm build` weiterhin grün.
- **Step 5 erledigt** — `.github/workflows/ci.yml` um zwei Jobs erweitert: `apps/web backend (offline)` (`uv sync --all-packages` + `uv run pytest apps/web/backend/tests -v`, deckt auch Cross-Consistency-Test ab) und `apps/web frontend build` (Node via `apps/web/frontend/.nvmrc=22`, pnpm@10.33.3 via `pnpm/action-setup@v4`, `pnpm install --frozen-lockfile` + `pnpm typecheck` + `pnpm build`). Lokal verifiziert (grün). Optionalen Playwright-Smoke bewusst ausgelassen — Mehrwert gegenüber Cross-Consistency-Test gering, Aufwand (Backend+Frontend parallel im CI) hoch.
- **Step 6 erledigt** — `speccify-plan.md` Phase 1d als abgeschlossen markiert + Tool-Vertrag `/api/v1/...` inline dokumentiert (Endpoints, Fehler-Codes `cache_miss`/`spec_invalid`/`unknown_target`/`bad_request`, Offline-/Replay-Cache-Limitierung, Cross-Consistency-Vertrag, CI-Jobs). `AGENTS.md` „Aktuelle Phase“ auf „Phase 1d abgeschlossen / nächste Phase 2 (Registry-MVP)“ umgestellt. Tag-Vorschlag `v0.4.0-phase-1d` an User dokumentiert (selbst nicht gesetzt, vgl. `rules.md`).
- [x] Phasen-Plan `phase-1d-browser-playground.md` nach `.agent/plans/archive/` verschoben (`isActive: false`); `AGENTS.md` referenziert nur noch den Archiv-Pfad (2026-05-21).
- Nächster Schritt: **Phase-2-Plan-Entwurf (Registry-MVP)** nach User-Tag `v0.4.0-phase-1d`.
- [x] **Phase-2-Plan-Skelett** geschrieben (2026-05-22): [`.agent/plans/phase-2-registry-mvp.md`](./plans/archive/phase-2-registry-mvp.md) (`isActive: true`). Scope (Django-Backend `registry/`, Auth+2FA, `publish`/`search`/`yank`/`login`/`whoami`, Web-UI, Lockfile-Bump auf `schema_version: 2` mit `signature`+`yank_status`, RemoteRegistry-Resolver-Integration, Workspaces nativ), 10 Open Questions als Round-1-Klärung mit User, Stages 0–9 als Skelett (Delivery-Steps folgen in Round 2 nach Klärung). Keine Code-Änderungen in dieser Session — nur Plan-Hygiene analog zu früheren Phasen-Kickoffs.
- [x] **Phase-2 Stage 0 abgeschlossen** (2026-05-23): Alle 10 Open Questions mit User geklärt (Django 5.x, Django-Templates in `registry/`, Postgres BYTEA, TOTP only, opaque Tokens, Device-Code-Login, Self-Service-Scopes mit Sperrliste, Workspaces auf Phase 3 verschoben, Web-UI in `registry/`, kein Default-Registry-Hostname). Workspaces-Stage aus Phase-2-Plan gestrichen, Round-2-Delivery-Steps (Step 1–8) in [`phase-2-registry-mvp.md`](./plans/archive/phase-2-registry-mvp.md) eingefügt.
- [x] **Phase-2 Stage 1 abgeschlossen** (2026-05-23): `registry/` als uv-Workspace-Member mit Django-5-Skeleton (`speccify_registry/{settings,urls,wsgi,asgi,manage}.py`), App `registry_api` mit 5 Modellen (`Scope`, `Spec`, `SpecVersion`, `ApiToken`, `ScopeReservation`), initiale Migration `0001_initial.py` eingecheckt, Docker-Compose-Stack (Postgres 16 + Django-Dev-Server, Port 8001) + `Dockerfile.dev`, in-memory SQLite-Fallback für Tests (`SPECCIFY_REGISTRY_TEST=1`), 8 Stage-1-Tests grün.
- [x] **Phase-2 Stage 2 abgeschlossen** (2026-05-23): Auth-Backend (`api/tokens.py` argon2-Hashing + Token-Prefix-Lookup, `api/authentication.py` Bearer-DRF-Auth, `api/device_codes.py` Issue/Approve/Poll-Flow mit Cache-Handover, `api/two_factor.py` TOTP via `django-otp`), Web-Views (`web/{forms,views,urls}.py`: Signup/Login/Logout/2FA-Setup/Tokens-CRUD/Device-Approve) + 5 Templates, REST-Endpoints `/api/v1/registry/auth/device-code{,/poll}` + `/whoami` mit Bearer-Auth. CLI: `_credentials.py` (XDG-Pfad, `0600`-Perms, TOML), `speccify login` (Device-Code, `webbrowser.open`, Polling) + `speccify whoami`. ApiToken-Modell um `token_prefix` erweitert, neues `DeviceCode`-Modell + Migration `0002`. Pytest-Config split: Root läuft mit `-p no:django` ohne registry (188 grün), `registry/` mit eigenem `pytest.ini` und `pytest-django` (30 grün, inkl. CLI-E2E gegen `live_server`). CI-Job `registry backend (django)` ergänzt. **218 Tests grün gesamt**, ruff clean.
- [x] **Phase-2 Stage 3 Backend abgeschlossen** (2026-05-23): `api/publish.py` mit `parse_and_validate` (YAML→`speccify_core.SchemaValidator`→Spec-ID-Regex→Version-Regex) und `publish()` (Auto-Claim mit `ScopeReservation`-Sperrliste, Ownership-Check, idempotenter Re-Publish bei Byte-Identität, 409 bei Byte-Drift). REST-Endpoints `POST /api/v1/registry/specs/publish` (JSON oder multipart, Bearer-Auth + frische 2FA), `GET .../specs/<scope>/<name>` (Version-Liste), `GET .../specs/<scope>/<name>/<version>` (YAML + Hash + Yank-Status). 15 neue Tests (`test_publish.py`): Happy, idempotent, conflict, missing-auth, stale-2FA, invalid-YAML, schema-violation, reserved-scope, scope-forbidden, missing-yaml-payload, versions-list, version-404, version-detail, multipart-upload, revoked-token. Stage 3 CLI/MCP-Adapter (publish-Command + MCP-Tool) bewusst auf Folge-Session vertagt. Pytest-Aufruf für Registry braucht `-c registry/pytest.ini` (Root-`pyproject.toml` würde sonst überschreiben); CI entsprechend angepasst. **233 Tests grün gesamt** (188 + 45), ruff clean.

## Beschreibung
Spec-First-Plattform für sprach-/framework-unabhängige Komponenten-Spezifikationen.
Phase 0 etabliert das Spec-Schema v0, den Validator und die CLI `speccify lint` als
Fundament für alle weiteren Phasen.

## Aktueller Stand
- `schema/spec.schema.json` v0 vorhanden (Draft 2020-12).
- `speccify_core` enthält `SpecLoader` + `SchemaValidator` mit Tests.
- `speccify_cli` mit Sub-Command `lint` (Typer); `speccify lint specs/*.yaml` läuft grün.
- 5 Referenz-Specs unter `specs/` (button, contact-form, http-api-client,
  onboarding-wizard, login-screen) — alle valide.
- Pytest grün (12 Tests). Ruff/Format-Check/Mypy grün.
- Dev-Tooling vollständig: `ruff`, `mypy`, `types-PyYAML` als Dev-Deps gepinnt.
- GitHub-Actions-Workflow `.github/workflows/ci.yml` deckt Lint + Format-Check +
  Mypy + Pytest + `speccify lint` ab.

## Nächste Schritte
- **NEUER AKTIVER PLAN (2026-08-07)**: [`plans/skills-als-format.md`](./plans/skills-als-format.md)
  — Playbooks werden **Agent Skills** (`SKILL.md` als Speicherformat, kein
  Export). BO-Entscheid zum Namen: *ein Playbook ist ein Skill, der andere
  Skills referenziert*. Grund: Ein Playbook war erst nach Installation
  nützlich, ein Skill wirkt, sobald er im Verzeichnis liegt. Der Spec ist
  herstellerneutral (agentskills.io), hat mit `metadata` eine offizielle
  Hintertür für Fremdfelder und keine Vorgaben für den Body. Was Speccify
  draufsetzt: Frische, Pinning, Komposition, Herkunft — plus zwei neue,
  kleine Hebel (Lint gegen die Best-Practice-Checkliste, Token-Budget), die
  auch für Leute nützlich sind, die nur Skills haben. **S0 (Refinement) offen.**
- **VERÖFFENTLICHT (2026-08-07)**: Repo ist öffentlich unter
  <https://github.com/mhennemeyer/speccify>, `main` ist Default. Der 2009er
  RSpec-Klon gleichen Namens bleibt unangetastet unter `master` — nichts
  verloren, alte Links funktionieren.
  **Website live**: <https://mhennemeyer.github.io/speccify/> (21 Seiten), per
  `pages.yml` bei jedem Push auf `main`. `public/CNAME` trägt speccify.io; die
  Domain wird aktiv, sobald der BO DNS setzt und die Custom-Domain in den
  Pages-Einstellungen einträgt (Werte in `docs/launch.md`).
  **Release-Pipeline gelaufen (BO-Auftrag)**: Tag `v0.2.0`, Build grün,
  Entwurfs-Release mit `.dmg` + `.app.tar.gz` (je 23 MB). Bundle geprüft —
  arm64, vier Sidecars, Engine mit 4 Wheels, Viewer-SPA, alle 10 Playbooks,
  Signatur `adhoc`. **Entwurf noch nicht veröffentlicht.** Erster Lauf war rot:
  Tauri prüft die **Existenz** von `APPLE_CERTIFICATE`, nicht den Inhalt — ein
  leeres Secret ließ `security import` scheitern. Anmeldedaten werden jetzt
  gestaged und nur bei Inhalt exportiert. Auslöser auf `v[0-9]+.[0-9]+.[0-9]+`
  verengt (`v*` hätte die zwölf Phasen-Tags getroffen).
  **Erster CI-Lauf überhaupt** (es gab nie ein Remote) hat sechs echte Fehler
  freigelegt, alle behoben: Playwright 1.44 kennt Ubuntu 24.04 nicht
  (`libasound2` → `libasound2t64`), Node 20 vs. Astros >= 22.12 (jetzt eine
  Quelle: `.nvmrc`), `ruff format` lief lokal nie mit, ein Typfehler in
  `search.py` — **weil mypy lokal kaputt war**: `.venv/bin/mypy` hatte einen
  Shebang auf die venv eines fremden Projekts, von iCloud hierher
  synchronisiert. lychee ohne `--root-dir` (450 Scheinfehler), danach ein
  echter: fehlendes `favicon.svg` auf allen Doku-Seiten. Dabei fiel die letzte
  alte Beschreibung auf („npm für Spezifikationen") — sie stand in
  `astro.config.mjs`, nicht in Markdown, deshalb hatte W5 sie übersehen.
  **Achtung iCloud**: Das Repo liegt unter `~/Desktop` und wird synchronisiert;
  70 Konfliktkopien (`datei 2.ext`) lagen im Arbeitsverzeichnis und haben die
  lokale Testzahl still verfälscht (253 statt 157). Per `.gitignore`
  ausgesperrt — das eigentliche Problem bleibt der Ablageort.
- [x] Phase 1b Step 1 — `speccify init <name> [--target react]` (minimal:
      nur `speccify.yaml`, kein Skeleton). 7 neue CLI-Tests grün, alle 81
      Tests grün, ruff/format/mypy clean.
- [x] Phase 1b Step 2 — Lockfile-Schema-Erweiterung `generator.oneOf`
      (`template`/`llm`), neuer `LlmGeneratorPin` + `AnyGeneratorPin`-Union,
      `TemplateGeneratorPin`-Alias für Rückwärtskompatibilität. 4 neue Tests
      grün (LLM mit/ohne `seed`, gemischtes Lockfile, Schema-Reject bei
      kombinierten Feldern), 85 Tests gesamt grün, ruff/format/mypy clean.
- [x] Phase 1b Step 3 — Replay-Cache + `LlmClient`-Protokoll
      (`speccify_core.codegen.replay`: `CacheKey`/`ReplayCache`/`CacheMissError` +
      `LlmClient`-Protokoll + `ReplayCacheClient`-Wrapper mit `bind_key`-Vertrag).
      15 neue Tests grün, 100 Tests gesamt, ruff/format/mypy clean.
- [x] Phase 1b Step 4 — React-LLM-Adapter (`speccify_core.codegen.react_llm`)
      mit LLM-Pin, Prompt-Template, minimaler Normalisierung, Klammer-Heuristik
      für TSX-Validität, PascalCase-Output (`<scope>/<Name>.tsx`); Dispatcher
      `render_for_target` + `TargetRender` + `SUPPORTED_TARGETS=("react",)`;
      Re-Exports in `speccify_core.__init__`. 20 neue Tests grün, 120 Tests
      gesamt, ruff/format/mypy clean. `pull`/`verify` bleiben in Step 4 noch
      beim Stub — Umstellung ist Step-5-Aufgabe.
- [x] Phase 1b Step 5a — **Provider-Switch von Anthropic auf AWS Bedrock**
      (firmenweite Default-Infrastruktur). Live-`BedrockClient`
      (`speccify_core.codegen.bedrock_client`) via `boto3` `converse`,
      Modell-Pin `bedrock/eu.anthropic.claude-opus-4-7` (`eu-central-1`),
      `temperature` weggelassen (deprecated für Opus-4-7),
      Standard-AWS-Credential-Chain. `boto3>=1.35` als optional-Dep
      `speccify-core[bedrock]` (+ Workspace-Mirror). Maintainer-Skript
      `scripts/record_llm_cache.py` umgestellt, eingebauter `.env`-Loader.
      10 neue Tests in `core/tests/test_bedrock_client.py` (Modell-Strip,
      fehlendes `boto3`, Text-Block-Extraktion via Fake-boto3, Region,
      Default-Chain, Schema-Fehler, Exception-Wrapping). **Live-Aufnahme
      erfolgreich**: 6/6 Cache-Einträge unter `tests/fixtures/llm-cache/`
      (~36 KB) eingecheckt. 131 Tests grün, ruff/format/mypy clean.
- [x] Phase 1b Step 5b — `pull`/`verify` umgestellt auf
      `render_for_target(spec, target, llm_client=...)`. Neue Flags
      `--offline/--no-offline` (Default offline) und `--cache-dir`
      (Default-Repo-Pfad `tests/fixtures/llm-cache`, Env-Override
      `SPECCIFY_CACHE_DIR`) auf `pull` und `verify`. Gemeinsamer Helper
      `speccify_cli.commands._llm_client.build_replay_client`. `pull`
      schreibt `LlmGeneratorPin` (`provider=bedrock`, `model`,
      `prompt_version`, `seed`, `cache_key=sha256:<digest>`) pro Spec
      ins Lockfile. `verify` prüft Modell-/Prompt-/Seed-/Cache-Key-Drift
      gegen Re-Render und meldet harte Cache-Misses. Neue Helper-Methode
      `Lockfile.with_generator(spec_id, generator)`. example-project
      regeneriert: 3 TSX-Dateien (`org/Button.tsx`, `org/ContactForm.tsx`,
      `org/OnboardingWizard.tsx`), Lockfile enthält LLM-Pins. 9 neue
      CLI-Tests (5 `test_pull.py` inkl. Determinismus + offline-Miss,
      6 `test_verify.py` inkl. Modell-Drift + Disk-Drift). **134 Tests
      grün**, ruff/format clean.
- [x] Phase 1b Step 5c — CI-Workflow um E2E-Smoke erweitert: bestehender
      `example-project`-Step nutzt explizit `--offline` für `pull`/`verify`;
      neuer Step `init + add + lock + pull + verify` läuft in `mktemp -d`
      gegen `registry-fixtures/` und `tests/fixtures/llm-cache/` (Binary
      direkt aus `.venv/bin/speccify`, weil `uv run` aus fremder CWD den
      Workspace-Kontext verliert). `README.md` erweitert um End-to-End-
      Smoke und Maintainer-Doku zu `scripts/record_llm_cache.py`. Lokal
      1:1 nachgestellt — beide Smoke-Pfade grün. 134 Tests grün,
      ruff/format clean.
- [x] Phase 1b Step 6 — Master-Plan-Sync: `speccify-plan.md` markiert Phase 1b als abgeschlossen (React-LLM/Bedrock/Replay-Cache + `pull`/`verify --offline` + CI-E2E), `AGENTS.md` „Aktuelle Phase" auf 1c umgestellt, Phasen-Plan-Step 5c + 6 abgehakt. Tag `v0.2.0-phase-1b` als Vorschlag an User offen (nicht selbst gesetzt).
- [x] Annotated Tags lokal gesetzt: `v0.1.0-phase-1a` (→ `d28cb33`) und `v0.2.0-phase-1b` (→ `8c90511`). Kein Git-Remote vorhanden → Push entfällt; User kann später `git push --tags` ausführen.
- [x] Phasen-Plan `.agent/plans/phase-1c-mcp-server.md` geschrieben (MCP-Server `speccify-mcp`, stdio-only, 6 Tools = CLI-1:1, Replay-Cache-offline-CI, Tag-Vorschlag `v0.3.0-phase-1c`).
- [x] **Phase 1c Step 0** — `mcp[cli]>=1.27.1,<2.0` in `mcp/pyproject.toml` gepinnt (PyPI-Latest 1.27.1, Extra `cli`, `requires_python>=3.10`); `uv sync --all-packages` + `uv.lock` aktualisiert; `uv run pytest` → 134 grün; ruff clean.
- [x] **Phase 1c Step 1** — Server-Skeleton: `speccify_mcp.server.build_server(ServerConfig)` liefert `FastMCP(name="speccify-mcp")` ohne Tools/Resources/Prompts; `speccify_mcp.cli:main` mit Argparse (`--project`/`--log-level`), Env-Fallback (`SPECCIFY_PROJECT_ROOT`/`SPECCIFY_LOG_LEVEL`), stderr-Logging, `server.run(transport="stdio")`. Console-Script `speccify-mcp` in `mcp/pyproject.toml`. 9 neue Unit-Tests in `mcp/tests/test_server_skeleton.py` (leeres tools/resources/prompts-list, Parser, Project-Root-Auflösung). **143 Tests grün**, ruff/format clean.
- [x] **Phase 1c Step 2** — Read-only Tools: `mcp/src/speccify_mcp/tools/{resolve,lint,render}.py` als reine Adapter-Funktionen, registriert über `FastMCP.tool()` in `server._register_readonly_tools`; `render` mit `ReplayCacheClient` (Default `tests/fixtures/llm-cache`, Env-Override `SPECCIFY_CACHE_DIR`, offline-Default). 12 neue Tests in `mcp/tests/test_tools_readonly.py` (happy + Fehlerpfad pro Tool, Test-Helper kopiert `example-project/`+`registry-fixtures/`). **155 Tests grün**, ruff/format clean.
- [x] **Phase 1c Step 3** — Write-Tools `lock`/`pull`/`verify` als Adapter unter `mcp/src/speccify_mcp/tools/{lock,pull,verify}.py` (eigener `_workspace.py` ohne `speccify-cli`-Dep, gleiche Konventionen wie CLI: atomares Schreiben, LLM-Pin im Lockfile, `--offline`-Default, Env-Override `SPECCIFY_CACHE_DIR`). Registriert über `FastMCP.tool()` in neuem `server._register_write_tools`. 10 neue Tests in `mcp/tests/test_tools_write.py` (lock happy + fehlendes Manifest; pull happy + fehlendes Lockfile + Target-Mismatch + offline Cache-Miss; verify grün + Disk-Drift + fehlendes Lockfile; **Cross-Consistency CLI ↔ MCP**: `cli.commands.pull.run_pull` und `speccify_mcp.tools.run_pull` produzieren byte-identische TSX-Outputs + Lockfile). **165 Tests grün**, ruff/format clean.
- [x] **Phase 1c Step 4** — Resources + Prompt: `mcp/src/speccify_mcp/{resources,prompts}.py` registrieren `speccify://manifest`, `speccify://lockfile` (mit Hint-Fallback bei fehlendem Lockfile), `spec://{scope}/{name}@{version}` (über `LocalRegistry.fetch` → `Spec.raw_bytes` als YAML), und Prompt `add-spec(spec_ref, out_dir=./src/components)` mit Schritt-Anleitung resolve→lock→pull→verify. Verdrahtet in `server.build_server` (Lazy-Import gegen Zyklus). 8 neue Tests in `mcp/tests/test_resources_prompts.py`; `test_server_skeleton` aktualisiert (2 fixe Resources + 1 Template + 1 Prompt). **173 Tests grün** (165 + 8), ruff/format clean.
- [x] **Phase 1c Step 5** — CI-Smoke `speccify-mcp` (stdio, offline) + Doku: `scripts/mcp_smoke.py` startet Server via `python -m speccify_mcp.cli`, prüft `tools/list` (6 Tools) + `tools/call render @org/button` (offline, TSX + `generator_pin.kind=llm`) + `resources/read speccify://manifest` mit offiziellem `mcp`-Python-Client. Pytest-Wrapper `mcp/tests/test_stdio_smoke.py` (1 Test) ruft das Skript als Subprocess (Symmetrie zu CI). CI-Step `speccify-mcp smoke (stdio, offline)` in `.github/workflows/ci.yml`. `mcp/README.md` neu (Installation, Tools-/Resources-/Prompts-Tabellen, Client-Config-Snippets); Top-Level-README ergänzt um Abschnitt „MCP-Server" + aktualisierte Phase-Liste/Status. **174 Tests grün**, ruff/format clean.
- [x] **Phase 1c Step 6** — Wrap-up: `speccify-plan.md` markiert Phase 1c als abgeschlossen mit inline-Tool-/Resource-/Prompt-Vertrag und Defaults; `AGENTS.md` „Aktuelle Phase" auf „Phase 1c abgeschlossen, nächste 1d (Browser-Playground)" umgestellt; Phasen-Plan-Step 6 abgehakt. Tag-Vorschlag `v0.3.0-phase-1c` an User dokumentiert (selbst nicht gesetzt, vgl. `rules.md`).
- [x] Phasen-Plan `.agent/plans/phase-1b-react-codegen.md` geschrieben
      (LLM-Codegen mit Replay-Cache, minimaler `init`, TSX mit Props/Types).
- [x] Phase 1a Step 5 — `speccify verify`, `lint`-Anpassung, CI-Step (E2E im
      example-project: lock + pull + verify), Master-Plan-Sync (React-first,
      Template-Pin, Sub-Spikes 1a–1d), `.gitignore` für example-project-Artefakte.
- [x] Phase 1a Step 4 — Stub-Codegen + `speccify pull --target react`
      (`speccify_core.codegen.stub` + Jinja-Template, atomares Schreiben,
      Lockfile-Update via `with_generated_files`, 8 neue Tests grün).
- [x] Phase 1a Step 3 — Lockfile-Format, `speccify lock` und `speccify add`
      (`schema/lockfile.schema.json`, `speccify_core.lockfile`,
      `speccify_cli.commands.lock`/`.add` mit gemeinsamem `WorkspaceContext`,
      16 neue Tests grün, deterministischer YAML-Dump).
- [x] Phase 1a Step 2 — MVS-Resolver mit transitiver Auflösung + Diamond-Test
      (`speccify_core.resolver`, `Range`/`Resolver`/`ResolverError`-Hierarchie,
      Diamond `button@0.1.1` über `login-screen.uses: ^0.1.1`).
- [x] Phase 1a Step 1 — Manifest und Pseudo-Registry-Layer
      (`schema/manifest.schema.json`, `speccify_core.manifest`,
      `speccify_core.registry`, `registry-fixtures/` mit 5 Specs +
      `button@0.1.1`, `example-project/`).
- [x] **Phase 1a-0 — Rebrand auf `speccify`** abgeschlossen
      (siehe [`.agent/plans/archive/phase-1a0-rename-to-speccify.md`](./plans/archive/phase-1a0-rename-to-speccify.md)).
- [x] Naming-Entscheidung getroffen: `speccify`
      (siehe [`.agent/plans/archive/naming-plan.md`](./plans/archive/naming-plan.md)).

## Blocker
Keine.