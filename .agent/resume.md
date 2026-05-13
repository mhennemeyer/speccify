# Resume — Schneller Wiedereinstieg

> Diese Datei ist der **Single-File-Wiedereinstieg** nach einem Rechner-
> Neustart. Wenn du als Agent eine neue Session beginnst: lies zuerst
> `.agent/agent.md`, dann **diese Datei**, dann `.agent/status.md` für
> den vollen Phasenstand und `.agent/plans/phase-1b-react-codegen.md`
> für den aktiven Plan.

## Stand 2026-05-12

- **Aktive Phase:** Phase 1b — React-Codegen.
- **Letzter abgeschlossener Schritt:** **Step 5b** (`pull`/`verify` auf
  `render_for_target` umgestellt; `--offline`/`--cache-dir`-Flags;
  `LlmGeneratorPin` ins Lockfile; Pin-Drift-Checks im `verify`).
- **Nächster offener Schritt:** **Step 5c** (CI-E2E-Smoke + README-Doku
  für `record_llm_cache.py`). Danach **Step 6** (Plan-Sync + Tag
  `v0.2.0-phase-1b`).

## Was läuft grün

```bash
uv run pytest             # 134 Tests grün
uv run ruff check .       # clean
uv run ruff format .      # clean
```

E2E im `example-project/`:

```bash
cd example-project
rm -rf out
uv run speccify lock
uv run speccify pull --out ./out      # 3 TSX-Dateien
uv run speccify verify --out ./out    # ✓ konsistent
```

Default-Cache: `tests/fixtures/llm-cache/` (im Repo eingecheckt, 6
Einträge aus Step 5a).

## Bekannte Lose Enden

- **mypy zeigt Vor-Bestand-Fehler** in:
  - `cli/tests/test_init.py` (CliRunner-Result-Typing aus Step 1),
  - `core/tests/test_bedrock_client.py` (Dict-Invarianz, Step 5a),
  - `core/tests/test_lockfile.py:126` (Union-Attribut nach Step 2).

  **Nicht durch Step 5b verursacht** — Status-Doku "mypy clean" war
  bereits in Step 5a leicht ungenau. In Step 5c (CI) sollten diese
  Fehler entweder behoben oder mypy auf `core/src cli/src` eingegrenzt
  werden (so wie es im 5a-Log dokumentiert ist).

## Wichtige Pfade

| Was | Pfad |
|---|---|
| Master-Plan | `.agent/plans/speccify-plan.md` |
| Aktiver Phasen-Plan | `.agent/plans/phase-1b-react-codegen.md` |
| Vollständiger Status | `.agent/status.md` |
| Session-Log (chronologisch, neuestes oben) | `.agent/log.md` |
| Replay-Cache (eingecheckt) | `tests/fixtures/llm-cache/` |
| CLI-Helfer Replay-Client | `cli/src/speccify_cli/commands/_llm_client.py` |
| Codegen-Dispatcher | `core/src/speccify_core/codegen/__init__.py` (`render_for_target`) |
| React-LLM-Adapter | `core/src/speccify_core/codegen/react_llm.py` |
| Live-Recorder (Bedrock) | `scripts/record_llm_cache.py` |
| example-project | `example-project/` (jetzt TSX, nicht mehr Markdown) |

## Worktree-Status beim Verlassen

`git status -s` (uncommitted):

```
 M .agent/log.md
 M .agent/plans/phase-1b-react-codegen.md
 M .agent/status.md
 M cli/src/speccify_cli/commands/pull.py
 M cli/src/speccify_cli/commands/verify.py
 M cli/tests/test_pull.py
 M cli/tests/test_verify.py
 M core/pyproject.toml
 D core/src/speccify_core/codegen/anthropic_client.py
 M core/src/speccify_core/codegen/react_llm.py
 M core/src/speccify_core/lockfile.py
 D core/tests/test_anthropic_client.py
 M pyproject.toml
 M scripts/record_llm_cache.py
 M uv.lock
?? .agent/resume.md
?? cli/src/speccify_cli/commands/_llm_client.py
?? core/src/speccify_core/codegen/bedrock_client.py
?? core/tests/test_bedrock_client.py
?? tests/
```

Letzter Commit (auf `main` o. ä.): `4160787 Complete Phase 1b Step 5:
Implement Anthropic Client for Live LLM Interaction` — d.h. Step 5a
(Bedrock-Switch + Live-Aufnahme) und Step 5b sind **noch nicht
committet**. Empfohlener nächster Commit-Schnitt:

1. `feat: switch LLM provider from Anthropic to AWS Bedrock` (Step 5a).
2. `feat(cli): wire pull/verify to render_for_target with replay cache`
   (Step 5b).
3. Danach Step 5c als separater Commit.

## Wiederaufnahme-Rezept

1. `uv sync` (Workspace).
2. `uv run pytest` → muss 134 grün zeigen.
3. `cat .agent/resume.md` (diese Datei) lesen.
4. `cat .agent/status.md` für Phasen-Stand.
5. `cat .agent/plans/phase-1b-react-codegen.md` → Step 5c als
   nächsten offenen Punkt suchen und starten.
