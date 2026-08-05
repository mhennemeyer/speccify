---
title: Targets
description: Aus einer Spec werden React, SwiftUI und Angular — deterministisch pinbar.
---

Ein *Target* ist eine Ziel-Technologie. Dieselbe Spec erzeugt Code für
mehrere Targets; welcher Generator mit welchem Pin gelaufen ist, steht im
Lockfile.

| Target | Ausgabe | Generator |
|---|---|---|
| `react` | `<scope>/<Name>.tsx` | LLM mit Replay-Cache |
| `swiftui` | `<Scope>/<Name>.swift` | LLM mit Replay-Cache |
| `angular` | `<scope>/<name>.component.ts` | LLM mit Replay-Cache |
| `react` (Mocks) | `<scope>/<Name>.mock.tsx` | **deterministisch, kein LLM** |
| `react` (Projekt) | komplettes Vite-Projekt | **deterministisch, kein LLM** |

```bash
uv run speccify pull --target react --offline
```

## Determinismus

- **Mocks und Projekt-Scaffold** sind reine Funktionen aus Spec-Bytes und
  Template-Version — zwei Läufe sind byte-identisch.
- **LLM-Targets** laufen in CI ausschließlich gegen einen eingecheckten
  Replay-Cache (`--offline`). Das Lockfile pinnt Modell, Prompt-Version, Seed
  und Cache-Key; `speccify verify` meldet jede Drift.

## Qualitäts-Vertrag

[Conformance](/conformance/) baut den generierten Code gegen die echten
Toolchains (`tsc --noEmit`, `swiftc -typecheck`), die
[Visual-Regression](/conformance/visual-regression/) vergleicht gerenderte
Screenshots gegen committete Referenzen.
