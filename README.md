# Speccify

> npm für Spezifikationen statt für Code — Komponenten beschreiben, nicht implementieren.
> Der AI-Agent ist der Compiler in das Ziel-Framework.

Speccify ist eine Spec-First-Plattform für sprach- und framework-unabhängige Komponenten-Spezifikationen.
Eine `speccify.yaml`-Spec beschreibt Verhalten, Inputs/Outputs, Akzeptanzkriterien und visuelle Referenzen
einer Komponente — und ein AI-Agent generiert daraus deterministisch Code für SwiftUI, React, Angular,
Jetpack Compose oder andere Targets. Verteilung über CLI (`speccify`) und MCP-Server.

## Quickstart

```bash
uv sync
uv run pytest
uv run ruff check .
```

## Wo es weitergeht

- [`AGENTS.md`](./AGENTS.md) — Onboarding für Coding-Agents (Vision, Repo-Layout, Konventionen).
- [`.agent/plans/speccify-plan.md`](./.agent/plans/speccify-plan.md) — Master-Plan (langfristige Vision & Roadmap).
- [`.agent/plans/phase-1a0-rename-to-speccify.md`](./.agent/plans/phase-1a0-rename-to-speccify.md) — Aktiver Rebrand-Plan (`flowcation` → `speccify`).
- [`.agent/plans/archive/phase-0-wrap-up.md`](./.agent/plans/archive/phase-0-wrap-up.md) — Phase-0-Wrap-up (abgeschlossen, ADR-Light für Q1–Q5).
- [`.agent/plans/phase-1a-resolver-lockfile.md`](./.agent/plans/phase-1a-resolver-lockfile.md) — Nächster Schritt: Resolver + Lockfile + `add`/`pull`/`verify`.
- [`.agent/plans/archive/phase-0-spec-schema-spike.md`](./.agent/plans/archive/phase-0-spec-schema-spike.md) — Phase-0-Implementierungs-Plan (abgeschlossen, archiviert).

## Status

Phase 0 abgeschlossen (Schema v0 + `speccify lint` + 5 Referenz-Specs, Tag `v0.0.0-phase0`). Aktiv: Phase 1a-0 — Rebrand auf `speccify`, danach Phase 1a (Resolver + Lockfile).

## Lizenz

MIT — siehe [`LICENSE`](./LICENSE).
