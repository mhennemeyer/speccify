---
title: 'Walkthrough: release-checks'
description: Ein echter Skill, von Anfang bis Ende — vom Quell-Repo zu drei verifizierten Tools in einem Projekt, das ausliefert.
sidebar:
  order: 5
---

Der Skill `release-checks` auditiert eine sandboxed macOS-App vor dem
App-Store-Upload: Entitlements, `Info.plist`-Usage-Keys, verwaiste
Lokalisierungs-Strings. Hier ist sein tatsächlicher Weg ins
Speccify-App-Projekt am 23.08.2026.

## Ausgangspunkt

Das Quell-Repo enthält den Skill und **drei Tool-Specs** — nur
Verträge, keine Implementierungen:

```text
github.com/mhennemeyer/speccify-first-test
└── skills/release-checks/
    ├── SKILL.md
    └── tools/
        ├── check-entitlements/TOOL.md
        ├── check-plist-keys/TOOL.md
        └── orphan-strings/TOOL.md
```

## Expand

`speccify expand release-checks` materialisierte den Skill im Projekt
und hielt die Herkunft fest:

```yaml
release-checks:
  source: git+https://github.com/mhennemeyer/speccify-first-test#skills/release-checks
  version: 1.0.0
  expanded: '2026-08-23'
  tools: [check-entitlements, check-plist-keys, orphan-strings]
```

Der Skill kam als normale `SKILL.md` unter `.agent/skills/` an und
bekam einen `## In this project`-Abschnitt mit den konkreten Fakten
*dieser* App: wie das Bundle gebaut wird, wo `Info.plist` und der
String-Katalog liegen, und welche Entitlements für das 1.0-Release
erwartet werden — „sandbox, network.client,
files.user-selected.read-write, bookmarks.app-scope — sonst nichts."
Der Upstream-Body blieb unberührt.

## Execute

Der Agent implementierte jeden Vertrag für diese Maschine:

| Tool                 | Implementierung | Warum diese Sprache                  |
| -------------------- | --------------- | ------------------------------------ |
| `check-entitlements` | `macos.sh`      | `codesign` macht die eigentliche Arbeit |
| `check-plist-keys`   | `macos.py`      | Plist-Parsen will einen echten Parser |
| `orphan-strings`     | `macos.py`      | läuft über Quellen + String-Katalog  |

Der `Pitfalls`-Abschnitt des Skills bewahrt für genau diesen Schritt
eine Lektion auf: Eine Shell-Implementierung, die stdin zweimal
liest — ein `python3 - <<EOF`-Heredoc nach `$(cat)` — verschluckt
das Input-JSON lautlos. Eine echte `.py`-Datei nehmen. Das ist die
Funktion von Pitfall-Abschnitten: Der nächste Agent entdeckt das
Problem nicht noch einmal.

## Evaluate

`speccify tool check` führte die Beispiele jedes Vertrags gegen die
Implementierungen aus, bis alle bestanden. Der Nachweis liest sich
jetzt, je Tool:

```yaml
platforms:
  macos:
    file: macos.py
    status: verified
    checked: '2026-08-23'
```

Dann die Urteilsschicht: den *Skill* gegen die echte App laufen
lassen und seine `Verify:`-Zeilen prüfen — jedes Entitlement benannte
ein ausgeliefertes Feature, die Plist-Keys hatten Besitzer, und jeder
Orphan-String-Kandidat wurde bestätigt oder erklärt statt blind
gelöscht (interpolierte Keys sind konstruktionsbedingt
False-Positives; der Skill sagt das dazu).

## Was am Ende steht

Drei verifizierte Tools und ein angepasster Skill, alles im Projekt
committet — ab jetzt für jeden Agenten nutzbar, ganz ohne
Speccify-Laufzeit. Und weil Verträge, Fixtures und Herkunft im Repo
liegen, startet die nächste Plattform (oder das nächste Projekt) von
derselben Quelle und wiederholt nur die Schritte, die wirklich
plattformspezifisch sind.
