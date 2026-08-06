---
title: "Git-Repos als Spec-Quelle (Phase P5)"
description: "Specs werden wie Go-Module oder SwiftPM-Pakete geteilt: **die Repo-URL ist die Identität, Tags sind die Versionen**. Es gibt keine zentrale Instanz, die Namen vergibt, kein Login, kein Publish-Upload — Veröffentlichen heißt `git tag` +"
---

<!-- AUTOGENERIERT aus docs/ via scripts/sync_docs_to_site.py — nicht von Hand editieren. -->

Specs werden wie Go-Module oder SwiftPM-Pakete geteilt: **die Repo-URL ist die
Identität, Tags sind die Versionen**. Es gibt keine zentrale Instanz, die Namen
vergibt, kein Login, kein Publish-Upload — Veröffentlichen heißt `git tag` +
`git push`.

## Eine Git-Quelle referenzieren

```yaml
# speccify.yaml
schema_version: 2
targets: [react]
dependencies:
  "git+https://github.com/acme/rating-stars": "^1.2"       # Spec im Repo-Root
  "git+https://github.com/acme/kit#specs/button": "^0.1"   # Spec im Unterordner
```

Dasselbe geht in `uses:` und `composition.uses:` einer Spec.

| Form | Erwartete Datei | Erwartete Tags |
|---|---|---|
| `git+<url>` | `spec.speccify.yaml` im Repo-Root | `v1.2.0` |
| `git+<url>#<pfad>` | `<pfad>/spec.speccify.yaml` | `<pfad>/v1.2.0` |

Damit kann ein Monorepo beliebig viele Specs unabhängig versionieren; welche
Tags zu welcher Spec gehören, ist mechanisch aus der Id ableitbar.

Die Spec behält ihren eigenen Namen (`id: "@acme/button"`): **danach heißen die
generierten Dateien**. Die Id im Manifest sagt, *woher* sie kommt — die Herkunft
hält das Lockfile fest, nicht der Dateiname.

## Reproduzierbarkeit

`speccify lock` schreibt neben Version und Spec-Hash den **Commit hinter dem
Tag** (Lockfile v4, Feld `source_commit`):

```yaml
specs:
  - id: git+https://github.com/acme/rating-stars
    version: 1.2.0
    sha256: sha256:…
    resolved_via: git
    source_commit: 9f1c0b1c1b2a4e7f5d3c8a90b1e2f3a4c5d6e7f8
```

Ein umgehängter Tag ändert damit nachweisbar den Lockfile-Diff. `verify` prüft
weiterhin Tag → Spec-Bytes → Output-Hashes; der Commit ist der zusätzliche
Anker. Signierte Tags sind ein späterer, additiver Schritt (der
`signature`-Block im Lockfile ist dafür reserviert).

## Cache und Offline

Pro Repo legt Speccify einen **Bare-Clone** unter `~/.cache/speccify/git/` an
(Override: `SPECCIFY_GIT_CACHE`). Tags kommen per `fetch --depth 1`, die
Spec-Bytes per `git cat-file blob <tag>:<pfad>` — es gibt keinen Working Tree
und kein Checkout.

Nach dem ersten Auflösen ist alles offline reproduzierbar: `pull --offline` und
`verify --offline` lesen ausschließlich lokale Refs. Fehlt der Cache, bricht der
Lauf mit einem Hinweis ab, statt heimlich ins Netz zu gehen. `git` läuft dabei
immer mit `GIT_TERMINAL_PROMPT=0` — ein privates Repo scheitert mit einer
Fehlermeldung statt in einem Passwort-Prompt zu hängen.

## Zusammenspiel mit der lokalen Registry

Beide Quellen laufen nebeneinander: jede Registry sagt über `serves`, welche
Ids sie bedient (`@scope/name` → lokale Registry, `git+…` → Git). Bestehende
Projekte verhalten sich unverändert; ein Projekt darf beide Formen mischen.

Der Dependency-Confusion-Schutz aus Phase 2 (ein `@scope` gehört zu genau einer
Registry) gilt weiter für scoped Ids. Git-Ids sind host-qualifiziert und damit
konstruktiv eindeutig — dort ist die Id ihr eigener Scope.

## Discovery: Specs finden

Es gibt keinen zentralen Suchdienst. Ein **Index** ist ein Git-Repo (oder ein
lokales Verzeichnis) mit einer Datei pro Spec-Repo — Vorbild: Homebrew-Taps,
Scoop-Buckets:

```
<index-repo>/entries/<name>.yaml
```

```yaml
schema_version: 1
source: git+https://github.com/acme/rating-stars
title: Rating Stars
summary: Sternebewertung mit halben Sternen.
kind: ui-component
keywords: [rating, stars]
license: MIT
```

Eine Datei pro Eintrag ist Absicht: ein PR fasst genau eine Datei an, es gibt
keine Merge-Konflikte in einer wachsenden Sammelliste, und CI validiert jeden
Eintrag einzeln (Schema: [`schema/index-entry.schema.json`](../schema/index-entry.schema.json)).

Der Index sagt **nur, wo eine Spec liegt** — nie, welche Versionen es gibt.
Versionen sind Tags und damit immer aktuell; ein Index kann nicht veralten.

```bash
speccify search rating                                   # Quellen s. u.
speccify search --index git+https://github.com/acme/spec-index rating
speccify search --json rating                            # für Agents/Skripte
speccify search --offline rating                         # nur der lokale Cache
```

Quellen-Reihenfolge: `--index` (mehrfach) > `SPECCIFY_INDEX` (komma-getrennt,
**nicht** doppelpunkt-getrennt — der steckt in jeder Git-URL) > `./index`.
Mehrere Indizes werden zusammengeführt; bei derselben Quelle gewinnt die erste
Nennung. Git-Indizes liegen im selben Bare-Clone-Cache wie Spec-Quellen.

Vorlage und Beitrags-Ablauf: [`index/README.md`](../index/README.md).

## Alle Wege, nicht nur die CLI

| Weg | Git-Quellen | Discovery |
|---|---|---|
| CLI | `lock`/`pull`/`verify` gegen `git+…`, `--offline` nutzt nur den Cache | `speccify search` |
| MCP | dieselben Tools (`lock`/`pull`/`verify`), Registry-Fassade inklusive | Tool `search` |
| Web/Composer | Validierung, Mock-Closure und `speccify build` lösen Git-Kinder auf; die Palette hat eine Index-Suche | `GET /api/v1/index?q=` |

Möglich macht das eine **Registry-Fassade** (`MultiRegistry`): der Resolver
nimmt von sich aus eine Liste, alles andere (Kompositions-Auflösung, Mock- und
App-Codegen) erwartet genau eine Registry. Die Fassade verteilt jede Anfrage an
die erste Registry, die die Id bedient — Git-Quellen kommen damit überall ohne
Sonderfall an. Eine unerreichbare Git-Quelle ist im Composer ein
Validierungs-Befund, kein Absturz.

```bash
# Kompositions-Kind direkt aus einem Repo — Mock rendert sofort
curl -s -X POST localhost:8000/api/v1/mock/draft -H 'content-type: application/json' \
  -d '{"spec_yaml": "… composition: {uses: {btn: git+https://host/repo@^0.1}, …}"}' | jq '.files | keys'
```

## Grenzen (Stand P5.5)

- Index-Treffer lassen sich als Kind einfügen, aber nicht „öffnen" (im Editor
  bearbeiten) — dafür müsste der Composer in ein fremdes Repo schreiben.
- Der Index dieses Repos ist noch leer: Platzhalter-URLs wären tote Links,
  gesät wird zum OSS-Launch (P6).
- Nur `https://`- und `file://`-Remotes; SSH-Refs sind bewusst noch nicht
  freigeschaltet (Credential-Handling).
- Tags müssen exaktes Semver tragen (`v1.2.0`), keine Pre-Releases.

## Cross-Referenzen

- Roadmap & Entscheidungen D16–D19: [`.agent/plans/archive/pivot-open-source-git-composer.md`](../.agent/plans/archive/pivot-open-source-git-composer.md)
- Lockfile-Format: [`schema/lockfile.schema.json`](../schema/lockfile.schema.json)
- Lokaler Gesamt-Workflow: [`local-dev-e2e.md`](./local-dev-e2e.md)
