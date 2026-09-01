---
title: Den eigenen Skill exportieren
description: Ein gelernter Workflow wird ein Skill in deinem eigenen Speccify-Work-Repo.
sidebar:
  order: 7
---

Importieren ist der halbe Kreislauf. Die andere Hälfte: Was dich das
Bauen von 4Notice *gelehrt* hat, geht zurück in ein Repo, das dir
gehört — dein **Speccify-Work-Repo** —, verfügbar für jedes folgende
Projekt. Dieses Kapitel setzt dieses Repo auf.

## 1. Dein Work-Repo anlegen

Ein privates GitHub-Repo, ein Verzeichnis pro Skill-Bundle:

```text
dein-skills-repo/
└── skills/
    ├── macos-notarize-tauri/
    │   ├── SKILL.md
    │   └── tools/
    │       └── verify-signatures/
    │           ├── TOOL.md
    │           └── fixtures/…
    └── release-checks/
        ├── SKILL.md
        └── tools/…
```

```sh
gh repo create dein-skills-repo --private
```

Bundles enthalten **Tool-Specs, keine Implementierungen** — Verträge
wandern, Skripte nicht ([warum](/de/speccify/overview/)). Ein
`reference.py` pro Tool ist als durchgerechnetes Beispiel für eine
Plattform in Ordnung; die Wahrheit bleibt der Spec.

## 2. Tag-Disziplin

Versionen sind Git-Tags, einer pro Bundle: `skills/<name>/v1.0.0`.
Zwei Regeln aus der Praxis:

- **Tags sind endgültig.** Die Versionsauflösung wählt den
  *niedrigsten* Tag, der einen Bereich erfüllt — ein kaputtes
  `v1.0.0`, das stehen bleibt, würde für immer gewählt. Ein Fehler
  heißt: neuer Tag *und* den kaputten löschen (solange ihn niemand
  gelockt hat) — nie am selben Tag neu taggen.
- **Geschwister-Skills innerhalb derselben Quelle referenzieren**
  (ein `uses`-Link auf `git+…#skills/<anderer>@^1.0`), damit ein
  Bundle auflöst, egal von wo es konsumiert wird.

Vor dem Pushen validieren:

```sh
speccify check    # jedes Bundle: Frontmatter, Specs, Beispiele
```

## 3. Den Kreislauf beweisen

Der Abnahmetest für dein Repo ist der Import, den du schon kennst:
In einem leeren Scratch-Ordner eines deiner Bundles per
`git+…#skills/<name>`-Id `add`en, expandieren, und zusehen, wie
normale Skills und Tool-Verträge unter `.agent/` erscheinen — genau
die [Import-Erfahrung](/de/tutorial/importing-skills/), die 4Notice
hatte, jetzt aus *deinem* Repo serviert.

## 4. Einen wirklich gelernten Workflow exportieren

:::note[Stub — dieser Schritt ist am echten Projekt der nächste]
4Notices Kandidat steht fest: *„SwiftUI-App von null bis zum ersten
lauffähigen Build mit der Speccify-App"* — der Setup-Workflow aus dem
[Projekt-Setup-Kapitel](/de/tutorial/project-setup/), verallgemeinert
zu einer `SKILL.md`, mit seinen Lektionen (argv-ohne-Shell,
DerivedData vs. iCloud) als Pitfalls, plus Tool-Specs, wo eine
Prüfung mechanisch sein kann. Sobald dieser Export gelaufen ist,
wird dieser Abschnitt das durchgerechnete Beispiel: was sich
verallgemeinert hat, was projektspezifisch blieb, und wie der Skill
im nächsten Projekt ankam.
:::

Die Form des Zugs ist aus dem Import-Kapitel rückwärts schon klar:
Projektspezifisches in einen `## In this project`-artigen Schluss
abstreifen (es bleibt zurück), teuer Gelerntes zu `Pitfalls` machen,
jedem Schritt eine `Verify:`-Zeile geben, und Tools einen Vertrag mit
Beispielen — denn dein nächstes Projekt wird dem
[Check](/de/speccify/evaluate/) vertrauen, nicht deinem Gedächtnis.
