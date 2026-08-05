# Discovery-Index

Ein Index sagt, **wo** Specs liegen — nicht, welche Versionen es gibt.
Versionen sind Git-Tags und damit immer aktuell; ein Index kann nicht
veralten.

Vorbild sind Homebrew-Taps und Scoop-Buckets: ein Git-Repo, eine Datei pro
Spec-Repo, erweiterbar per Pull Request. Dieses Verzeichnis ist der Index des
Speccify-Repos selbst und dient zugleich als Vorlage für eigene Indizes.

## Format

Eine Datei pro Eintrag unter `entries/*.yaml` (der Dateiname ist frei, die
`source` ist der Schlüssel). Schema:
[`schema/index-entry.schema.json`](../schema/index-entry.schema.json).

```yaml
schema_version: 1
source: git+https://github.com/acme/rating-stars   # oder mit #pfad/im/repo
title: Rating Stars
summary: Sternebewertung mit halben Sternen und Tastaturbedienung.
kind: ui-component
keywords: [rating, stars, review]
homepage: https://github.com/acme/rating-stars
license: MIT
```

Warum eine Datei pro Eintrag: ein PR fasst genau eine Datei an, es gibt keine
Merge-Konflikte in einer wachsenden Sammelliste, und CI kann jeden Eintrag
einzeln validieren.

## Eintragen

1. Spec-Repo taggen (`v1.2.0`, bei Specs in Unterordnern `<pfad>/v1.2.0`).
2. `entries/<name>.yaml` nach obigem Schema anlegen.
3. Pull Request. CI validiert Schema und Eindeutigkeit der `source`
   (`core/tests/test_spec_index.py::test_repo_index_is_valid`).

## Benutzen

```bash
speccify search rating                       # Quellen: --index, SPECCIFY_INDEX, ./index
speccify search --index git+https://github.com/acme/spec-index rating
speccify search --json rating                # maschinenlesbar für Agents
```

Git-Indizes liegen im selben Bare-Clone-Cache wie Spec-Quellen und sind danach
mit `--offline` ohne Netz lesbar.

**Noch keine Einträge**: Das Ökosystem wird zum OSS-Launch (P6) gesät —
Platzhalter-URLs wären tote Links. Das Format, die Validierung und `speccify
search` stehen; eintragen kann man ab sofort.
