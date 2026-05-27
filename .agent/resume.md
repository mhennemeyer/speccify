# Resume — Speccify Phase 4 abgeschlossen

> Einstiegspunkt für die nächste Session. Letzte Aktualisierung: 2026-05-27.

## Status

- **Phase 4 abgeschlossen** (2026-05-27). Plan archiviert: [`plans/archive/phase-4-workspaces.md`](./plans/archive/phase-4-workspaces.md).
- **Tag-Vorschlag an User**: `v0.7.0-phase-4` (selbst nicht setzen, vgl. `rules.md`).
- **Phase 3** abgeschlossen (Stages 0–8); Tag-Vorschlag `v0.6.0-phase-3` (offen).
- **Phase 2** abgeschlossen; Tag-Vorschlag `v0.5.0-phase-2` (offen).
- **Kein aktiver Plan** in `.agent/plans/` (außer Master-Plan).

## Verifikation Phase 4

- **Root-Pytest**: 312 passed (+19 ggü. Phase 3 = 293).
- **Registry-Pytest**: 119 passed (unverändert).
- **Gesamt: 431 Tests grün.**
- `ruff check` → All checks passed.
- `ruff format --check` → 141 files already formatted.

## Was Phase 4 geliefert hat

- **Stage 0**: 10 Open Questions vom User geklärt — Root-only Lockfile (Cargo-Style), sichtbares `<member>/speccify_generated/`, CWD-Detection für `add`, strikte MVS-Konflikt-Strategie, keine Path-Deps, Hash-only Verify, MCP-Bridge via `workspace_root`-Arg, Web out-of-scope, kein Schema-Bump, `workspaces:`-Key-Heuristik.
- **Stage 1**: `Workspace.lock(registry) -> Lockfile` in `core/src/speccify_core/workspace.py` + 3 Tests (Happy, leere Targets, Range-Konflikt).
- **Stage 2**: `cli/.../lock.py` delegiert im Workspace-Modus an `workspace.lock()`.
- **Stage 3**: `cli/.../pull.py` workspace-aware, materialisiert nach `<member>/speccify_generated/<target>/`; Helper `_render_lock_entry_into()` extrahiert. `--target` im Workspace verboten.
- **Stage 4**: `cli/.../add.py` mit `--member/-m`-Flag + CWD-Detection (`_resolve_workspace_target_dir`); automatischer Root-Re-Lock.
- **Stage 5**: `cli/.../verify.py` mit `_run_workspace_verify()` — Hash-only (Member-Deps ⊆ Root-Lockfile + Disk-Hash), kein Re-Render, kein LLM-Pin-Check.
- **Stage 6**: Diagnostische `ResolverError`-Message per Snapshot-Test gepinnt; MCP-Bridge: `lock`/`pull`/`verify` mit optionalem `workspace_root`-Parameter, delegieren an CLI-`run_*`-Funktionen (Single-Source-of-Truth).
- **Stage 7**: `docs/workspaces.md` (193 LOC) — Konzept, CLI-Walkthrough, Konflikt-Beispiel, MCP-Integration, Design-Entscheidungen; README um Workspaces-Link + Phase-3/4-Archivlinks erweitert.
- **Stage 8**: Plan-Archivierung + AGENTS.md/resume.md aktualisiert.

## Nächster Schritt — Phase-5-Plan-Entwurf nach User-Tag

Kandidaten (aus Phase-3-Folge-Substages, die bei Phase 4 explizit out-of-scope waren):

1. **Conformance-Backends**: Build-Smoke (echte `tsc`/`swiftc`/`ng build`) + Visual-Regression gegen Spec-`screenshots[]` (Phase 3 Stage 0 hatte MVP-Decision dafür).
2. **75-Pfad-Cross-Consistency-Sweep**: voller Sweep über `5 Specs × 3 Targets × 5 Pfade (Local/Remote/CLI/MCP/Web)` mit echtem Bedrock-Replay-Cache für SwiftUI/Angular.
3. **Fehlende Phase-0-Specs**: vollständige 5er-Reihe (statt nur Button + ContactForm).
4. **Web-Backend Workspace-aware** (Phase 4 out-of-scope): Member-Liste + aggregierter Lockfile-View im Playground.

Vor Implementierung: Stage 0 = Open Questions an User (analog Phase 3/4-Disziplin).

## Befehle (Spickzettel)

```bash
# Hidden-Flag entfernen (jedes Mal nach uv sync nötig) — läuft auch automatisch via conftest.py
chflags nohidden .venv/lib/python3.12/site-packages/*.pth

# Root-Tests
.venv/bin/python -m pytest -q

# Registry-Tests
cd registry && ../.venv/bin/python -m pytest -q

# Lint + Format
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

## Pflichtlektüre vor Code

1. `AGENTS.md` (Aktuelle Phase + Konventionen).
2. `.agent/agent.md` + `.agent/rules.md` (Sprache: Deutsch, Du; FP-Stil; Tests pflicht; Tags nur User).
3. `docs/workspaces.md` (Phase-4-Doku, Decisions + CLI-Walkthrough).
4. `.agent/plans/archive/phase-4-workspaces.md` (Phase-4-Plan mit Status-Block oben).
