---
title: Überblick
description: Geteilt wird der Vertrag, nicht die Implementierung — Speccifys Expand-Execute-Evaluate-Schleife.
sidebar:
  order: 1
---

Fertige Skripte wandern nicht. Ein `.py` oder `.sh`, das auf einer
Maschine läuft, bricht auf der nächsten: Python-Version, Shell,
Pfadtrenner, fehlende Binaries — und der Empfänger patcht am Ende
eine fremde Datei. Speccifys Antwort: **Skills mit Tool-Specs**
teilen statt Skills mit Skripten:

> Ein Skill beschreibt, *was* zu tun ist; ein Tool-Spec beschreibt
> genau, *was ein Werkzeug können muss* — und der Agent programmiert
> es **vor Ort** aus, in dem, was auf dieser Maschine läuft. Geteilt
> wird der Vertrag, nicht die Implementierung.

Ein Spec erzwingt zudem eine Präzision, die im fertigen Skript
implizit bleibt: Eingaben, Ausgaben, Seiteneffekte, Beispiele. Ein
Skript sagt *wie*; ein Spec sagt *was* — und *was* altert langsamer.

## Zwei Welten

Ein Skill existiert in zwei klar getrennten Formen:

|            | In der **Quelle** (ein Skills-Repo)          | Im **Projekt** (`.agent/`)                       |
| ---------- | -------------------------------------------- | ------------------------------------------------ |
| Form       | `SKILL.md` + Speccify-Metadaten + Tool-Specs | ganz normale Skills — einfaches Markdown         |
| Referenzen | `uses` zeigt auf andere Skills               | aufgelöst: jeder referenzierte Skill liegt daneben |
| Tools      | nur Spec (`TOOL.md`)                         | **implementiert**, eine Variante pro Plattform   |
| Platzhalter | generisch                                   | konkret für dieses Projekt                       |
| Git        | im Quell-Repo                                | **committet** im Projekt-Repo                    |

Das expandierte Ergebnis braucht Speccify nicht mehr, um zu
funktionieren — es sind einfach Dateien unter `.agent/`, genau wie in
den [Grundlagen](/de/fundamentals/overview/) beschrieben.

## Der Dreischritt

1. **[Expand](/de/speccify/expand/)** — der Übergang von Quelle zu
   Projekt: Referenzen auflösen, Metadaten abstreifen, Platzhalter
   konkretisieren, Tool-Verträge kopieren, Herkunft festhalten.
2. **[Execute](/de/speccify/execute/)** — der Agent implementiert
   jedes Tool für diese Plattform aus seinem Vertrag und folgt dem
   Skill.
3. **[Evaluate](/de/speccify/evaluate/)** — mechanische Prüfung
   (`speccify tool check` führt die Beispiele des Vertrags aus) plus
   die aktive Gegenbeweis-Suche des Agenten. Fehlschläge führen
   zurück in die Schleife.

Der [Walkthrough](/de/speccify/walkthrough/) verfolgt einen echten
Skill — `release-checks` — durch alle drei Schritte.
