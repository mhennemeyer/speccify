---
title: Was wir bauen
description: 4Notice, eine kleine Zwei-Plattform-Notiz-App — vom leeren Ordner bis in den App Store mit Claude Code, der Speccify-App und der Speccify-CLI.
sidebar:
  order: 1
---

Dieses Tutorial baut eine echte App, von Anfang bis Ende: **4Notice**,
eine kleine SwiftUI-Notizzettel-App — vier Zettel, immer zur Hand —
für macOS und iOS aus gemeinsamen Quellen. Die App ist absichtlich
klein; Gegenstand ist die Methode, und die Methode skaliert.

Am Ende bist du vom leeren Ordner bis zur App-Store-Einreichung
gekommen, und unterwegs hast du:

- ein Projekt aufgesetzt, an dem ein **Terminal-Agent** produktiv
  arbeiten kann — Plan, Board, Aktionen, alles als Dateien im Repo;
- gelernt, mit **Plänen und Tickets** stetig voranzukommen und die
  Historie mit **atomaren Commits** ehrlich zu halten;
- **Skills importiert** aus einer Quelle und durch
  Expand → Execute → Evaluate gebracht;
- **deinen eigenen Skill exportiert** — einen Workflow, den du beim
  Bauen gelernt hast — in dein eigenes Speccify-Work-Repo, wo dein
  nächstes Projekt ihn findet;
- die App lokalisiert, **fastlane** und
  App-Store-Connect-Automatisierung verdrahtet und vor dem Upload die
  Release-Checks laufen lassen.

## Die drei Werkzeuge

| Werkzeug         | Rolle in diesem Tutorial                                     |
| ---------------- | ------------------------------------------------------------ |
| **Claude Code**  | der Agent: implementiert Tickets, schreibt Tools, committet   |
| **Speccify-App** | das Cockpit des Owners: Board, Pläne, Skills, Aktionen        |
| **Speccify-CLI** | der Skill-/Tool-Manager: Quellen, Expand, Check, Export       |

Keines davon ist tragend für das *Ergebnis*: Am Ende stehen einfache
Dateien und gewöhnliche Xcode-Builds. Jeder Schritt bleibt
inspizierbar, jedes Werkzeug austauschbar.

## Wie das hier zu lesen ist

Das Tutorial ist ehrlich, was seine Herkunft angeht: 4Notice ist ein
echtes Projekt, und jedes Kapitel wurde geschrieben, **nachdem** der
entsprechende Schritt dort wirklich passiert ist. Kapitel, deren
Schritt noch aussteht, sind als markierte Stubs sichtbar — der Bogen
ist real, nicht projiziert. Wer die Konzepte hinter einem Schritt
will: Die Reference-Sections
([Grundlagen](/de/fundamentals/overview/),
[Speccify](/de/speccify/overview/),
[die Speccify-App](/de/app/overview/)) gehen tiefer; das Tutorial
verlinkt dorthin, statt sie zu wiederholen.

Erste Station: [was installiert sein muss](/de/tutorial/prerequisites/).
