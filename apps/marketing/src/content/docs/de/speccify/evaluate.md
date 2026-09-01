---
title: Evaluate
description: Eingebaute Mini-QA — eine mechanische Schicht und eine Urteilsschicht, mit Rückschleife bei Fehlschlag.
sidebar:
  order: 4
---

**Evaluate** ist der eingebaute QA-Schritt, und er hat zwei
Schichten.

## Die mechanische Schicht: `speccify tool check`

```sh
speccify tool check check-plist-keys
```

Das Kommando füttert jedes Beispiel aus der `TOOL.md` des Tools in
die Implementierung dieser Plattform und vergleicht das JSON. Grün
oder rot, ohne Urteil. Die Beispiele im Vertrag *sind* der
Abnahmetest:

```markdown
### a plist with a camera usage description
input: {"plist": "fixtures/Camera.plist"}
output: {"ok": true, "keys": ["NSCameraUsageDescription"]}
```

Das Verdikt landet in `expansions.yaml`: Ein bestandenes Tool geht
auf `status: verified` mit Datum und Plattform; ein durchgefallenes
fällt zurück auf `implemented`. Die Buchhaltung ist in beide
Richtungen ehrlich — bringt ein Re-Expand einen geänderten Vertrag
(der Spec-Hash weicht ab), wird das `verified`-Abzeichen *entfernt*,
bis der Check wieder besteht. Ein Tool ist nie „verified" gegen einen
Vertrag, gegen den es nicht geprüft wurde.

## Die Urteilsschicht: der Agent sucht Gegenbeweise

Mechanische Checks beweisen, dass die Tools ihren Verträgen
entsprechen — nicht, dass das *Ergebnis des Skills* stimmt. Also
prüft der Agent das Resultat gegen die **`Verify:`-Zeilen** des
Skills (jeder Schritt eines gut geschriebenen Skills hat eine) und
gegen die Akzeptanzkriterien des Tickets — und sucht dabei aktiv nach
Gegenbeweisen, nicht nach Bestätigung.

- Kein Gegenbeweis gefunden → fertig.
- Gegenbeweis gefunden → **neue Iteration**: zurück zu
  [Expand](/de/speccify/expand/), wenn die Anpassung falsch war,
  zurück zu [Execute](/de/speccify/execute/), wenn die Ausführung es
  war.

Befunde, die sich als *generell* erweisen — eine Falle, in die jeder
tappen würde, eine Lücke im Vertrag — fließen als Korrektur zurück
ins Quell-Repo, damit das nächste Projekt einen besseren Skill
expandiert.

Die ganze Schleife am Stück: der
[Walkthrough](/de/speccify/walkthrough/).
