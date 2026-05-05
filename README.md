# Flowcation

> npm für Spezifikationen statt für Code — Komponenten beschreiben, nicht implementieren.
> Der AI-Agent ist der Compiler in das Ziel-Framework.

Flowcation ist eine Spec-First-Plattform für sprach- und framework-unabhängige Komponenten-Spezifikationen.
Eine `flowcation.yaml`-Spec beschreibt Verhalten, Inputs/Outputs, Akzeptanzkriterien und visuelle Referenzen
einer Komponente — und ein AI-Agent generiert daraus deterministisch Code für SwiftUI, React, Angular,
Jetpack Compose oder andere Targets. Verteilung über CLI (`flowcation`) und MCP-Server.

## Quickstart

```bash
uv sync
uv run pytest
uv run ruff check .
```

## Wo es weitergeht

- [`AGENTS.md`](./AGENTS.md) — Onboarding für Coding-Agents (Vision, Repo-Layout, Konventionen).
- [`.agent/plans/flowcation-plan.md`](./.agent/plans/flowcation-plan.md) — Master-Plan (langfristige Vision & Roadmap).
- [`.agent/plans/phase-0-spec-schema-spike.md`](./.agent/plans/phase-0-spec-schema-spike.md) — aktueller Implementierungs-Plan (Phase 0).

## Status

Phase 0 — Spec-Schema v0 + `flowcation lint` + 5 Referenz-Specs. Kein produktiver Code.

## Lizenz

MIT — siehe [`LICENSE`](./LICENSE).
