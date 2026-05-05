# Log: Flowcation

## 2026-05-05
- Projekt initialisiert
- Phase-0-Abschluss-Tooling ergänzt:
  - `ruff`, `mypy`, `types-PyYAML` als Dev-Deps in Workspace-`pyproject.toml` gepinnt
    (passt zur Tooling-Aussage in `AGENTS.md`).
  - Repo mit `ruff format` formatiert (2 Dateien angepasst:
    `cli/tests/test_lint.py`, `core/src/flowcation_core/validator.py`).
  - GitHub-Actions-Workflow `.github/workflows/ci.yml` um Format-Check + Mypy
    erweitert (vorher nur `ruff check` + Tests + lint).
- Verifiziert lokal: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy core/src cli/src`, `uv run pytest` (12 Tests),
  `uv run flowcation lint specs/*.yaml` — alle grün.
- Phase 0 inhaltlich vollständig (Stages 1–8 abgedeckt); offen sind nur die
  im Phase-0-Plan genannten Open Questions sowie der Übergang zu Phase 1.
