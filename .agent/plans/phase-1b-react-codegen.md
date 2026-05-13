---
sessionId: session-260506-160000-1b
isActive: true
---

# Requirements

### Overview & Goals

Phase 1a ist abgeschlossen (Resolver + Lockfile + Stub-Codegen + `add`/`lock`/`pull`/`verify`, 74 Tests grün, End-to-End im `example-project/` reproduzierbar). Der Resolver-/Lockfile-Vertrag ist stabil: Lockfile pinnt Spec-Bundles per SHA-256 und Generator per `kind`, plus Output-Hashes pro generierter Datei.

**Ziel von Phase 1b:** Echtes React-Codegen statt Stub-Markdown, plus `speccify init`. Ein frisch initialisiertes Projekt kann via
```
speccify init my-app --target react
cd my-app
speccify add @org/button
speccify pull --target react --out ./src/generated
speccify verify
```
durchlaufen und erhält pro Spec eine **TSX-Komponente** mit minimalen Props/Types, die aus den Spec-Inputs/Events deterministisch abgeleitet sind. Codegen ist **LLM-basiert** (Variante B aus dem Master-Plan, [`speccify-plan.md`](./speccify-plan.md) Z. 227–240): Modell-Pin, Prompt-Version und Seed werden im Lockfile verankert; CI nutzt einen Replay-Cache statt Live-API.

Single Source of Truth für Phase-1b-Änderungen ist dieses Dokument.

### Scope

**In Scope**
- `speccify init <name> [--target react]`: legt minimales `speccify.yaml` mit `target` + leerer `dependencies`-Map an. Kein Skeleton-Projekt, kein `package.json`, keine `src/`-Struktur.
- LLM-Codegen-Adapter `speccify_core.codegen.react_llm` mit:
  - Prompt-Template (versioniert: `prompt_version`),
  - Modell-Pin (`kind: llm`, `model: <provider/name@date>`),
  - deterministischem `seed`,
  - Replay-Cache (Disk-basiert, keyed über `(spec_sha256, target, model, prompt_version, seed)`).
- Lockfile-Erweiterung: `generator.kind` darf `template` *oder* `llm` sein; Schema-Update + Round-Trip-Tests. Pro Spec ein Eintrag mit eigenem Generator-Pin.
- Codegen-Output: **eine TSX-Datei pro Spec**, Pfad `<scope>/<PascalName>.tsx`. Inhalt:
  - `import` für externe `uses`-Specs (Pfad-Resolution analog zum Output-Layout),
  - Props-Type aus `inputs`,
  - Event-Callback-Types aus `events`,
  - Funktionskomponenten-Skeleton mit `// TODO`-Markern für Body — kein Storybook, keine Tests, kein Styling-System.
- CLI-Anpassungen: `speccify pull --target react` ruft den LLM-Adapter; Default-Target bleibt aus Manifest. `--offline` Flag, das nur den Replay-Cache nutzt und bei Cache-Miss fehlschlägt (für CI).
- Tests: Replay-basierte Snapshot-Tests pro Phase-0-Spec (5 + Diamond → 6 Outputs), Determinismus-Tests (zwei `pull`-Aufrufe mit gleichem Cache → byte-identisch), Lockfile-Schema-Tests für `kind: llm`, `init`-Smoke-Tests.
- Master-Plan-Sync + Tag-Vorschlag `v0.2.0-phase-1b`.

**Out of Scope**
- Storybook-Stories oder Vitest/RTL-Tests pro Spec (User-Entscheidung: nur TSX + Props/Types).
- Voll-Skeleton-Projekt bei `init` (kein `package.json`, keine `tsconfig.json`).
- SwiftUI/Angular (Phase 3).
- MCP-Server (Phase 1c).
- Browser-Playground (Phase 1d).
- Live-LLM-Calls in CI — CI läuft ausschließlich gegen den eingecheckten Replay-Cache.
- Streaming/Multi-Turn-Prompts.
- `speccify publish`/`yank`/`search` (Phase 2).

### User Stories
- *Als Entwickler* will ich `speccify init my-app --target react` aufrufen, damit ich sofort ein gültiges Manifest habe, ohne YAML-Boilerplate von Hand zu schreiben.
- *Als Spec-Konsument* will ich `speccify pull --target react` aufrufen und für jede Spec eine TSX-Komponente mit getypten Props/Events erhalten, die ich in mein React-Projekt einfügen kann.
- *Als CI-Pipeline* will ich `speccify verify --offline` ausführen und sicher sein, dass weder Specs noch generierte TSX-Dateien gedriftet sind — ohne API-Key.
- *Als Phase-1c-Implementierer* will ich, dass der LLM-Codegen-Adapter dieselbe `render(spec, target) -> bytes`-Signatur wie der Stub-Codegen hat, damit MCP ihn ohne Sonderpfad einbinden kann.

### Functional Requirements
- `speccify init <name> [--target <t>]`: erzeugt `<name>/speccify.yaml` mit `schema_version: 1`, `target: <t|react>`, `dependencies: {}`. Fehler, wenn Verzeichnis existiert *und* nicht leer ist. Gibt nichts anderes aus.
- `speccify pull --target react`: für jede Lockfile-Entry mit `target == react` ruft den LLM-Adapter, schreibt TSX atomar (`tempfile` + `os.replace`), aktualisiert `generated_files_sha256`. Bei Cache-Miss + ohne `--offline`: Live-API-Call (Provider via Env-Var `ANTHROPIC_API_KEY` o.ä.); bei Cache-Hit: keine API. Mit `--offline`: Cache-Miss → Exit 1.
- Lockfile `generator` für LLM-Specs:
  ```yaml
  generator:
    kind: llm
    model: "anthropic/claude-sonnet-4.5@2026-03-01"
    prompt_version: 1
    seed: 1
  ```
  Schema validiert beide Varianten (`template` und `llm`) per `oneOf`.
- Replay-Cache-Layout: `~/.cache/speccify/llm-replay/<sha256-of-key>.json` mit `{key, request, response, created_at}`. Kann via `SPECCIFY_CACHE_DIR` überschrieben werden. Repo-lokaler Cache für CI: `.speccify-cache/` (gitignored *außer* `.speccify-cache/fixtures/`, der eingecheckt ist).
- TSX-Output muss bei identischem `(spec_sha256, target, model, prompt_version, seed)` byte-identisch sein (post-formatiert via `prettier`-kompatibler Normalisierung im Adapter — kein externer Tool-Call, sondern deterministische Eigen-Normalisierung: feste Quote-Style, feste Indent-Width, trailing newline).
- Klare Fehler: fehlender API-Key bei Cache-Miss ohne `--offline`, ungültiges TSX vom LLM (Syntax-Check via leichtgewichtigem Parser, z.B. `tree-sitter-typescript` oder String-basiert minimal), Modell-Mismatch zum Lockfile bei `verify`.

### Non-Functional Requirements
- **Determinismus**: Replay-Cache ist die Wahrheit; jede Änderung an Prompt/Model erzwingt `prompt_version`-Bump, was Cache-Key invalidiert.
- **Offline-CI**: `uv run pytest` und der `example-project/`-E2E-Step laufen ohne Netzwerk dank eingechecktem Cache.
- **Cache-Größe**: Eingecheckter Cache nur für die 6 Phase-0-Spec-Outputs; Größenbudget < 500 KB total (Markdown-/JSON-komprimiert).
- **Reproduzierbarkeit über Modell-EOL hinweg**: Wenn ein Modell EOL geht, bleibt der Cache-Hit gültig; nur Cache-Miss + Live-Call schlägt fehl — wird im Plan als bekannte Einschränkung dokumentiert.
- **Performance**: Cache-Hit-Pull < 100 ms pro Spec; Cache-Miss + Live-Call < 30 s pro Spec (Anthropic-Latenz-Annahme).


# Technical Design

### Current Implementation (nach Phase 1a)
- `speccify_core.codegen` mit `stub.py` (`render`, `render_to_files`, `TEMPLATE_SET`, `TEMPLATE_VERSION`) — bleibt unverändert; React-Adapter wird Geschwister-Modul.
- `speccify_core.lockfile` mit `GeneratorPin(kind, template_set, template_version)` — wird zu Union-Type erweitert (`TemplateGeneratorPin | LlmGeneratorPin`); Default in `build_lockfile` bleibt Template, wird in `pull` durch konkreten Pin überschrieben.
- `schema/lockfile.schema.json` — `generator` wird zu `oneOf` zwischen Template- und LLM-Variante.
- `speccify_cli.commands.pull` — ruft heute `speccify_core.codegen.stub.render_to_files`; in 1b wird stattdessen ein Codegen-Dispatcher pro `target` aufgerufen.
- `speccify_cli.commands.lock`/`add` — unverändert.

### Key Decisions
1. **LLM-Codegen statt Templates für React.** Bewusste Master-Plan-konforme Wahl (User-Entscheidung): direkt Zielzustand aus dem Master-Plan (Variante B). Begründung: Templates für TSX würden den LLM-Layer nur verzögern und müssten in Phase 1c/1d ohnehin durch LLM ersetzt werden.
2. **Replay-Cache + `--offline` als CI-Strategie.** Kein Live-API-Call in CI. Cache-Fixtures sind eingecheckt unter `tests/fixtures/llm-cache/`. Cache-Key enthält *Spec-Bytes-Hash*, nicht Spec-ID — d.h. Spec-Änderung invalidiert Cache automatisch.
3. **TSX-Output minimal.** Nur Props/Types und Komponentenrumpf mit `// TODO`-Markern (User-Entscheidung). Kein Styling, kein State, kein Test/Story. Phase 1c/1d können auf Wunsch nachziehen.
4. **`speccify init` minimal.** Keine `package.json`/Skeleton-Generation (User-Entscheidung) — nur `speccify.yaml`. Hält Phase 1b klein und fokussiert auf den Codegen-Vertrag.
5. **Codegen-Dispatcher in `speccify_core.codegen`.** Neue Funktion `render_for_target(spec, target, generator_pin) -> list[GeneratedFile]`, die intern auf `stub` oder `react_llm` route. `pull` weiß nichts mehr von konkreten Adaptern.
6. **Provider-Abstraktion.** `LlmClient`-Protokoll mit `complete(prompt: str, model: str, seed: int) -> str`. Default-Implementation `AnthropicClient`; in Tests `ReplayCacheClient` (greift nur auf den eingecheckten Cache zu, niemals aufs Netz).
7. **Hash-Stabilität bei LLM-Outputs.** Nach LLM-Response wird das TSX durch eine deterministische Normalisierungs-Pipeline (Whitespace-Normalisierung, feste Quote-Style, sortierte Imports) gejagt, *bevor* der Hash berechnet wird. So sind kleinere LLM-Variationen pro Seed dennoch stabil reproduzierbar — falls sie vom selben Cache-Eintrag kommen.

### Proposed Changes

#### 1. `speccify init`
Neues CLI-Modul `speccify_cli.commands.init`:
```python
def init(name: str, target: str = "react") -> None:
    target_dir = Path.cwd() / name
    if target_dir.exists() and any(target_dir.iterdir()):
        raise InitError(f"{target_dir} exists and is not empty")
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest = ProjectManifest(target=target, dependencies={}, registry_path=Path("./registry"))
    manifest.write(target_dir / "speccify.yaml")
```

#### 2. LLM-Codegen-Adapter
Neues Modul `speccify_core.codegen.react_llm`:
```python
PROMPT_VERSION = 1
DEFAULT_MODEL = "anthropic/claude-sonnet-4.5@2026-03-01"
DEFAULT_SEED = 1

class LlmClient(Protocol):
    def complete(self, *, prompt: str, model: str, seed: int) -> str: ...

def render(spec: Spec, *, client: LlmClient, model: str, prompt_version: int, seed: int) -> bytes: ...
def render_to_files(spec: Spec, *, client: LlmClient, ...) -> list[GeneratedFile]: ...
```
Prompt-Template als `core/src/speccify_core/codegen/templates/react_llm.prompt.j2` — Eingabe ist die geladene Spec, Ausgabe ist die instanziierte Prompt-Zeichenkette.

#### 3. Replay-Cache
Neues Modul `speccify_core.codegen.replay`:
```python
class ReplayCache:
    def __init__(self, root: Path): ...
    def get(self, key: CacheKey) -> str | None: ...
    def put(self, key: CacheKey, response: str) -> None: ...

@dataclass(frozen=True)
class CacheKey:
    spec_sha256: str
    target: str
    model: str
    prompt_version: int
    seed: int
    def digest(self) -> str: ...  # sha256 über kanonisches JSON
```
`ReplayCacheClient` wrappt einen Real-Client und cached. Cache-Miss + offline → `CacheMissError`.

#### 4. Lockfile-Schema-Update
`schema/lockfile.schema.json`:
```json
"generator": {
  "oneOf": [
    {"$ref": "#/$defs/template_generator"},
    {"$ref": "#/$defs/llm_generator"}
  ]
}
```
`speccify_core.lockfile`: `GeneratorPin` wird Union; YAML-Dump-Logik dispatched über `kind`.

#### 5. Codegen-Dispatcher
`speccify_core.codegen.__init__`:
```python
def render_for_target(spec: Spec, target: str, *, llm_client: LlmClient | None = None) -> list[GeneratedFile]: ...
```
`pull` ruft nur noch `render_for_target` und persistiert den vom Adapter zurückgegebenen `GeneratorPin` ins Lockfile.

#### 6. CI + Fixtures
- `tests/fixtures/llm-cache/` mit eingecheckten Replay-Einträgen für Phase-0-Specs.
- CI ruft `speccify pull --offline` (neues Flag) und `verify --offline`.
- Live-Aufnahme-Skript `scripts/record_llm_cache.py` (manuell, mit API-Key) für Maintainer.

### File Layout (Delta zu Phase 1a)
```
core/src/speccify_core/codegen/
  __init__.py                 # render_for_target Dispatcher
  stub.py                     # unverändert
  react_llm.py                # NEU
  replay.py                   # NEU
  templates/
    stub.md.j2                # unverändert
    react_llm.prompt.j2       # NEU
core/src/speccify_core/lockfile.py    # GeneratorPin → Union
schema/lockfile.schema.json           # generator.oneOf
cli/src/speccify_cli/commands/
  init.py                     # NEU
  pull.py                     # nutzt Dispatcher + LlmClient
tests/fixtures/llm-cache/             # NEU, eingecheckt
scripts/record_llm_cache.py           # NEU, manueller Run
```

### Risks
- **LLM-Output-Stabilität.** Auch mit Seed kann das Modell minimale Variationen liefern. Mitigation: Normalisierungs-Pipeline + Cache-First-Strategie. Wenn Normalisierung nicht reicht, Fallback auf "Cache ist die Wahrheit, Re-Record nur bei Spec-Änderung".
- **Modell-EOL.** Anthropic kann Modelle abkündigen. Mitigation: Cache reicht für Reproduktion; `record_llm_cache.py` muss bei EOL auf Nachfolge-Modell umgestellt werden, was `prompt_version`-Bump *und* Cache-Re-Record erfordert.
- **TSX-Validität.** LLM kann ungültiges TSX liefern. Mitigation: leichtgewichtiger Syntax-Check (Klammer-/Tag-Balancing reicht für Phase 1b; volle TS-Compilation wäre Phase-1d-Sache). Bei Fehlschlag: Exit 1 mit Spec-ID + Snippet.
- **Provider-Lock-in.** Anthropic ist Default. Mitigation: `LlmClient`-Protokoll erlaubt OpenAI/lokale Modelle; nicht in 1b implementiert, aber Vertrag offen.
- **Cache-Drift in PRs.** Wenn ein PR eine Spec ändert, muss der Cache neu aufgenommen werden. Mitigation: `verify --offline` schlägt mit klarer Anweisung fehl ("run `scripts/record_llm_cache.py`").

### Testing Strategy
- **Unit**: `ReplayCache` (get/put/digest), Prompt-Rendering aus Jinja, `GeneratorPin`-Union-Round-Trip, Normalisierungs-Pipeline (idempotent).
- **Integration**: `render_for_target` mit `ReplayCacheClient` für jede Phase-0-Spec, byte-identischer Output über zwei Runs.
- **CLI-Smoke**: `init` (Verzeichnis-Anlage, Idempotenz-Fehlerfall), `pull --offline` (Happy + Cache-Miss → Fehler), `verify --offline` (Drift-Detection für TSX).
- **Schema**: Lockfile mit `kind: llm` round-trip + Schema-Validation.
- **E2E**: `example-project/` durchläuft `init` (in tmp), `add @org/button`, `pull --target react --offline`, `verify --offline` — alle 3 Specs als TSX vorhanden.

### Acceptance Criteria
1. `speccify init my-app --target react` erzeugt `my-app/speccify.yaml` mit korrektem Schema; Re-Run auf nicht-leerem Verzeichnis schlägt mit klarer Meldung fehl.
2. `speccify pull --target react --offline` erzeugt für jede Phase-0-Spec eine TSX-Datei mit Props/Types aus Inputs/Events; zwei aufeinanderfolgende Runs sind byte-identisch.
3. Lockfile enthält pro Eintrag einen `kind: llm`-Generator-Pin mit `model`/`prompt_version`/`seed` und `generated_files_sha256` für die TSX-Datei.
4. `speccify verify --offline` erkennt Disk-Drift (manuelle TSX-Änderung) und Lockfile-Drift (Modell/Seed-Änderung).
5. CI (kein API-Key) läuft komplett grün: Lint, Format, Mypy, Pytest, E2E im `example-project/`.
6. `uv run pytest` ≥ 90 Tests (74 aus 1a + ≥ 16 neu); `ruff`, `mypy` clean.

# Delivery Plan

> Atomare Schritte nach `rules.md` ("Ein Prompt = ein Commit"). Jeder Step liefert grüne Tests + sauberen Lint.

### Step 1 — `speccify init` + Manifest-Default ✅
- [x] CLI-Command `speccify init <name> [--target react]` (`cli/src/speccify_cli/commands/init.py`, `run_init` + `init_command`).
- [x] Minimaler Output: `speccify.yaml` mit `schema_version: 1`, `target` (Default `react`), `dependencies: {}`. Kein `registry`-Block, kein Skeleton.
- [x] Fehler bei nicht-leerem Zielverzeichnis und ungültigem Namen (`/`/`\`); leeres existierendes Verzeichnis wird befüllt.
- [x] Tests `cli/tests/test_init.py` (7 neue Tests): Happy-Path, Default-Target, Custom-Target, Manifest-Loadbarkeit via `ProjectManifest.load`, leeres existierendes Verzeichnis, nicht-leeres Verzeichnis (Exit 1, kein Manifest geschrieben), ungültiger Name.
- [x] Status/Log/Plan-Sync.

### Step 2 — Lockfile-Schema-Erweiterung (`kind: llm`) ✅
- [x] `schema/lockfile.schema.json` `generator.oneOf` mit Varianten `kind: template` (template_set + template_version) und `kind: llm` (provider, model, prompt_version, optional `seed`, `cache_key`).
- [x] `speccify_core.lockfile`: neuer `LlmGeneratorPin` (frozen dataclass), `TemplateGeneratorPin` als Alias auf bestehenden `GeneratorPin` (Rückwärtskompatibilität), Type-Alias `AnyGeneratorPin = GeneratorPin | LlmGeneratorPin`. `LockEntry.generator: AnyGeneratorPin`. Serialisierung/Parsing per `kind` verzweigt (`_generator_to_dict` / `_generator_from_dict`); `seed` bleibt im YAML weg, wenn nicht gesetzt.
- [x] Re-Exports in `speccify_core.__init__` (`AnyGeneratorPin`, `LlmGeneratorPin`, `TemplateGeneratorPin`).
- [x] 4 neue Round-Trip-Tests in `core/tests/test_lockfile.py`: LLM mit `seed`, LLM ohne `seed`, gemischtes Lockfile (template + llm in einem `specs[]`), Schema-Reject bei kombinierten Template-/LLM-Feldern (`oneOf`-Verletzung). Default-Verhalten (`build_lockfile` → Template-Pin) unverändert; bestehende Tests bleiben grün.
- [x] Status/Log/Plan-Sync.

### Step 3 — Replay-Cache + `LlmClient`-Protokoll ✅
- [x] `speccify_core.codegen.replay` mit `CacheKey` (frozen dataclass, kanonischer JSON-`digest()` über `sort_keys`+kompakte Separators), `ReplayCache` (Disk-Layout `<root>/<digest>.json` mit `{key, response}`, atomares `put` via tempfile + `replace`, `get`/`has`/`put`), `CacheMissError`.
- [x] `LlmClient`-Protokoll (`complete(*, prompt, model, seed) -> str`) und `ReplayCacheClient`-Wrapper mit `offline`-Flag, optionalem `inner`-Live-Client und `bind_key(...)`-Vertrag (Aufrufer setzt Spec-Kontext explizit; Key wird nach Erfolg konsumiert).
- [x] Re-Exports in `speccify_core.codegen.__init__` und `speccify_core.__init__` (`CacheKey`, `CacheMissError`, `LlmClient`, `ReplayCache`, `ReplayCacheClient`).
- [x] 15 neue Tests in `core/tests/test_replay_cache.py`: `CacheKey`-Digest-Stabilität + Feld-Sensitivität, `ReplayCache` Get/Put/Has/Round-Trip/kanonisches JSON/Overwrite/Corrupt-Entry, `ReplayCacheClient` Offline-Miss/Offline-Hit/Online-Miss-Fallback (+Cache-Eintrag)/Online-Hit (kein Inner-Call)/`bind_key`-Pflicht/Key-Mismatch/Key-Konsum nach Use, Protocol-Strukturalität.
- [x] Status/Log/Plan-Sync.

### Step 4 — React-LLM-Adapter + Codegen-Dispatcher ✅
- [x] `speccify_core.codegen.react_llm` mit Pin-Konstanten (`PROVIDER="anthropic"`, `MODEL="anthropic/claude-sonnet-4.5@2026-03-01"`, `PROMPT_VERSION="0.1.0"`, `DEFAULT_SEED=1`, `TARGET="react"`), `build_prompt`, `normalize_tsx` (Markdown-Fence-Strip + CRLF→LF + Trailing-WS + finale Newline), `validate_tsx` (Klammer-Heuristik mit String-/Kommentar-Awareness), `make_cache_key`, `render`/`render_to_files` (auto-`bind_key` für `ReplayCacheClient`), `CodegenError`, `ReactRenderResult`. Output-Pfad `<scope>/<PascalCase(name)>.tsx`.
- [x] Prompt-Template `core/src/speccify_core/codegen/templates/react_llm.prompt.j2` (deterministisch, Single-Default-Export, TSX-only-Anweisung, kein Markdown). Hatch `force-include` für die `.j2`-Datei in `core/pyproject.toml`.
- [x] `speccify_core.codegen.render_for_target`-Dispatcher + `TargetRender(files, cache_key)` + `SUPPORTED_TARGETS=("react",)`. `pull`/`verify` bleiben in Step 4 noch beim Stub-Codegen — Umstellung auf den Dispatcher ist explizit Teil von Step 5.
- [x] Re-Exports in `speccify_core.__init__` (`CodegenError`, `SUPPORTED_TARGETS`, `TargetRender`, `render_for_target`).
- [x] 20 neue Tests in `core/tests/test_react_llm.py`: `normalize_tsx` (CRLF/Trailing-WS/finale Newline/Markdown-Fences), `validate_tsx` (balanced/leer/unbalanced/String+Kommentar-Klammern ignorieren/unterminated string), `build_prompt` (Spec-Id + Props + Events sichtbar), `make_cache_key` (deterministisch + Pin-Felder), `render`/`render_to_files` (Cache-Hit, Offline-Miss → `CacheMissError`, PascalCase-Pfad, ungültiges TSX → `CodegenError`, Fence-Strip), Dispatcher (React-Pfad, fehlender Client, unbekanntes Target, byte-Identität über zwei Runs).
- [x] Plan-Open-Questions vor Step 4 mit User geklärt: Anthropic Claude Sonnet 4.5 fix, minimale Normalisierung, Klammer-Heuristik in Python, Cache-Fixtures unter `tests/fixtures/llm-cache/` (Eincheck-Pfad ist Step-5-Aufgabe).
- [x] Status/Log/Plan-Sync.

### Step 5 — `speccify pull --target react --offline` + CI

#### Sub-Step 5a — Live-`BedrockClient` + Recorder ✅
- [x] **Provider-Switch von Anthropic auf AWS Bedrock** (User-Entscheidung): firmenweit steht Bedrock zur Verfügung, kein direkter Anthropic-API-Pfad mehr. Modell-Pin auf `bedrock/eu.anthropic.claude-opus-4-7` (`eu-central-1`).
- [x] `speccify_core.codegen.bedrock_client.BedrockClient` (frozen dataclass) mit Lazy-Import von `boto3`, Provider-Präfix-/Date-Suffix-Stripping, Single-Shot `bedrock-runtime.converse`, Text-Block-Extraktion. `seed` und `temperature` werden bewusst nicht durchgereicht (Bedrock-`converse` kennt `seed` nicht; `temperature` ist für Claude-Opus-4-7 deprecated). Reproduzierbarkeit kommt aus dem Replay-Cache. AWS-Credentials per Standard-Chain (`AWS_REGION`/`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_PROFILE`).
- [x] `boto3>=1.35` als optional-Dep `speccify-core[bedrock]` + Workspace-Mirror (`speccify[bedrock]`); CI installiert das Extra nicht.
- [x] `scripts/record_llm_cache.py` als Maintainer-Tool: Walk über `registry-fixtures/<scope>/<name>/<version>/`, idempotent (skip bei Cache-Hit, `--force` zum Überschreiben), normalisiert + validiert TSX vor dem `cache.put`. Lädt `.env` am Repo-Root automatisch (minimaler eigener `_load_dotenv`, ohne `python-dotenv`-Dep). Ergebnis-Layout: `tests/fixtures/llm-cache/<digest>.json`.
- [x] 10 Tests in `core/tests/test_bedrock_client.py` (Modell-String-Stripping, fehlendes SDK, Text-Block-Extraktion via Fake-boto3, Region-Durchreichung, Default-Chain, Schema-Fehler, Exception-Wrapping). Alle 131 Tests grün, ruff/mypy clean.
- [x] **Live-Aufnahme erfolgreich**: 6/6 Cache-Einträge unter `tests/fixtures/llm-cache/` (~36 KB) live via Bedrock `converse` rekorded und eingecheckt.

#### Sub-Step 5b — `pull`/`verify` auf Dispatcher umstellen ✅
- [x] `pull` ruft `render_for_target` mit `ReplayCacheClient` (Default-Cache-Wurzel `tests/fixtures/llm-cache/`, Override via `--cache-dir` und `SPECCIFY_CACHE_DIR`). `--offline/--no-offline` Flag (Default `--offline`; Cache-Miss → Exit 1 mit klarer Meldung). Gemeinsamer Helper `speccify_cli.commands._llm_client.build_replay_client`.
- [x] Lockfile-Pin pro Spec auf `LlmGeneratorPin` (`provider=bedrock`, `model`, `prompt_version`, `seed`, `cache_key=sha256:<digest>`) gesetzt; Helper-Methode `Lockfile.with_generator(spec_id, generator)` in `core/src/speccify_core/lockfile.py`.
- [x] `verify` re-rendert via Replay-Client (`--offline/--cache-dir` analog zu `pull`) und prüft Modell-/Prompt-Version-/Seed-/Cache-Key-Drift gegen Lockfile-`LlmGeneratorPin`.
- [x] Tests neu/erweitert (9): `cli/tests/test_pull.py` (5: TSX-Output + Lockfile-Pin, Determinismus byte-identisch, Fail ohne Lockfile, Target-Mismatch, Cache-Miss bei leerem `--cache-dir`) und `cli/tests/test_verify.py` (6: Happy-Path, Disk-Drift, Fail ohne Lockfile, Fail ohne `pull`, Modell-Drift via manuell editiertes Lockfile, Cache-Miss). 134 Tests gesamt grün, ruff/format clean. mypy-Vor-Bestands-Fehler in Test-Dateien anderer Steps bleiben offen (siehe `.agent/resume.md`).
- [x] `example-project/`-E2E aktualisiert: alte Stub-`.md`-Outputs entfernt, 3 TSX-Dateien (`out/org/Button.tsx`, `out/org/ContactForm.tsx`, `out/org/OnboardingWizard.tsx`) regeneriert; `speccify.lock` enthält LLM-Pins; `speccify verify` läuft grün.
- [x] Status/Log/Plan-Sync (siehe `.agent/log.md` Eintrag 2026-05-12, `.agent/status.md`, `.agent/resume.md`).

#### Sub-Step 5c — CI
- [ ] CI-Workflow `.github/workflows/ci.yml`: E2E-Smoke `init` (tmp) + `add` + `pull --offline` + `verify --offline`.
- [ ] `scripts/record_llm_cache.py` in `README.md` dokumentiert.

### Step 6 — Master-Plan-Sync + Tag
- [ ] `speccify-plan.md`: Phase 1b auf "abgeschlossen" markieren, React-LLM-Strategie + Replay-Cache-Ansatz dokumentieren.
- [ ] `AGENTS.md` "Aktuelle Phase" auf 1c umstellen.
- [ ] `.agent/status.md` + `.agent/log.md` synchronisieren.
- [ ] Vorschlag annotated Tag `v0.2.0-phase-1b` an User (nicht selbst setzen).

### Open Questions (vor Step 4 geklärt)
1. **Provider-Default** ✅ — Anthropic Claude Sonnet 4.5 fix verdrahtet (Modell-String hart im Code, kein Env-Var-Switch in 1b). Provider-Switch via `LlmClient`-Protokoll bleibt für 1c+ offen.
2. **Normalisierungs-Tiefe** ✅ — Minimal: Trailing-Whitespace strippen, CRLF→LF, finale Newline erzwingen. Keine Quote-/Import-Normalisierung in 1b.
3. **TSX-Validitäts-Check** ✅ — Leichtgewichtige Heuristik: Klammer-/Tag-Balancing in Python, kein externer Parser.
4. **Cache-Fixture-Ort** ✅ — `tests/fixtures/llm-cache/` auf Repo-Root (klar als Test-Artefakt erkennbar).
