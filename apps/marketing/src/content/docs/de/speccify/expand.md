---
title: Expand
description: Aus einem Quell-Skill werden normale Projektdateien — und ein Herkunftsnachweis, der sich alles merkt.
sidebar:
  order: 2
---

**Expand** macht aus einem Skill eines Quell-Repos einen oder mehrere
normale Skills unter `.agent/skills/`, plus Tool-Verträge unter
`.agent/tools/`. `speccify expand <skill>` rechnet den
Abhängigkeitsbaum aus, legt Verzeichnisse und `TOOL.md`-Kopien an,
streift die Speccify-Metadaten ab, schreibt den Herkunftsnachweis —
und übergibt dem Agenten eine Aufgabenliste: *„2 Skills normalisiert,
3 Tools für macos zu implementieren, 2 Platzhalter zu füllen."*

Was mit dem Inhalt passiert:

- **Referenzen werden aufgelöst.** Ein per `uses` verwiesener Skill
  wird selbst zum normalen Skill nebenan; der Verweis im Body wird
  ein gewöhnlicher relativer Link.
- **Metadaten werden abgestreift.** Kein `speccify.*`-Frontmatter
  überlebt im Projekt — ein Projekt-Skill sieht aus wie ein von Hand
  geschriebener.
- **Platzhalter werden konkret** (Bundle-Id, Pfade, Identitäten,
  Ports), und Projektspezifisches kommt als `## In this
  project`-Abschnitt *hinzu* — der Upstream-Body bleibt unberührt,
  sodass ein späteres Re-Expand ein Merge ist, kein Umschreiben.
- **Tool-Verträge werden kopiert** nach
  `.agent/tools/<name>/TOOL.md`, damit der Vertrag dort liegt, wo die
  Implementierung entsteht. Tools sind projektweit: Zwei Skills, die
  dasselbe Tool brauchen, teilen eine Implementierung.

## Der Herkunftsnachweis

Die Herkunft liegt nicht im Skill — sie liegt in
`.agent/speccify/expansions.yaml`, geschrieben von `speccify expand`.
Aus dem Speccify-App-Projekt, wörtlich:

```yaml
schema_version: 1
skills:
  release-checks:
    source: git+https://github.com/mhennemeyer/speccify-first-test#skills/release-checks
    version: 1.0.0
    bundle_sha256: sha256:9692ba527af7c8a12ec94a56cd925a1609f97965bba1959da2408307791fe425
    expanded: '2026-08-23'
    requested: true
    tools:
    - check-entitlements
    - check-plist-keys
    - orphan-strings
tools:
  check-plist-keys:
    from:
    - release-checks
    spec_sha256: 8dc9cae189f6ced17c7c238de90ca3ac26eca36ec49f16d1211ea641d4f159dd
    platforms:
      macos:
        file: macos.py
        status: verified
        checked: '2026-08-23'
```

Der Nachweis beantwortet drei Fragen, die die Dateien allein nicht
können: *Woher kam das* (Quelle, Version, Inhalts-Hash), *welche
Tools bringt es mit und in welchem Zustand* (`implemented` vs.
`verified`, je Plattform), und *ist Upstream weitergezogen* seit der
Expansion. Die Datei trägt aus gutem Grund eine Warnung im Kopf:
**Editiere die Skills, nicht diese Datei** — sie ist Buchhaltung,
und Speccify pflegt sie.

Mit den Dateien an Ort und Stelle und der Aufgabenliste in der Hand
geht es weiter zu [Execute](/de/speccify/execute/).
