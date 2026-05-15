# Resume — Schneller Wiedereinstieg

> Diese Datei ist der **Single-File-Wiedereinstieg** nach einem Rechner-
> Neustart. Wenn du als Agent eine neue Session beginnst: lies zuerst
> `.agent/agent.md`, dann **diese Datei**, dann `.agent/status.md` für
> den vollen Phasenstand und `.agent/plans/phase-1c-mcp-server.md`
> für den aktiven Plan.

## Stand 2026-05-15

- **Aktive Phase:** Phase 1c — MCP-Server (`speccify-mcp`).
- **Letzter abgeschlossener Schritt:** **Step 0** (`mcp[cli]>=1.27.1,<2.0`
  in `mcp/pyproject.toml` gepinnt, `uv.lock` aktualisiert, 134 Tests
  grün, ruff/format clean).
- **Nächster offener Schritt:** **Step 1** — Server-Skeleton
  (`speccify_mcp.cli` mit `--project`/`--log-level`, `server.py` mit
  leerem Tool-Set + Health-Check) + Unit-Test, der den Server
  instanziiert und ein leeres `tools/list` zurückbekommt.
- **Phase 1b ist abgeschlossen und lokal getaggt** (`v0.1.0-phase-1a`
  → `d28cb33`, `v0.2.0-phase-1b` → `8c90511`). Kein Git-Remote → kein
  Push.

## Was läuft grün

```bash
uv run pytest             # 134 Tests grün
uv run ruff check .       # clean
uv run ruff format .      # clean
```

E2E im `example-project/` (Phase-1b-Smoke, immer noch grün):

```bash
cd example-project
rm -rf out
uv run speccify lock
uv run speccify pull --out ./out      # 3 TSX-Dateien
uv run speccify verify --out ./out    # ✓ konsistent
```

Default-Cache: `tests/fixtures/llm-cache/` (im Repo eingecheckt, 6
Einträge).

## Bekannte lose Enden

- **mypy zeigt Vor-Bestand-Fehler** in:
  - `cli/tests/test_init.py` (CliRunner-Result-Typing aus Phase 1b
    Step 1),
  - `core/tests/test_bedrock_client.py` (Dict-Invarianz, Step 5a),
  - `core/tests/test_lockfile.py:126` (Union-Attribut nach Step 2).

  Nicht durch Phase-1c-Arbeit verursacht. Bei Bedarf in einem
  Phase-1c-Step gemeinsam mit dem MCP-Test-Setup einsammeln oder
  `mypy` auf `core/src cli/src mcp/src` eingrenzen.
- **`.venv`-Artefakt-Falle**: nach `uv sync --all-packages` können
  präexistierende `_editable_impl_*.pth`-Dateien ohne Trailing-Newline
  dazu führen, dass `speccify_*` nicht mehr importierbar sind, obwohl
  `uv pip list` sie zeigt. Fix: `uv sync --all-packages --reinstall`
  oder `.venv` löschen + neu bauen. Vgl. Log 2026-05-15 + 2026-05-13
  Step 5c.

## Wichtige Pfade

| Was | Pfad |
|---|---|
| Master-Plan | `.agent/plans/speccify-plan.md` |
| Aktiver Phasen-Plan | `.agent/plans/phase-1c-mcp-server.md` |
| Vollständiger Status | `.agent/status.md` |
| Session-Log (chronologisch, neuestes oben) | `.agent/log.md` |
| Replay-Cache (eingecheckt) | `tests/fixtures/llm-cache/` |
| CLI-Helfer Replay-Client | `cli/src/speccify_cli/commands/_llm_client.py` |
| Codegen-Dispatcher | `core/src/speccify_core/codegen/__init__.py` (`render_for_target`) |
| React-LLM-Adapter | `core/src/speccify_core/codegen/react_llm.py` |
| Live-Recorder (Bedrock) | `scripts/record_llm_cache.py` |
| MCP-Paket (Skeleton folgt in Step 1) | `mcp/src/speccify_mcp/` |
| example-project | `example-project/` (TSX-Outputs) |

## Worktree-Status

Phase-1c-Step-0-Änderungen (uncommitted):

```
 M .agent/log.md
 M .agent/plans/phase-1c-mcp-server.md
 M .agent/resume.md
 M .agent/status.md
 M mcp/pyproject.toml
 M uv.lock
```

Empfohlener Commit-Schnitt nach Step 0:
`chore(mcp): pin mcp[cli]>=1.27.1,<2.0 (phase-1c step 0)`.

## Wiederaufnahme-Rezept

1. `uv sync --all-packages` (Workspace). Falls Importe nach dem Sync
   fehlschlagen: `uv sync --all-packages --reinstall`.
2. `uv run pytest` → muss 134 grün zeigen.
3. `cat .agent/resume.md` (diese Datei) lesen.
4. `cat .agent/status.md` für Phasen-Stand.
5. `cat .agent/plans/phase-1c-mcp-server.md` → Step 1 als nächsten
   offenen Punkt suchen und starten (Skeleton + leeres `tools/list`).
