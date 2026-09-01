---
title: Execute
description: Der Agent implementiert jedes Tool vor Ort aus seinem Vertrag — und folgt dann dem Skill.
sidebar:
  order: 3
---

**Execute** ist der Part des Agenten. Expand hat eine Aufgabenliste
hinterlassen — typischerweise *„n Tools für diese Plattform zu
implementieren"* — und in jedem Tool-Ordner einen `TOOL.md`-Vertrag.
Der Agent schreibt jetzt die Plattform-Datei neben jeden Vertrag:

```text
.agent/tools/check-plist-keys/
├── TOOL.md        ← der Vertrag (kam aus der Quelle)
├── fixtures/      ← Testdateien, auf die die Beispiele verweisen
└── macos.py       ← hier geschrieben, vom Agenten, für diese Maschine
```

Der Vertrag legt alles Wesentliche fest — Input-Schema,
Output-Schema, deklarierte Effekte, durchgerechnete Beispiele —
sodass „implementier das" eine eng umrissene Aufgabe ist:

- **Das Wire-Format ist nicht verhandelbar:** ein JSON-Objekt auf
  stdin, ein JSON-Objekt auf stdout, Exit 0 wenn `ok` true ist.
- **Die Sprache ist frei.** Auf dieser Maschine wurde es `python3`
  (`macos.py`) fürs Plist-Parsen und ein Shell-Skript (`macos.sh`),
  wo `codesign` die eigentliche Arbeit macht. Eine andere Plattform
  bekommt ihre eigene Datei — `windows.ps1` neben `macos.py` — und
  **beide werden committet**: Die nächste Maschine derselben
  Plattform implementiert nichts mehr.
- **Fehlerfälle gehören zum Vertrag.** Enthalten die Beispiele des
  Specs einen Fehlende-Datei-Fall mit `ok: false` und
  `error`-String, muss die Implementierung genau das tun.

Die Iterationsregel: implementieren, dann
[`speccify tool check`](/de/speccify/evaluate/) — und weitermachen,
**bis jedes Beispiel besteht**. Nicht der Agent erklärt ein Tool für
fertig; der Check tut es.

Stehen die Tools, ist das Ausführen des *Skills* nichts Besonderes:
Der Agent folgt der expandierten `SKILL.md` Schritt für Schritt und
ruft die Tools auf, denen er jetzt trauen kann — genau wie unter
[Skills](/de/fundamentals/skills/) beschrieben. Speccify ergänzt nur
eine **Spur** — welcher Skill lief, welche Iteration, wann — damit es
später eine Antwort auf „was hat er eigentlich getan?" gibt.

Ob das Ergebnis taugt, beantwortet
[Evaluate](/de/speccify/evaluate/).
