# Git-Repos als Spec-Quelle (Phase P5)

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

## Grenzen (Stand P5.2)

- Discovery (`speccify search`, Index-Repo) folgt in P5.3.
- MCP-Tools, Web-Backend und Composer-Palette kennen Git-Quellen noch nicht
  (P5.4) — CLI-Pfad (`lock`/`pull`/`verify`) ist vollständig.
- Nur `https://`- und `file://`-Remotes; SSH-Refs sind bewusst noch nicht
  freigeschaltet (Credential-Handling).
- Tags müssen exaktes Semver tragen (`v1.2.0`), keine Pre-Releases.

## Cross-Referenzen

- Roadmap & Entscheidungen D16–D19: [`.agent/plans/pivot-open-source-git-composer.md`](../.agent/plans/pivot-open-source-git-composer.md)
- Lockfile-Format: [`schema/lockfile.schema.json`](../schema/lockfile.schema.json)
- Lokaler Gesamt-Workflow: [`local-dev-e2e.md`](./local-dev-e2e.md)
