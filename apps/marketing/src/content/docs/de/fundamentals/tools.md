---
title: Tools & Tool-Specs
description: Kleine Programme mit striktem Vertrag — JSON rein, JSON raus, und eine TOOL.md, die sie prüfbar macht.
sidebar:
  order: 3
---

Ein **Tool** ist ein kleines Programm, das ein Skill aufrufen kann:
die Entitlements eines App-Bundles auflisten, verwaiste
Lokalisierungs-Keys finden, eine Plist prüfen. Was es zum *Tool*
macht statt zum losen Skript, ist der **Spec**: eine `TOOL.md` neben
der Implementierung, die den Vertrag so präzise festhält, dass eine
Maschine ihn prüfen kann.

## Die Konvention

- Ein Ordner pro Tool unter `.agent/tools/<name>/`.
- `TOOL.md` ist der **Vertrag**: Input und Output als JSON Schema,
  deklarierte `effects` und `requires`, durchgerechnete Beispiele.
- Daneben **eine Implementierung pro Plattform**: `macos.py`,
  `macos.sh`, `linux.py`, … — was die Plattform eben braucht.
- Das Wire-Format ist immer gleich: **ein JSON-Objekt auf stdin, ein
  JSON-Objekt auf stdout**, Exit-Code 0 wenn `ok` true ist.
- Tools sind projektweit. Mehrere Skills können ein Tool teilen; ein
  Skill verlinkt es als `../../tools/<name>/`.

## Ein echter Vertrag

`check-plist-keys` aus dem Speccify-App-Projekt — die vollständige
`TOOL.md`:

```markdown
---
name: check-plist-keys
description: Lists usage-description and background keys in an
  Info.plist — every entry must belong to a shipped feature.
inputs:
  type: object
  required: [plist]
  additionalProperties: false
  properties:
    plist:
      type: string
      description: Path to the Info.plist, relative to the tool
        directory or absolute.
outputs:
  type: object
  required: [ok, keys]
  properties:
    ok: {type: boolean}
    keys: {type: array, items: {type: string}, description: Matching
      keys (UsageDescription, NSUbiquitousContainers,
      UIBackgroundModes), sorted.}
    error: {type: string}
effects: reads the plist; writes nothing
requires: python3
runtime: any
---

## Behaviour

Read the plist and report every key that App Review would ask about:
all `*UsageDescription` keys, `NSUbiquitousContainers` and
`UIBackgroundModes`. An empty list is a valid, good answer. A missing
or unreadable file is `ok: false`.

## Examples

### a plist without any such keys
input: {"plist": "fixtures/Clean.plist"}
output: {"ok": true, "keys": []}

### a plist with a camera usage description
input: {"plist": "fixtures/Camera.plist"}
output: {"ok": true, "keys": ["NSCameraUsageDescription"]}

### missing file
input: {"plist": "fixtures/Missing.plist"}
output: {"ok": false, "keys": [], "error": "cannot read fixtures/Missing.plist"}
```

Jeder Teil hat eine Funktion:

- **`inputs` / `outputs` als JSON Schema** — keine Prosa. Ein Agent
  (oder Mensch) kann einen Aufruf validieren, bevor er ihn macht.
- **`effects` und `requires`** — je eine Zeile, damit ein Reviewer
  weiß, was ein Lauf anfassen kann und was installiert sein muss.
- **`## Examples` sind Testfälle**, keine Dekoration. Jedes benennt
  eine Fixture, die im Tool-Ordner mitkommt. `speccify tool check
  check-plist-keys` führt jedes Beispiel gegen die Implementierung
  aus und vergleicht das JSON — die Beispiele *sind* der
  Abnahmetest.
- **Der Fehlerfall gehört zum Vertrag.** Eine fehlende Datei liefert
  `ok: false` mit `error`-String; sie stürzt nicht ab und weicht
  nicht auf stderr aus.

## Ein Tool aufrufen

Aus einer Shell (und aus den Anweisungen eines Skills) sieht ein
Aufruf so aus:

```sh
echo '{"plist": "fixtures/Camera.plist"}' | python3 .agent/tools/check-plist-keys/macos.py
# → {"ok": true, "keys": ["NSCameraUsageDescription"]}
```

Eine Falle aus der Praxis, festgehalten im Skill, der diese Tools
benutzt: Eine Shell-Implementierung, die stdin zweimal liest — etwa
ein `python3 - <<EOF`-Heredoc nach `$(cat)` — verschluckt das JSON
lautlos. Lieber eine echte `.py`-Datei als Inline-Heredocs.

## Warum die Trennung von Skill und Tool zählt

Ein Skill sagt, *wann* eine Prüfung läuft und *was das Ergebnis
bedeutet*; ein Tool *misst*. Der messende Teil ist deterministisch
und maschinell geprüft — ein Agent kann dort nicht still abdriften:
Widersprechen sich Implementierung und Vertrag, schlägt
`speccify tool check` fehl. Das Urteil bleibt, wo es hingehört: im
[Skill](/de/fundamentals/skills/) und letztlich beim Owner. Wie ein
Tool vom Vertrag zur geprüften Implementierung kommt, ist Thema der
[Speccify-Section](/de/speccify/overview/).
