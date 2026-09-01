---
title: Skills, Tools & Quellen
description: Was dein Agent hier kann — in der App durchsuchbar, importierbar aus Speccify-Quellen.
sidebar:
  order: 5
---

Der Skills-Tab zeigt, was der Agent in *diesem* Projekt zu tun weiß:
die [Skills](/de/fundamentals/skills/) unter `.agent/skills/`, jeder
mit seiner Herkunft aus `expansions.yaml`. Der Tools-Tab tut dasselbe
für die [Tools](/de/fundamentals/tools/) unter `.agent/tools/` —
dieselben Dateien, die der Agent liest, für dich gerendert.

:::note[Screenshot]
*Platzhalter: Skills-Tab mit dem release-checks-Skill und seinen
Tools.*
:::

## Eine Quelle der Wahrheit, viele Agenten

`.agent/skills/` ist die Quelle; agent-spezifische Ordner sind
Links dorthin (auf Windows als Junction):

```text
.claude/skills → ../.agent/skills
.agents/skills → ../.agent/skills
```

Einen Skill unter `.agent/skills/` anlegen oder ändern — und jeder
Agent sieht ihn sofort. Die Regel gilt für dich wie für den Agenten:
Dort editieren, nie im Dot-Ordner.

## Quellen: Skills, die du nicht geschrieben hast

Skills und Tools können aus einer **Speccify-Quelle** kommen — einem
Skills-Repo. Der Modus **Quellen durchsuchen** im Skills-Tab zeigt
die Quellen dieses Projekts (eine oder mehrere; der Default kommt aus
den Dashboard-Settings). Die Ordnerstruktur der Quelle *ist* die
Organisation — ihre Ordner sind die Kategorien, durch die du
blätterst. Ein Skill lässt sich als Vorschau ansehen;
**Importieren (expand)** tippt das passende
`speccify add … && speccify expand …`-Kommando ins Agent-Terminal,
und der [Expand-Schritt](/de/speccify/expand/) erledigt den Rest:
normale Skills landen in `.agent/skills/`, Tool-Verträge in
`.agent/tools/`, und `.agent/speccify/expansions.yaml` hält fest,
woher jeder kam, in welcher Version, und ob die Implementierung jedes
Tools auf dieser Plattform `verified` ist.

Zwei Regeln halten die Buchhaltung gesund:

- **Editiere Skills und Tools, nicht `expansions.yaml`** — den
  Nachweis pflegt Speccify; Hand-Edits würden ihn lügen lassen.
- **Tools sind absichtlich vorab genehmigt.** Die Settings des Hosts
  (bei Claude Code `.claude/settings.json`) erlauben das Ausführen
  von allem unter `.agent/tools/` — Implementierungen sind
  vertragsgeprüft, also kann der Agent sie ohne Permission-Prompt
  aufrufen.

Nutzt der Agent einen expandierten Skill während er ein Ticket
bearbeitet, loggt er eine `agent_run`-Zeile in die Ticket-History mit
Skill- und Tool-Namen — das [Ticket-Detail](/de/app/board/) ist
die Spur dessen, was benutzt wurde; eine separate Log-Datei gibt es
nicht.
