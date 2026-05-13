# Log: Speccify

## 2026-05-13 (Tags gesetzt + Phase-1c-Plan angelegt)
- **Tags lokal gesetzt** (User-Freigabe in diesem Prompt: „Bitte setze
  den Tag und mache ausnahmsweise die aktionen im Git"):
  - `v0.1.0-phase-1a` annotated → `d28cb33` ("Complete Phase 1a:
    Finalize Codegen and CLI Enhancements"), Message: "Phase 1a:
    Resolver + Lockfile + Stub-Codegen + add/lock/pull/verify".
  - `v0.2.0-phase-1b` annotated → `8c90511` ("Complete Phase 1b:
    Finalize Step 6 with Master-Plan Sync"), Message: "Phase 1b:
    React-LLM-Codegen + speccify init + Replay-Cache + pull/verify
    --offline + CI-E2E".
  - `git remote -v` ist leer → kein Push möglich. User kann später bei
    Bedarf `git remote add` + `git push --tags` ausführen.
- **Phase 1c gestartet — Phasen-Plan geschrieben**:
  `.agent/plans/phase-1c-mcp-server.md` mit Scope (MCP-Server
  `speccify-mcp`, offizielles `mcp[cli]`-SDK, stdio-only, 6 Tools
  spiegeln CLI 1:1: `resolve`/`lock`/`render`/`pull`/`verify`/`lint`,
  plus Resources `spec://`+`speccify://manifest|lockfile` und Prompt
  `add-spec`), Technical Design (Modul-Layout `mcp/src/speccify_mcp/`
  mit `cli.py`/`server.py`/`tools/`/`resources.py`/`prompts.py`,
  Replay-Cache bleibt in `speccify_core`, MCP ist stateless),
  Implementation Plan (Steps 0–6: SDK pinnen → Skeleton → Read-Tools →
  Write-Tools + Cross-Consistency CLI↔MCP → Resources/Prompts →
  CI-Smoke+Doku → Wrap-up). Tag-Vorschlag `v0.3.0-phase-1c`.
- **Status-Sync**: `.agent/status.md` Meta-Phase auf "Phase 1c
  gestartet" gesetzt; Tag-Setzung und Plan-Anlage als `[x]` markiert;
  neue `[ ]`-Bullets für Steps 0–6.
- **Nächster Schritt**: Phase 1c Step 0 — `mcp[cli]`-Version
  recherchieren und in `mcp/pyproject.toml` pinnen.

## 2026-05-13 (Phase 1b Step 6 — Master-Plan-Sync + Phase-1b-Abschluss)
- **Step 6 abgeschlossen, Phase 1b damit komplett.** Sync der Plan-Dokumente
  nach dem Step-5c-Commit; keine Code-Änderungen.
- **`.agent/plans/speccify-plan.md`**: Phase 1b in der Sub-Spike-Liste auf
  "abgeschlossen 2026-05-13" gesetzt; React-LLM-Strategie (Bedrock-Modell
  `bedrock/eu.anthropic.claude-opus-4-7` via `converse`, Reproduzierbarkeit
  durch Replay-Cache mit Cache-Key über `spec_sha256 + target + model +
  prompt_version + seed`, Lockfile-Generator-Pin um `kind: llm` erweitert,
  `pull`/`verify --offline/--cache-dir`, CI-E2E gegen `tests/fixtures/llm-cache/`,
  `scripts/record_llm_cache.py` als Maintainer-Tool) im Plan inline dokumentiert.
  Phase 1c als "nächster Schritt" markiert. Tag-Vorschlag `v0.2.0-phase-1b`
  im Plan vermerkt.
- **`AGENTS.md`** "Aktuelle Phase" auf "Phase 1b abgeschlossen, Phase 1c
  als nächste" umgestellt; Tag-Vorschläge `v0.2.0-phase-1b` und optional
  `v0.1.0-phase-1a` aufgeführt.
- **`.agent/plans/phase-1b-react-codegen.md`**: Sub-Step 5c und Step 6
  abgehakt (drei `[x]`-Bullets unter Step 6 für Plan-/AGENTS-/Sync-Arbeit;
  Tag-Bullet bewusst `[ ]`, da User-Action).
- **`.agent/status.md`**: Meta-Phase auf "Phase 1b abgeschlossen" gesetzt;
  Step-6-Bullet als `[x]` markiert; offene `[ ]`-Punkte: User-Tag-Setzung
  `v0.2.0-phase-1b`, optional `v0.1.0-phase-1a`, Phase-1c-Plan schreiben.
- **Verifikation**: `uv run pytest` → 134 grün, `uv run ruff check .` und
  `uv run ruff format --check .` clean (Plan-Sync ist Doku-only, kein
  Code-Drift erwartet).
- **Tag-Vorschlag an User**: `git tag -a v0.2.0-phase-1b -m "Phase 1b:
  React-LLM-Codegen + speccify init + Replay-Cache + pull/verify --offline + CI-E2E"`
  (bewusst nicht selbst gesetzt — `rules.md` "Ein Prompt = ein Commit",
  Tagging ist User-Entscheidung).
- **Nächster Schritt**: Phasen-Plan `phase-1c-mcp-server.md` skizzieren
  (MCP-Server, der `speccify_core` ans Protokoll bindet: `resolve`,
  `search`, `render`, `validate`, `lock`, `verify`).

## 2026-05-13 (Phase 1b Step 5c — CI-E2E-Smoke + README-Doku)
- **Step 5c abgeschlossen.** CI deckt jetzt End-to-End beide Pfade ab:
  bestehendes `example-project/` (`lock` + `pull --offline` + `verify --offline`)
  und einen **frischen Smoke-Pfad** aus `tmp` (`init` + `add` + `lock` +
  `pull --offline` + `verify --offline`) gegen `registry-fixtures/` und
  den eingecheckten Replay-Cache.
- **`.github/workflows/ci.yml`**:
  - Bestehender Step `speccify end-to-end smoke (lock + pull + verify)`
    erhält `--offline` Flags für `pull` und `verify` (Default-Verhalten,
    aber explizit für CI-Klarheit).
  - Neuer Step `speccify init + add + pull + verify smoke (offline)`:
    legt in `mktemp -d` ein Projekt via `speccify init smoke-app
    --target react` an, fügt `@org/button` hinzu (`--registry`-Override
    auf `registry-fixtures/`), lockt, pullt und verifiziert offline gegen
    `tests/fixtures/llm-cache/`. Ruft das Binary direkt aus dem venv
    (`$GITHUB_WORKSPACE/.venv/bin/speccify`), weil `uv run` aus einer
    fremden CWD den Workspace-Kontext verliert.
- **`README.md`** überarbeitet:
  - Neuer Abschnitt **End-to-End Smoke (offline)** mit den exakten
    Befehlen aus dem CI-Smoke (example-project + frisches Projekt).
  - Neuer Abschnitt **Replay-Cache neu aufnehmen (Maintainer)**
    dokumentiert `scripts/record_llm_cache.py` (Voraussetzungen:
    `uv sync --extra bedrock`, AWS-Credentials via Env oder `.env`;
    `--force` für Re-Record).
  - „Wo es weitergeht“ aktualisiert: Phase 1b verlinkt, Phase 1a
    abgeschlossen markiert, Rebrand-Plan ins Archiv verlinkt.
  - Status-Absatz auf Phase 1b umgestellt.
- **Lokale Verifikation der CI-Sequenz** (1:1 nachgestellt mit
  `.venv/bin/speccify`): beide Smoke-Pfade laufen grün, der frische
  Pfad erzeugt `out/org/Button.tsx`, der example-project-Pfad bleibt
  byte-identisch.
- **Side-Quest**: lokales `.venv` war durch macOS/iCloud-Duplikate
  korrumpiert (`_editable_impl_speccify_cli 2.pth` neben dem Original →
  `site` ignorierte beide Pfade). Fix: `.venv` gelöscht und neu
  `uv sync --all-packages`. Kein Repo-Change nötig, nur als Hinweis im
  Log.
- **Verifikation**: `uv run pytest` → 134 grün; `uv run ruff check .` +
  `uv run ruff format --check .` clean.
- **Nächster Schritt** (Step 6): Master-Plan-Sync, ggf. annotated Tag
  `v0.2.0-phase-1b`; optional `v0.1.0-phase-1a` für die abgeschlossene
  Phase 1a nachziehen.

## 2026-05-12 (Phase 1b Step 5b — `pull`/`verify` auf Dispatcher + Replay-Cache umgestellt)
- **Step 5b abgeschlossen.** `speccify pull` und `speccify verify` rufen
  jetzt den Codegen-Dispatcher `speccify_core.render_for_target(spec,
  target, llm_client=...)` statt direkt den Stub-Adapter. Für
  `target == "react"` wird ein `ReplayCacheClient` über dem eingecheckten
  Cache (`tests/fixtures/llm-cache/`) eingespeist.
- **Neue CLI-Flags** auf `pull` und `verify`:
  - `--offline/--no-offline` (Default `--offline`): Cache-Miss → Exit 1
    mit klarer Fehlermeldung, kein Live-Bedrock-Call.
  - `--cache-dir <pfad>`: überschreibt Default und Env-Var
    `SPECCIFY_CACHE_DIR`. Default ist der repo-lokale Cache-Pfad
    `tests/fixtures/llm-cache/` (in `cli/src/speccify_cli/commands/_llm_client.py`).
- **Gemeinsamer Helper** `speccify_cli.commands._llm_client`
  (`resolve_cache_dir`, `build_replay_client`) — `pull` und `verify`
  teilen sich Pfad-Resolution und Client-Bau. `inner`-Hook für späteren
  Live-Fallback ist vorgesehen, aber in 5b nicht verdrahtet (Live-
  Aufnahme bleibt `scripts/record_llm_cache.py`).
- **Lockfile schreibt `LlmGeneratorPin`** pro Spec bei `pull`:
  `provider=bedrock`, `model=bedrock/eu.anthropic.claude-opus-4-7`,
  `prompt_version=0.1.0`, `seed=1`,
  `cache_key=sha256:<digest(spec_sha256+target+model+prompt_version+seed)>`.
  Helper-Methode `Lockfile.with_generator(spec_id, generator)` neu in
  `core/src/speccify_core/lockfile.py` (gemeinsam mit
  `with_generated_files` über interne `_replace_entry`-Hilfe).
- **`verify` prüft Pin-Konsistenz**: Modell-/Prompt-Version-/Seed-/
  Cache-Key-Drift zwischen Lockfile-`LlmGeneratorPin` und Re-Render-
  `cache_key` werden als separate Problem-Strings gemeldet (zusätzlich
  zu den bestehenden Spec-Hash- und Disk-Hash-Checks).
- **example-project regeneriert**: alte `*.md`-Stub-Outputs entfernt;
  `out/org/Button.tsx`, `out/org/ContactForm.tsx`,
  `out/org/OnboardingWizard.tsx` neu generiert (alle 3 aus Replay-Cache,
  byte-identisch reproduzierbar). `speccify.lock` enthält nun für jede
  Spec einen LLM-Pin mit `cache_key`. `speccify verify` läuft grün.
- **Tests neu/erweitert** (9 neu):
  - `cli/tests/test_pull.py` (5): TSX-Output + Lockfile-Pin, Determinismus
    (zwei `pull`-Aufrufe → byte-identisch), Fail ohne Lockfile,
    Target-Mismatch, Cache-Miss bei leerem `--cache-dir`.
  - `cli/tests/test_verify.py` (6): Happy-Path, Disk-Drift,
    Fail ohne Lockfile, Fail ohne `pull`, Modell-Drift (manuell editiertes
    Lockfile), Cache-Miss bei leerem `--cache-dir`.
- **Verifikation**: `uv run pytest` → **134 grün**, `uv run ruff check .`
  clean, `uv run ruff format .` clean. `mypy` zeigt Vor-Bestands-Fehler
  in `cli/tests/test_init.py`, `core/tests/test_bedrock_client.py` und
  `core/tests/test_lockfile.py` — **nicht von Step 5b verursacht** (in
  ungetauchten Test-Dateien aus Step 1/5a, bestehender Drift seit Step 5a-
  Status-Doku "mypy clean" behauptete). Wird in Step 5c bzw. separat
  bereinigt.
- **Nächster Schritt** (Step 5c): CI-Workflow um E2E-Smoke
  `init` + `add` + `pull --offline` + `verify --offline` erweitern;
  `record_llm_cache.py` im `README.md` dokumentieren. Danach Step 6
  (Master-Plan-Sync + Tag `v0.2.0-phase-1b`).

## 2026-05-08 (Phase 1b Step 5a — Provider-Switch: Anthropic → AWS Bedrock + Live-Aufnahme)
- **User-Entscheidung**: firmenweit nutzen wir AWS Bedrock statt der direkten
  Anthropic-API (`toshpy`, `himi-ai` als Referenz). Phase 1b stellt komplett
  auf Bedrock um, bevor Step 5b startet.
- **Ersetzt**: `speccify_core.codegen.anthropic_client.AnthropicClient` → neuer
  `speccify_core.codegen.bedrock_client.BedrockClient` (frozen dataclass) mit
  Lazy-Import von `boto3`, Provider-Präfix-Strip (`bedrock/...`) +
  Date-Suffix-Strip, Single-Shot `bedrock-runtime.converse`,
  deterministischer Text-Block-Extraktion aus `output.message.content`. AWS-
  Credentials via Standard-Chain (`AWS_REGION` / `AWS_ACCESS_KEY_ID` /
  `AWS_SECRET_ACCESS_KEY` / `AWS_PROFILE`); `region` optional am Client.
- **Bedrock-Spezifika**:
  - `seed` nicht durchgereicht (kennt `converse` nicht).
  - `temperature` bewusst **weggelassen** — `eu.anthropic.claude-opus-4-7`
    lehnt das Feld als deprecated mit `ValidationException` ab (initialer
    Run hatte `temperature: 0.0` und 6/6 Specs schlugen fehl). Determinismus
    kommt aus dem Replay-Cache.
  - Modell-Pin in `react_llm.py` von `anthropic/claude-sonnet-4.5@2026-03-01`
    auf `bedrock/eu.anthropic.claude-opus-4-7` umgestellt (Standard-Modell
    aus `toshpy/.env`).
- **Optional-Dep**: `anthropic>=0.34` → `boto3>=1.35`; Extras umbenannt von
  `[anthropic]` auf `[bedrock]` (Sub-Paket `core/pyproject.toml` +
  Workspace-Root `pyproject.toml`).
- **Recorder umgestellt** (`scripts/record_llm_cache.py`): Live-Client jetzt
  `BedrockClient`, AWS-Credential-Check (`AWS_ACCESS_KEY_ID` oder
  `AWS_PROFILE`) statt `ANTHROPIC_API_KEY`. Eingebauter minimaler
  `_load_dotenv` (ohne `python-dotenv`-Dep): liest `.env` am Repo-Root,
  setzt Vars nur falls nicht bereits exportiert (Shell wins). `.env` aus
  `toshpy` nach Repo-Root kopiert (`.gitignore` deckte `.env` bereits ab,
  daher keine Versehensgefahr).
- **Tests**: `core/tests/test_anthropic_client.py` (7 Tests) entfernt, neu
  `core/tests/test_bedrock_client.py` mit 10 Tests (Provider/Date-Strip,
  fehlendes `boto3`, Text-Block-Extraktion via Fake-boto3,
  Region-Durchreichung, Default-Chain-Pfad, Schema-Fehler, leere
  Text-Blöcke, Exception-Wrapping).
- **Live-Aufnahme erfolgreich**: `uv sync --extra bedrock` +
  `uv run python scripts/record_llm_cache.py` → 6/6 Cache-Einträge unter
  `tests/fixtures/llm-cache/` (~36 KB total) live via Bedrock `converse`
  rekorded und eingecheckt. Erste Iteration schlug an deprecated
  `temperature` ab, zweite (ohne `temperature`) lief sauber durch.
- **Verifikation**: `uv run pytest` 131 grün (120 alt + 10 neu + 1
  Lockfile-Korrektur unverändert), `ruff check`, `ruff format`,
  `mypy core/src cli/src` alle clean.
- Plan-/AGENTS-Sync: Step 5a in `phase-1b-react-codegen.md` auf Bedrock
  umformuliert + abgehakt (inkl. Live-Aufnahme); Sub-Step 5b nun unblocked.

## 2026-05-07 (Phase 1b Step 5a-Fix — Workspace-Extra `anthropic`)
- **Bugfix für Live-Aufnahme**: `uv sync --extra anthropic` schlug am Repo-Root
  mit `Extra `anthropic` is not defined in the project's `optional-dependencies`
  table` fehl, weil das Extra nur im Sub-Paket `core/pyproject.toml` deklariert
  war, `uv sync` am Workspace-Root aber das Root-`pyproject.toml` konsultiert.
- Fix: `[project.optional-dependencies]` im Root-`pyproject.toml` ergänzt mit
  `anthropic = ["speccify-core[anthropic]"]` — spiegelt das Sub-Paket-Extra auf
  Workspace-Ebene, sodass der im Phasen-Plan/AGENTS-Anleitung dokumentierte
  Aufruf `uv sync --extra anthropic` direkt funktioniert. CI-Default
  (`uv sync` ohne Extra) bleibt unverändert.
- Verifikation: `uv sync --extra anthropic` installiert `anthropic`, `httpx`,
  `pydantic` etc. sauber; `uv run pytest` 127 grün; `ruff`/`mypy` clean.
- **Maintainer kann jetzt aufnehmen**:
  ```
  uv sync --extra anthropic
  ANTHROPIC_API_KEY=sk-... uv run python scripts/record_llm_cache.py
  ```

## 2026-05-07 (Phase 1b Step 5a — Live-`AnthropicClient` + Recorder-Skript)
- **Step 5a abgeschlossen**: neuer Live-Adapter
  `speccify_core.codegen.anthropic_client.AnthropicClient` (frozen
  dataclass) mit Lazy-Import des `anthropic` SDK, Provider-Präfix-Strip
  (`anthropic/...`) + Date-Suffix-Strip (`...@2026-03-01`), Single-Shot
  `messages.create` mit `temperature=0.0`, deterministischer
  Text-Block-Extraktion. `seed` wird bewusst nicht durchgereicht (SDK-fremd) —
  Reproduzierbarkeit kommt aus dem Replay-Cache. Klare Fehler bei leerem
  `api_key` und fehlender SDK-Installation (`AnthropicClientError`).
- `anthropic>=0.34` als **optional-Dep** `speccify-core[anthropic]` in
  `core/pyproject.toml` ergänzt — CI installiert das SDK nicht, da
  `pull --offline` ausschließlich gegen den Replay-Cache läuft.
- Neues Maintainer-Tool `scripts/record_llm_cache.py`: walkt
  `registry-fixtures/<scope>/<name>/<version>/spec.speccify.yaml`
  deterministisch, baut pro Spec einen `CacheKey` via
  `react_llm.make_cache_key`, ruft Live-`AnthropicClient`, normalisiert +
  validiert TSX (Klammer-Heuristik) und schreibt den **rohen** Response in
  den Replay-Cache. Idempotent (skip bei Cache-Hit; `--force` überschreibt).
  Fail-Fast ohne `ANTHROPIC_API_KEY`. Zielverzeichnis:
  `tests/fixtures/llm-cache/`.
- 7 neue Tests in `core/tests/test_anthropic_client.py`: Provider/Date-Strip
  (4 Varianten), `AnthropicClientError` ohne API-Key, klare
  Fehler-Message bei fehlendem SDK (Lazy-Import-Pfad), Text-Block-Extraktion
  via Fake-SDK (Filter auf `type=='text'`, mehrere Blöcke).
- Verifikation: `uv run pytest` 127 grün (120 alt + 7 neu), `ruff check`,
  `ruff format`, `mypy core/src cli/src` alle clean.
- **Offen für Maintainer**: Live-Aufnahme der 6 Phase-0-Cache-Einträge mit
  `ANTHROPIC_API_KEY` und Eincheck unter `tests/fixtures/llm-cache/`.
  Sub-Step 5b (`pull`/`verify` auf Dispatcher umstellen) hängt davon ab.
- Plan-/Status-Sync: Step 5 in `phase-1b-react-codegen.md` in 5a/5b/5c
  zerlegt, 5a ✅; `.agent/status.md` aktualisiert.

## 2026-05-07 (Phase 1b Step 4 — React-LLM-Adapter + Codegen-Dispatcher)
- **Step 4 abgeschlossen**: neuer Adapter `speccify_core.codegen.react_llm`
  mit Pin-Konstanten (`PROVIDER="anthropic"`,
  `MODEL="anthropic/claude-sonnet-4.5@2026-03-01"`, `PROMPT_VERSION="0.1.0"`,
  `DEFAULT_SEED=1`, `TARGET="react"`), `build_prompt`, `normalize_tsx`
  (Markdown-Fence-Strip + CRLF→LF + Trailing-WS + finale Newline; bewusst
  minimal nach User-Entscheidung), `validate_tsx` (Klammer-Heuristik mit
  String-/Kommentar-Awareness — fängt grobe LLM-Fehler ohne Native-Toolchain),
  `make_cache_key`, `render`/`render_to_files` (auto-`bind_key` für
  `ReplayCacheClient`), `CodegenError`, `ReactRenderResult`. Output-Pfad
  `<scope>/<PascalCase(name)>.tsx`.
- Prompt-Template `core/src/speccify_core/codegen/templates/react_llm.prompt.j2`
  (deterministisch, Single-Default-Export, TSX-only-Anweisung); Hatch
  `force-include` für die `.j2`-Datei in `core/pyproject.toml` ergänzt.
- Dispatcher `speccify_core.codegen.render_for_target` + `TargetRender(files,
  cache_key)` + `SUPPORTED_TARGETS=("react",)`. Phase-1a-Stub-Re-Exports
  (`render`, `render_to_files`) bleiben erhalten — `pull`/`verify` werden
  explizit erst in Step 5 auf den Dispatcher umgestellt.
- Re-Exports in `speccify_core.__init__` (`CodegenError`, `SUPPORTED_TARGETS`,
  `TargetRender`, `render_for_target`); `__all__` aktualisiert.
- 20 neue Tests in `core/tests/test_react_llm.py`: `normalize_tsx`
  (Trailing-WS/CRLF, finale Newline, Markdown-Fences), `validate_tsx`
  (balanced/leer/unbalanced/Klammern in Strings+Kommentaren ignoriert/
  unterminated string), `build_prompt` (Spec-Id + Props + Events sichtbar),
  `make_cache_key` (Determinismus + Pin-Felder), `render`/`render_to_files`
  (Cache-Hit, Offline-Miss → `CacheMissError`, PascalCase-Pfad, ungültiges
  TSX → `CodegenError`, Fence-Strip), Dispatcher (React-Pfad, fehlender
  Client → `CodegenError`, unbekanntes Target → `NotImplementedError`,
  `SUPPORTED_TARGETS`-Membership, byte-Identität über zwei Runs).
- Plan-Open-Questions vor Step 4 mit User geklärt und im Plan verankert:
  Anthropic Claude Sonnet 4.5 fix verdrahtet, minimale Normalisierung,
  Klammer-Heuristik in Python, Cache-Fixtures unter `tests/fixtures/llm-cache/`
  (Eincheck-Pfad in Step 5).
- Verifikation: `uv run pytest` 120 grün (100 alt + 20 neu), `ruff check`,
  `ruff format --check`, `mypy core/src cli/src` alle clean.
- Plan-/Status-Sync: Step 4 ✅ in `phase-1b-react-codegen.md`,
  `.agent/status.md` Phase + Nächste-Schritte aktualisiert.

## 2026-05-07 (Phase 1b Step 3 — Replay-Cache + `LlmClient`-Protokoll)
- **Step 3 abgeschlossen**: neues Modul `speccify_core.codegen.replay` mit
  `CacheKey` (frozen dataclass; `digest()` über kanonisches JSON mit
  `sort_keys=True` und kompakten Separators → SHA-256-Hex), `ReplayCache`
  (Disk-Layout `<root>/<digest>.json` mit `{key, response}`; atomares `put`
  via tempfile + `replace`; `get`/`has`/`put`; korruptes Entry → `CacheMissError`),
  und `CacheMissError`.
- `LlmClient`-Protokoll mit Signatur `complete(*, prompt, model, seed) -> str`
  und `ReplayCacheClient`-Wrapper: `offline=True` → Cache-Miss wirft direkt;
  `offline=False` + `inner` → Live-Call mit Cache-Einlagerung; `bind_key(...)`
  setzt Spec-Kontext explizit (kein impliziter Threading-Kanal); Key wird
  nach erfolgreichem Call konsumiert; Mismatch zwischen `bind_key.model/seed`
  und `complete.model/seed` → `CacheMissError`.
- Re-Exports in `speccify_core.codegen.__init__` und `speccify_core.__init__`
  (`CacheKey`, `CacheMissError`, `LlmClient`, `ReplayCache`,
  `ReplayCacheClient`); `__all__` aktualisiert.
- 15 neue Tests in `core/tests/test_replay_cache.py`: Digest-Stabilität +
  Feld-Sensitivität (alle 7 Varianten verschieden), Get/Put/Has/Round-Trip,
  kanonisches JSON-Layout, Overwrite, Corrupt-Entry-Reject, Offline-Miss/-Hit,
  Online-Miss-Fallback (inkl. Cache-Speicherung), Online-Hit (kein
  Inner-Call), `bind_key`-Pflicht, Key-Mismatch, Key-Konsum nach Use,
  Protocol-Strukturalität.
- Verifikation: `uv run pytest` 100 grün (85 alt + 15 neu), `ruff check`,
  `ruff format --check`, `mypy core/src cli/src` alle clean.
- Plan-/Status-Sync: Step 3 ✅ in `phase-1b-react-codegen.md`,
  `.agent/status.md` Phase + Nächste-Schritte aktualisiert.

## 2026-05-07 (Phase 1b Step 2 — Lockfile-Schema `kind: llm`)
- **Step 2 abgeschlossen**: `schema/lockfile.schema.json` `generator` jetzt
  `oneOf` mit `kind: template` (template_set + template_version) und
  `kind: llm` (provider, model, prompt_version, optional `seed` ≥ 0,
  `cache_key` als sha256-Pattern).
- `speccify_core.lockfile`: neuer `LlmGeneratorPin` (frozen dataclass);
  bestehender `GeneratorPin` bleibt als Template-Pin und wird zusätzlich als
  `TemplateGeneratorPin` aliasiert; Type-Alias `AnyGeneratorPin = GeneratorPin
  | LlmGeneratorPin`. `LockEntry.generator: AnyGeneratorPin`. Serialisierung/
  Parsing per `kind` verzweigt; `seed` wird im YAML weggelassen, wenn nicht
  gesetzt.
- Re-Exports in `speccify_core.__init__` ergänzt (`AnyGeneratorPin`,
  `LlmGeneratorPin`, `TemplateGeneratorPin`); `__all__` aktualisiert.
- 4 neue Round-Trip-Tests in `core/tests/test_lockfile.py`: LLM-Pin mit `seed`
  (inkl. Re-Read und `"seed: 42"` im YAML), LLM-Pin ohne `seed` (kein
  `seed:`-Key im Output), gemischtes Lockfile (template + llm in einem
  `specs[]`, Round-Trip-Equality), Schema-Reject bei kombinierten Template-/
  LLM-Feldern (`oneOf`-Verletzung).
- Default-Verhalten unverändert: `build_lockfile` und alle bestehenden Tests/
  Fixtures laufen weiter mit Template-Pin.
- Verifikation: `uv run pytest` 85 grün (81 alt + 4 neu), `ruff check`,
  `ruff format --check`, `mypy core/src cli/src` alle clean.
- Plan-/Status-Sync: Step 2 ✅ in `phase-1b-react-codegen.md`,
  `.agent/status.md` Nächste-Schritte aktualisiert.

## 2026-05-06 (Phase 1b Step 1 — `speccify init`)
- **Step 1 abgeschlossen**: neuer CLI-Command `speccify init <name>
  [--target react]` (`cli/src/speccify_cli/commands/init.py`).
- Output ist bewusst minimal (User-Entscheidung): `speccify.yaml` mit
  `schema_version: 1`, `target` (Default `react`), `dependencies: {}`.
  Kein `registry`-Block, kein `package.json`/Skeleton.
- Verhalten: Verzeichnis wird angelegt, falls nicht existent; existierendes
  leeres Verzeichnis wird befüllt; nicht-leeres Verzeichnis oder ungültiger
  Name (Slash/Backslash) → Exit 1 mit Fehlermeldung, kein Manifest geschrieben.
- 7 neue CLI-Tests (`cli/tests/test_init.py`): Happy-Path, Default-Target,
  Custom-Target, Round-Trip via `ProjectManifest.load`, leeres existierendes
  Verzeichnis, nicht-leeres Verzeichnis (Exit 1), ungültiger Name.
- Verifikation: `uv run pytest` 81 grün (74 alt + 7 neu), `ruff check`,
  `ruff format --check`, `mypy core/src cli/src` alle clean.
- Plan-/Status-Sync: Step 1 ✅ in `phase-1b-react-codegen.md`,
  `.agent/status.md` Nächste-Schritte aktualisiert.

## 2026-05-06 (Phase 1b geplant)
- **Phasen-Plan `phase-1b-react-codegen.md` geschrieben** — reines Plan-Dokument
  als nächster atomarer Commit, bevor Code für Phase 1b angefasst wird
  (Plan-Disziplin Regel #1, `AGENTS.md`).
- Kern-Entscheidungen mit User abgestimmt:
  - **LLM-Codegen** (Variante B aus Master-Plan) statt Templates für React —
    direkt der Zielzustand. CI nutzt einen eingecheckten Replay-Cache statt
    Live-API-Calls (`--offline` Flag), Cache-Key über
    `(spec_sha256, target, model, prompt_version, seed)`.
  - **`speccify init` minimal**: nur `speccify.yaml` mit `target` + leerer
    `dependencies`, kein `package.json`/Skeleton-Projekt.
  - **TSX-Output minimal**: ein File pro Spec mit Props/Types aus Inputs/Events
    + Komponenten-Skeleton mit `// TODO`-Markern. Keine Tests/Stories.
- Plan zerlegt in 6 atomare Steps: (1) `init`, (2) Lockfile-Schema-Erweiterung
  (`generator.oneOf` für `template`/`llm`), (3) Replay-Cache + `LlmClient`-
  Protokoll, (4) React-LLM-Adapter + Codegen-Dispatcher, (5)
  `pull --target react --offline` + CI + Fixtures, (6) Master-Plan-Sync + Tag
  `v0.2.0-phase-1b`.
- Offene Fragen vor Step 4 im Plan dokumentiert: Provider-Default,
  Normalisierungs-Tiefe, TSX-Validitäts-Check, Cache-Fixture-Ort.
- `AGENTS.md` „Aktuelle Phase" und `.agent/status.md` auf „Phase 1b geplant,
  Step 1 als Nächstes" umgestellt.

## 2026-05-06 (Phase 1a abgeschlossen)
- **Phase 1a Step 4 + Step 5 abgeschlossen** — Stub-Codegen, `speccify pull`,
  `speccify verify`, `lint`-Anpassung, CI-Step und Master-Plan-Sync. Damit ist
  der vollständige Resolver/Lockfile/Codegen/Verify-Kreis für Phase 1a zu.
  - Neues Codegen-Modul `speccify_core.codegen` (Re-Exports) + `codegen/stub.py`
    mit Konstanten `TEMPLATE_SET="phase-1a-stub"` / `TEMPLATE_VERSION="0.1.0"`,
    `render(spec, target)` und `render_to_files(spec, target)`. Output-Pfad
    folgt `<scope>/<name>.md`.
  - Jinja2-Template `core/src/speccify_core/codegen/templates/stub.md.j2` mit
    YAML-Frontmatter (`target`, `spec_id`, `spec_version`, `template_set`,
    `template_version`), Markdown-Tabellen für Inputs/Outputs/Events/Acceptance
    und einer `Uses`-Liste. Determinismus: `keep_trailing_newline=True`,
    keine Datums-/Zufallswerte.
  - `jinja2>=3.1` als Runtime-Dependency in `core/pyproject.toml`; Hatch
    `force-include` für die `.j2`-Datei (sonst landet sie nicht im Wheel).
  - Lockfile-Defaults (`DEFAULT_TEMPLATE_SET`/`DEFAULT_TEMPLATE_VERSION`)
    werden jetzt aus `speccify_core.codegen.stub` re-exportiert (single source
    of truth, wie im Plan vorgesehen).
  - Neuer CLI-Command `speccify pull` (`commands/pull.py`): liest Lockfile,
    fordert Specs aus der `LocalRegistry`, ruft Stub-Codegen, schreibt Dateien
    atomar (`tempfile` + `os.replace`), aktualisiert
    `generated_files_sha256` pro Eintrag via `Lockfile.with_generated_files`.
    Klare Fehler bei fehlendem Lockfile oder Target-Mismatch zum Lockfile.
  - Neuer CLI-Command `speccify verify` (`commands/verify.py`): re-resolved das
    Manifest, vergleicht (id, version, sha256, target) mit dem Lockfile,
    re-rendert jede Spec und vergleicht Output-Hashes, prüft schließlich auch
    die tatsächlichen Dateien auf Disk gegen die Lockfile-Hashes
    (Drift-Detection). Sammelt alle Probleme und beendet bei Drift mit Exit 1.
  - `speccify lint` angepasst: Specs ohne Top-Level `kind`-Feld (Projekt-
    Manifeste wie `speccify.yaml`) werden mit Hinweis übersprungen statt
    fälschlich gegen `spec.schema.json` validiert. Manifest-Schema-Validierung
    läuft weiter beim Manifest-Load in `lock`/`add`.
  - 12 neue Tests:
    - `core/tests/test_codegen_stub.py` — Determinismus, Output-Pfad-Konvention,
      Frontmatter, `Uses`-Block für Workflow-Specs.
    - `cli/tests/test_pull.py` — E2E (lock + pull, Hash im Lockfile passt zur
      Disk-Datei), Determinismus über zwei `pull`-Aufrufe, fehlendes Lockfile,
      Target-Mismatch zum Lockfile.
    - `cli/tests/test_verify.py` — Happy-Path, manueller Disk-Drift → Exit 1
      mit „Disk-Drift", fehlendes Lockfile, fehlender `pull` (leere
      `generated_files_sha256`).
  - End-to-End im `example-project/` lokal grün:
    `uv run speccify lock` → 3 Specs (button, login-screen via Diamond,
    onboarding-wizard), `uv run speccify pull --out ./out` → 3 Markdown-Dateien,
    `uv run speccify verify --out ./out` → konsistent.
  - CI-Workflow `.github/workflows/ci.yml` um E2E-Smoke ergänzt
    (`cd example-project && lock && pull && verify`).
  - `.gitignore` ergänzt um `example-project/out/` und
    `example-project/speccify.lock` (werden in CI bei jedem Lauf neu gebaut).
  - Master-Plan `.agent/plans/speccify-plan.md` synchronisiert:
    - Lockfile-Beispiel hat jetzt zwei Varianten: `kind: template` (Phase 1a,
      ohne API-Keys reproduzierbar) und `kind: llm` (Phase 1b+).
    - Phase 1 explizit in Sub-Spikes 1a / 1b / 1c / 1d zerlegt; 1a verlinkt
      auf den abgeschlossenen Phasen-Plan.
    - Erstes Codegen-Target ist React (statt SwiftUI), Begründung dokumentiert;
      Phase 3 zieht SwiftUI/Angular nach.
  - Verifikation lokal grün: `uv run pytest` (74 Tests, +12 neu seit Step 3),
    `uv run ruff check`, `uv run ruff format --check`,
    `uv run mypy core/src cli/src`, `uv run speccify lint specs/*.speccify.yaml`,
    sowie der CI-E2E-Pfad im `example-project/`.
  - Phase-1a-Plan: Steps 4 und 5 sind als ✅ markiert; `status.md` und
    `AGENTS.md` auf „Phase 1a abgeschlossen → Phase 1b" umgestellt.

## 2026-05-06 (noch später²)
- **Phase 1a Step 3 abgeschlossen** — Lockfile-Format + `speccify lock`/`add`:
  - Neues JSON-Schema `schema/lockfile.schema.json` (Draft 2020-12) mit
    `schema_version=1`, `target`, `specs[]` (id, version, sha256, resolved_via,
    target, generator{kind=template, template_set, template_version},
    generated_files_sha256[]).
  - Neues Modul `speccify_core.lockfile` mit `Lockfile`/`LockEntry`/`GeneratorPin`/
    `GeneratedFile`, `LockfileError`, `Lockfile.load`/`write` (deterministischer
    YAML-Dump mit fixer Key-Reihenfolge, alphabetisch nach `id`),
    `Lockfile.with_generated_files` (für Step 4) und Top-Level-Helper
    `build_lockfile(target, resolutions)`.
  - Defaults-Konstanten `DEFAULT_TEMPLATE_SET="phase-1a-stub"` und
    `DEFAULT_TEMPLATE_VERSION="0.1.0"` zentralisiert (Step 4 importiert sie aus
    `speccify_core.codegen.stub`, bis dahin liegen sie hier).
  - Re-Exports in `speccify_core.__init__` ergänzt.
  - CLI-Subcommand-Layer neu: `cli/src/speccify_cli/commands/__init__.py`,
    `_workspace.py` (gemeinsamer `WorkspaceContext` mit Manifest+Registry-Lookup,
    `--registry`-Override), `lock.py` (`speccify lock`) und `add.py`
    (`speccify add @scope/name[@<range>]`, Default-Range `^<major.minor>` aus
    latest-Registry-Version, ruft implizit `lock`).
  - 16 neue Tests:
    - `core/tests/test_lockfile.py` — Round-Trip, alphabetische Sortierung beim
      Schreiben, Schema-Violation, `with_generated_files`-Verhalten,
      `build_lockfile` aus echtem Resolver-Graph.
    - `cli/tests/test_lock.py` — Smoke gegen Fixtures, Determinismus zweier
      Aufrufe, unbekannte Dependency, fehlendes Manifest, `--registry`-Override.
    - `cli/tests/test_add.py` — Default-Range, expliziter Caret, exakte Version,
      unbekannte Spec, ungültige Spec-Referenz.
  - Verifikation lokal grün: `uv run pytest` (62 Tests, +16 neu),
    `uv run ruff check`/`format --check`, `uv run mypy core/src cli/src`.
  - Plan-Status: Phase 1a Step 4 (Stub-Codegen + `speccify pull`) ist als
    Nächstes dran.

## 2026-05-06 (noch später)
- **Phase 1a Step 2 abgeschlossen** — MVS-Resolver:
  - Neues Modul `speccify_core.resolver` mit `Range` (Caret `^X.Y`/`^X.Y.Z` + exakt
    `X.Y.Z`), `Resolution`, `ResolvedGraph`, `Resolver` und `ResolverError`-Hierarchie
    (`VersionNotFoundError`, `RangeConflictError`).
  - MVS-Algorithmus strikt nach Go-Vorbild: Maximum aller geforderten
    Mindestversionen, danach kleinste verfügbare Version, die alle Ranges
    erfüllt. Transitive Auflösung über `uses:` via Worklist.
  - Spec-Hashing: `sha256` der Original-Bytes der Spec-Datei (nicht re-serialisiert)
    → `Resolution.spec_sha256`. Resolutions deterministisch alphabetisch sortiert.
  - Re-Exports in `speccify_core.__init__` ergänzt.
  - 12 neue Tests in `core/tests/test_resolver.py`: Range-Parser (Caret/Exact/Invalid),
    Happy-Path, transitive `uses:`-Auflösung, Diamond mit `button@0.1.1` als
    Resultat (`onboarding-wizard.uses: ^0.1` + `login-screen.uses: ^0.1.1`),
    sortierte Resolutions, fehlende Version, unbekannte Spec, inkompatible Ranges,
    ungültige Range im Manifest.
  - Verifikation lokal grün: `uv run pytest` (46 Tests, +12 neu),
    `uv run ruff check`/`format --check`, `uv run mypy core/src cli/src`.
  - Plan-Status: Phase 1a Step 3 (Lockfile + `speccify add`/`lock`) ist als
    Nächstes dran.

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
