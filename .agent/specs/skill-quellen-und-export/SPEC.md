---
station: Doing
order: 10
created: 2026-09-09
---
# Plan: Skill-Quellen und Export — beliebige Repos, pro Projekt und global

> **BO (2026-09-09):** Multi-Source/Export-Repos: beliebige Skill-Repos
> anbinden, Skills importieren **und exportieren**. Auch auf Projektbasis
> (ITSD → GitLab; eigene Projekte → privates GitHub; Speccify → öffentliches
> GitHub neben speccify). Trotzdem global im Dashboard, weil die meisten
> erst einmal nur eins haben. Und Skills entwickeln, die projektspezifische
> Skills von projektspezifischen Infos bereinigen und als allgemeinen Skill
> in ein Repo exportieren.

## Ist-Stand (erhoben 2026-09-09)

* **Core (Python):** Ein Projekt-Manifest `speccify.yaml` hat *eine*
  lokale Bibliothek (`library.path`) und Abhängigkeiten mit Ids
  `@scope/name` (lokale Bibliothek, Version aus `metadata.speccify.version`)
  oder `git+<url>#<pfad>` (Git-Quelle: Bare-Clone-Cache unter
  `~/.cache/speccify/git/`, **Tags als Versionen** `<pfad>/vX.Y.Z`, System-
  `git` mit `GIT_TERMINAL_PROMPT=0` — privates GitLab/GitHub läuft über die
  vorhandenen Credentials). Lockfile pinnt Commit + Bundle-Hash;
  `expansions.yaml` merkt `source` je Skill.
* **App (Rust/React):** `skill_library` = **ein** lokaler Pfad im Dashboard,
  `speccify.sources` = lokale Pfade je Projekt (`.agent/settings.json`).
  Der Skill-Browser (`skill_sources.rs`) liest rekursiv `SKILL.md` aus
  einem Ordner, Ordner = Kategorie; Import tippt `speccify add <id>
  --library <ordner> && speccify expand …` ins Agent-Terminal.
  **Git-URLs kennt die App nicht.**
* **Export:** nur als Handanleitung im Speccify-Skill (§ 5 „Give back what
  was general": Text generalisieren, `## In this project` streichen,
  `TOOL.md` mitnehmen, Implementierung als `reference.<ext>`, `speccify
  check`, taggen). Kein Kommando, keine UI. Die Trennlinie ist mechanisch:
  alles über `## In this project` ist Upstream und wird beim Re-Expand
  ersetzt, der Abschnitt selbst bleibt.

## Entscheidungen (BO-Delegation 2026-09-09: „leg direkt los")

* **D1 — Git-Repos als verwaltete Checkouts, nicht als Tag-Quellen.** Die
  App klont jede Git-Quelle einmal nach `~/.speccify/sources/<slug>/`
  (System-`git`, `pull --ff-only` beim Aktualisieren) und behandelt den
  Checkout wie eine lokale Bibliothek: Ids und Versionen kommen aus den
  `SKILL.md`-Metadaten, **keine Tags nötig**. Das passt zum Alltag
  (privates Repo, schnelle Iteration, Export per Commit + Push). Die
  Tag-Quellen des Core (`git+…`, reproduzierbar gepinnt) bleiben für den
  CLI-/Team-Weg erhalten; die App zeigt beide.
* **D2 — Eine Quelle ist `{name, location, kind}`**: `location` ist Git-URL
  (https oder ssh) oder Ordner; `kind` wird erkannt. Global in
  `~/.speccify/settings.json` als `skill_sources: [...]`
  (`skill_library` wird beim ersten Lesen zum ersten Eintrag migriert),
  pro Projekt in `.agent/settings.json` → `speccify.sources` (Strings
  bleiben gültig: Pfad oder URL). Wirksam im Projekt: Projekt-Quellen,
  dann globale.
* **D3 — Herkunft ist die URL, nicht der Checkout-Pfad.** Beim Import aus
  einer Git-Quelle schreibt `expand` die URL nach `expansions.yaml`
  (`source`), damit ein Kollege dieselbe Quelle auflöst; der Checkout-Pfad
  ist Cache.
* **D4 — Export als CLI-Kommando + App-Knopf, Commit durch App oder
  Agent.** `speccify export <skill> --to <quelle> [--category <ordner>]`
  schreibt in den Checkout: `SKILL.md` ohne `## In this project`, mit
  `metadata.speccify.version`/`scope`, `tools/<name>/TOOL.md` und
  Implementierungen als `reference.<ext>`; danach `speccify check` auf dem
  Ziel und ein **Generalisierungs-Bericht** (Verdachtsstellen: absolute
  Pfade, Domains, Bundle-Ids, Ports, Personen). Committen/Pushen macht der
  Git-Tab-Mechanismus der App im Quell-Checkout — oder der Agent, dem der
  Skill den Ablauf vorgibt. Kein Auto-Push.
* **D5 — Zugang über System-git.** Kein eigener Token-Speicher: HTTPS über
  den Credential-Helper (macOS Keychain, Windows Credential Manager,
  GitLab-Token als Passwort), SSH über den Agent. Scheitert ein Klon,
  zeigt die App die Git-Meldung und den Hinweis, wie man sich anmeldet.

## Meilensteine

**Q1 — Quellen-Modell und verwaltete Checkouts (Rust + Settings).**
`sources_cmd.rs`: `sources_list(project?)` (global + Projekt, mit Status:
Ordner/geklont/fehlt/Fehler, letzter Pull), `source_add(scope, location,
name?)` (Git → klonen, Ordner → prüfen), `source_remove`,
`source_refresh` (pull --ff-only), `source_path` (Checkout). Settings-
Migration `skill_library` → `skill_sources[0]`. Skill-Browser liest aus
dem Checkout. *Fertig heißt:* Tests für Slug/Erkennung/Migration, ein
echter Klon eines öffentlichen Repos im Test-Temp, Browser zeigt Skills
aus einer Git-Quelle. **Rust-Änderung → BO-App startet neu; die
uv-Sidecar-Umbenennung (`speccify-uv`, Linux-deb-Konflikt) kommt in
derselben Runde mit.**

**Q2 — UI.** Dashboard *Bibliothek*: Liste der globalen Quellen mit
Hinzufügen (URL oder Ordner), Entfernen, Aktualisieren, Status; die
Settings-Zeile „Skill-Quelle (Default)" geht darin auf. Projektfenster
Skills-Tab, Modus „Quellen durchsuchen": Auswahl über alle wirksamen
Quellen mit Badge *global*/*Projekt*, „+ Quelle" nimmt URL oder Ordner,
Aktualisieren-Knopf, Import wie bisher (Kommando ins Terminal, mit
Checkout als `--library`). Leerzustand erklärt beides.

**Q3 — Export.** Core `speccify export` (siehe D4) mit Tests
(Abschnitt streichen, Metadaten setzen, Tools mitnehmen, Bericht);
App: Inspektor eines Projekt-Skills bekommt *Exportieren…* (Quelle +
Kategorie wählen → Kommando ins Terminal); der Git-Tab kann den Quell-
Checkout als zweites Repo öffnen (Commit + Push dort).

**Q4 — Der Generalisierungs-Skill.** Speccify-Skill § 5 auf das Kommando
umstellen und eine Checkliste ergänzen (Platzhalter `<wie-hier>`,
Geheimnisse, Pfade, Identitäten, Beispiele als Vertrag); eigener Abschnitt
„Skill aus dem Projekt zurückgeben" mit dem Bericht als Startpunkt. Eval:
ein AVC-Skill einmal durch den Weg schicken.

**Q5 — Herkunft und Drift.** `expand` schreibt die Quell-URL (D3);
`speccify verify` meldet, wenn der Checkout hinter der Herkunft liegt;
Skills-Tab zeigt „neuere Version in der Quelle".

## Nicht in diesem Plan

Ein zentrales Skill-Verzeichnis (der Index-Mechanismus des Core bleibt wie
er ist), Token-Verwaltung in der App, automatisches Pushen, Konfliktlösung
bei divergierenden Checkouts (dann Meldung + Git-Tab).

## Tasks

- [x] Q1 Quellen-Modell und verwaltete Checkouts (sources_cmd.rs)
- [x] Q2 UI: Bibliothek im Dashboard, „+ Quelle" im Skills-Tab
- [x] Q3 `speccify export` + Inspektor-Knopf „Exportieren…"
- [x] Q4 Speccify-Skill §5 auf das Kommando, Eval an AVC-Skills (project-path, skill-ref)
- [x] Q5 Manifest `sources:`, `add --source`, Lockfile-Herkunft
- [ ] Anzeige „neuere Version in der Quelle" im Skills-Tab (braucht `speccify verify --json`)

## Stand bei der Migration (2026-09-09)

Q1 + Q2 geliefert 2026-09-09 (d6982ae); Q3 Export (CLI `speccify export`, Inspektor-Knopf) + Q4 Skill-Text geliefert 2026-09-09; Eval an AVC-Skills 2026-09-09 (extract-service: erster Bericht leer → Heuristiken project-path + skill-ref ergänzt, jetzt 20 echte Treffer); Q5 Kern geliefert 2026-09-09 (Manifest `sources:`, `add --source`, Lockfile `resolved_via` = Quelle, Drift über `verify` nach Aktualisieren) — offen nur noch die Anzeige „neuere Version in der Quelle" im Skills-Tab
