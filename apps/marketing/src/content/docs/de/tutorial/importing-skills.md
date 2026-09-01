---
title: Skills importieren
description: Eine Skill-Quelle einbinden und einen Skill durch Expand, Execute, Evaluate bringen.
sidebar:
  order: 6
---

Eine Mac-App auszuliefern wirft Probleme auf, die mit der App selbst
nichts zu tun haben: Notarisierung, Release-Checks, Zertifikate —
schon einmal gelöst, womöglich von dir im letzten Projekt. Dieses
Kapitel importiert diese Lösungen als **Skills** in 4Notice, aus
einem Skills-Repo.

Sind die Konzepte neu: Die
[Speccify-Section](/de/speccify/overview/) erklärt sie; hier tun wir
es einfach.

## 1. Die Quelle einbinden

Im Skills-Tab der Speccify-App, unter **Quellen durchsuchen**, das Repo per URL
einbinden (oder `speccify add` im Terminal). Für 4Notice ist die
Quelle ein privates GitHub-Repo mit Skill-Bundles; der Zugriff läuft
über dieselben `gh`-Credentials, die git ohnehin benutzt. Das Projekt
merkt sich seine Abhängigkeiten in `speccify.yaml`:

```yaml
dependencies:
  git+https://github.com/<du>/<skills-repo>#skills/macos-notarize-tauri: ^1.0
  git+https://github.com/<du>/<skills-repo>#skills/release-checks: ^1.0
```

Die Repo-URL ist die Identität, Tags sind die Versionen, ein Bundle
ist ein Verzeichnis — `git+<url>#<pfad>`.

## 2. Import = Expand

Das Importieren eines Skills aus der Quellenliste führt den
[Expand-Schritt](/de/speccify/expand/) aus und endet mit einer
Aufgabenliste für den Agenten. Was aus zwei angeforderten Skills
tatsächlich in 4Notice ankam:

```text
.agent/skills/macos-notarize-tauri/     ← angefordert
.agent/skills/apple-developer-id-cert/  ← kam mit: der erste `uses` ihn
.agent/skills/release-checks/           ← angefordert
.agent/tools/check-entitlements/        TOOL.md + Fixtures
.agent/tools/check-plist-keys/          TOOL.md + Fixtures
.agent/tools/orphan-strings/            TOOL.md + Fixtures
.agent/tools/verify-signatures/         TOOL.md (nur Vertrag — s. unten)
.agent/speccify/expansions.yaml         ← Herkunft
```

Beachte die zweite Zeile: Abhängigkeiten zwischen Skills lösen sich
zur Expand-Zeit auf — `macos-notarize-tauri` erklärt, dass er auf
`apple-developer-id-cert` aufbaut, also kommt der als eigener
normaler Skill daneben an. Nichts verweist mehr zurück auf die
Quelle.

## 3. Execute: der Agent implementiert die Tools

Die Tool-Ordner kommen mit Verträgen und Fixtures, aber ohne
Implementierungen für deine Maschine — [das ist der
Punkt](/de/speccify/execute/). Ein Agenten-Lauf implementierte die
drei release-checks-Tools (`macos.py`, `macos.sh`) aus ihren
Verträgen.

Und ein Tool **blieb absichtlich Vertrag**: `verify-signatures` wird
erst zur Notarisierung gebraucht und ist deshalb noch nicht
implementiert. Import verpflichtet nicht, alles am ersten Tag zu
bauen — ein unimplementiertes Tool ist im Tools-Tab und im
Herkunftsnachweis als solches sichtbar, nicht vergessen.

## 4. Evaluate: prüfen, dann vertrauen

```sh
speccify tool check check-entitlements   # → verified
speccify tool check check-plist-keys     # → verified
speccify tool check orphan-strings       # → verified
```

Jeder Check führt die Beispiele des Vertrags gegen die frische
Implementierung aus ([wie das geht](/de/speccify/evaluate/)). Danach
nutzt der Agent diese Skills wie jeden lokalen — und loggt eine
`agent_run`-Zeile in die Ticket-History, wenn er es tut.

Der ganze Import war in 4Notice **ein atomarer Commit**, Subject
„Import skills from speccify-first-test and implement their tools" —
Skills, Tools, Fixtures, Herkunft, 3× verified, alles in einem
reviewbaren Schritt.

Weiter mit der Richtung, die daraus einen Kreislauf macht:
[exportieren, was 4Notice dich gelehrt hat](/de/tutorial/exporting-skills/).
