# Launch-Vorbereitung (P6)

Alles hier ist **vorbereitet, nicht ausgeführt**. Öffentliches Veröffentlichen
— Repo anlegen, pushen, posten — ist eine bewusste Entscheidung und bleibt beim
Maintainer. Diese Seite sammelt, was dafür fertig ist und was noch fehlt.

## Vor dem Launch: was grün sein muss

```bash
uv run pytest                                   # 523 Tests
uv run pytest -m app_build tests/test_app_build_smoke.py
uv run ruff check . && uv run ruff format --check .
uv run python scripts/gen_cli_docs.py --check   # CLI-Doku ohne Drift
uv run python scripts/sync_docs_to_site.py --check
pnpm run composer:e2e                           # 6 UI-Tests
pnpm --filter speccify-marketing build          # 29 Seiten
```

Dazu die zwei Dinge, die nur der Maintainer kann:

- **Signierte Mac-App**: Developer-ID-Zertifikat + App-Specific Password, dann
  `./scripts/release_macos.sh` (siehe [`release.md`](./release.md)). Ohne einen
  echten Lauf ist unbewiesen, dass Signatur und Notarisierung durchgehen.
- **Updater-Schlüssel**: `pnpm --filter speccify-desktop tauri signer generate
  -w ~/.speccify/updater.key`, Public Key nach
  `apps/desktop/src-tauri/tauri.conf.json`. Ohne Key bleibt der Updater bewusst
  inaktiv.

## Repo öffentlich machen

1. GitHub-Repo anlegen und pushen (bisher gibt es kein Remote).
2. `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `LICENSE` (MIT) sind da.
3. Doku-Site deployen (siehe [`deploy.md`](./deploy.md)); `PUBLIC_DOWNLOAD_URL`
   setzen, sonst zeigt `/download/` die Selbstbau-Anleitung statt eines toten
   Links.
4. Platzhalter ersetzen: In den Docs stehen `github.com/acme/...`-Beispiele —
   die dürfen als Beispiele bleiben, aber der Link auf
   `github.com/speccify/speccify` in `concepts/spec-format` muss auf das echte
   Repo zeigen.

## Ökosystem säen

Der Discovery-Index (`index/entries/`) ist **absichtlich leer**: Einträge auf
Repos, die es nicht gibt, wären tote Links. Zum Launch gehören ein bis drei
echte Spec-Repos, damit `speccify search` beim ersten Versuch etwas findet.

Vorschlag als Saatgut — die vorhandenen Referenz-Specs, je als eigenes Repo:

| Repo | Spec | Warum |
|---|---|---|
| `speccify/spec-button` | `registry-fixtures/org/button` | kleinster sinnvoller Baustein |
| `speccify/spec-text-input` | `registry-fixtures/org/text-input` | zeigt Events mit Payload |
| `speccify/spec-search-bar` | `registry-fixtures/org/search-bar` | Composite über die beiden anderen — beweist Komposition über Repo-Grenzen |

Pro Repo:

```bash
mkdir spec-button && cd spec-button && git init
cp <speccify>/registry-fixtures/org/button/0.1.0/spec.speccify.yaml .
git add . && git commit -m "button 0.1.0" && git tag v0.1.0
git push --follow-tags
```

Danach je eine Datei in `index/entries/` (Format:
[`index/README.md`](../index/README.md)), Commit, fertig — `speccify search`
findet sie sofort, und die CI validiert jeden Eintrag.

## Launch-Text (Entwurf)

**Titel (HN)**: *Speccify – Spezifikationen statt Code, geteilt über Git*

> Speccify beschreibt Software-Komponenten in einer versionierten
> `speccify.yaml`: API-Vertrag, Verhalten, Akzeptanzkriterien. Zwei Dinge
> machen das praktisch statt akademisch:
>
> **1. Jede Spec ist sofort lauffähig.** Aus dem API-Block entsteht
> deterministisch ein Mock — ohne LLM, ohne Netz, byte-identisch reproduzierbar.
> Man kann eine App komponieren und im Browser bedienen, bevor eine Zeile
> implementiert ist. Der visuelle Composer rendert genau diese Mocks, nicht
> Platzhalter-Grafiken: das ist der Unterschied zu den No-Code-Ansätzen, die an
> Code-Drift gescheitert sind — hier ist die Spec die Quelle, der Composer nur
> ein Editor darauf.
>
> **2. Geteilt wird über Git, nicht über ein Registry.** Wie bei Go-Modulen ist
> die Repo-URL die Identität, Tags sind die Versionen. Veröffentlichen heißt
> `git tag` + `git push`. Das Lockfile pinnt zusätzlich den Commit; nach dem
> ersten Auflösen läuft alles offline. Discovery über Index-Repos im
> Homebrew-Tap-Prinzip — eine Datei pro Spec-Repo, per PR erweiterbar.
>
> Die Implementierung generiert ein AI-Agent, aber reproduzierbar: Modell,
> Prompt-Version und Cache-Key stehen im Lockfile, CI läuft gegen einen
> eingecheckten Replay-Cache, und Conformance-Checks bauen den generierten Code
> gegen die echten Toolchains.
>
> Alles MIT, kein Hosted-Service, kein Account. CLI, MCP-Server (für
> Coding-Agents) und Web-API liefern byte-identische Ergebnisse.

**Kurzfassung (X/Mastodon)**:

> Spezifikationen statt Code: Aus einer `speccify.yaml` entsteht sofort ein
> lauffähiger Mock — komponier deine App, bevor du sie implementierst.
> Geteilt über Git wie Go-Module, Commit-gepinnt, alles MIT.

**Was ich beim Posten erwarten würde** (und wofür Antworten bereitliegen
sollten): „Warum kein npm/Registry?" → Dependency-Confusion und
Namens-Squatting entfallen mit host-qualifizierten Ids; „Ist das nicht nur
Codegen?" → nein, der Determinismus-Stack (Lockfile, Replay-Cache,
Conformance) ist der Kern; „Was, wenn das LLM Mist baut?" → Mock und
Implementierung erfüllen denselben Vertrag, Drift ist ein `verify`-Fehler.

## Danach

- Issue-Templates stehen (`.github/ISSUE_TEMPLATE/`).
- Erste Fremd-PRs werden vermutlich Index-Einträge sein — die CI-Validierung
  dafür läuft bereits (`core/tests/test_spec_index.py::test_repo_index_is_valid`).
- Offene Produkt-Themen, die sich gut als „good first issue" eignen: weitere
  Build-Targets (`speccify build --target swiftui`), SSH-Remotes für
  Git-Quellen, Pre-Release-Tags, Routen-Editor im Composer.
