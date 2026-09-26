---
station: Backlog
order: 71
created: 2026-09-25
needs_human: true
ready: false
open_question: Q1
modules: ci, website, release, docs
---
# Umzug ins itsd-GitLab: eigenes Produkt statt Open Source

## Why

Speccify wird ein eigenes Produkt und nicht mehr offen weiterentwickelt
(Nutzerentscheidung 2026-09-25; es gab keine externen Beteiligten). Quelle,
Spec-Register, CI, Releases und Website hängen heute vollständig an GitHub
(`mhennemeyer/speccify`, öffentlich, MIT) und müssen ins itsd-GitLab und auf
eigene Infrastruktur.

## What

Bestandsaufnahme 2026-09-25, woran das Repo nach außen hängt:

- **Quelle**: GitHub `mhennemeyer/speccify` (öffentlich, 4 Sterne, 0 Forks,
  1 Beobachter), Standardbranch `main`; Branch `master` trägt ein fremdes
  Projekt von 2009 („A minimal RSpec clone“, zwei fremde Sterne). Spec-Register
  ist der Branch `specs` desselben Repos (Worktree `.agent/specs`).
  `speccify-qa` ist ein zweites öffentliches Repo.
- **CI** (`.github/workflows`, 1269 Zeilen, 5 Workflows): `ci.yml` (smoke,
  web-backend, rust, desktop-windows auf `windows-latest`, desktop-linux,
  desktop-frontend), `release.yml` (macOS-Build mit Signatur und Notarisierung
  auf `macos-14`, Windows, Linux x64 und arm64, DMG-Prüfung, Update-Manifest),
  `pages.yml` (Website nach GitHub Pages), `docs.yml`, `linux-bundle.yml`.
  GitHub-Actions ohne GitLab-Gegenstück: `tauri-apps/tauri-action`,
  `upload-pages-artifact`/`deploy-pages`, `setup-uv`, `rust-cache`.
- **Runner**: itsd-GitLab hat sichtbar nur Docker-Runner (Linux). macOS-Build,
  Signatur, Notarisierung und Windows-Build brauchen eigene Runner.
- **Secrets** (7, GitHub): Apple-Zertifikat und -Passwort, Signing-Identity,
  Apple-ID/-Passwort/-Team für Notarisierung, Tauri-Updater-Schlüssel.
- **Releases/Updater**: Assets und `latest.json` liegen in GitHub Releases
  (v0.8.2 … v0.8.6); die App prüft
  `https://github.com/mhennemeyer/speccify/releases/latest/download/latest.json`.
  Wird das Repo privat, verliert jede installierte 0.8.x still ihre Updates.
- **Website**: `speccify.io` ist GitHub Pages (DNS A-Records auf GitHub, CNAME
  `mhennemeyer.github.io`), gebaut von `pages.yml` aus `apps/marketing` und
  `docs/`. Download-Seite liest die GitHub-Releases-API und nennt
  `git clone https://github.com/…`. 50 Fundstellen `github.com/mhennemeyer`
  in Site, Doku, Skripten, Tests, `tauri.conf.json`, `Cargo.toml`.
- **Lizenz**: MIT in LICENSE und allen Manifesten, dazu CONTRIBUTING und
  CODE_OF_CONDUCT. Veröffentlichte Versionen 0.7.0–0.8.6 bleiben unter MIT
  (praktisch ohne Empfänger). Kein Paket auf PyPI/npm/crates.io von uns
  (`speccify` auf PyPI gehört einem Dritten).

Umfang des Umzugs:

1. GitLab-Projekt anlegen, Historie mit allen Branches (`main`, `specs`,
   `master`) und Tags übertragen; `speccify-qa` ebenso; Remotes, Register-
   Worktree, Playbooks/Skills (`release`, `local-app`) und `Cargo.toml`
   `repository` umstellen.
2. `.gitlab-ci.yml` mit denselben Prüfungen wie `ci.yml`; Release-Pipeline
   (Tag → signierte Bundles, Update-Manifest) auf eigenen Runnern; Secrets als
   maskierte, geschützte CI-Variablen.
3. Update-Endpunkt und Download-Host unabhängig von GitHub (Vorschlag:
   `https://speccify.io/releases/latest.json` und Assets auf eigener
   Ablage); `tauri.conf.json`, `build_update_manifest.py`, Release-Skill.
4. Website: Hosting weg von GitHub Pages, DNS umstellen, GitHub-Links und
   Klon-Anleitungen ersetzen oder entfernen.
5. Lizenz und Community-Dateien durch proprietäre Hinweise ersetzen;
   Manifeste (`license`), README.
6. GitHub-Repo nach erfolgreichem Umzug privat stellen oder löschen;
   installierte 0.8.x einmalig von Hand auf die erste GitLab-Version heben.

Nicht enthalten: neue Funktionen; Umbenennung des Produkts; App-Identifier
`io.speccify.desktop` bleibt (sonst verlieren Updates die Zuordnung).

## Acceptance

- Wenn ein Tag `vX.Y.Z` im GitLab gepusht wird, dann entstehen signierte und
  notarisierte macOS-Bundles, Windows- und Linux-Bundles sowie `latest.json`,
  und eine installierte App findet das Update am neuen Endpunkt.
- Wenn `main` im GitLab gepusht wird, dann laufen dieselben Prüfungen wie
  heute in `ci.yml`, und die Website wird am neuen Host veröffentlicht.
- Wenn `speccify.io` aufgerufen wird, dann kommt die Seite vom eigenen Host;
  keine Seite, kein Skript und keine App-Konfiguration verweist mehr auf
  GitHub.
- Wenn das GitHub-Repo privat oder gelöscht ist, dann funktionieren Register,
  Board, Release-Skill und lokale App unverändert.
- Wenn jemand das Repo öffnet, dann steht dort die proprietäre Lizenz, keine
  Einladung zu Beiträgen.

## Decisions

1. 2026-09-25: Zweischritt statt Sofortumzug (Nutzer). Brücke: Speccify bleibt
   vorerst auf GitHub, wird privat, Peter kommt als Mitarbeiter dazu; Releases
   und Updater bekommen einen von der Quelle unabhängigen Weg. Zielbild
   bleibt das itsd-GitLab, sobald dort Runner für macOS, Windows und Linux
   stehen — die braucht der itsdcloud-Desktop-Client (app-Spec 0115) ohnehin,
   Speccify bringt die fertige Release-Pipeline als Vorlage mit.
2. 2026-09-26: Website auf Netlify statt GitHub Pages (Recherche im
   Research-Ordner, „2026-09-25 Netlify statt GitHub Pages für speccify.io“).
   Grund: unabhängig vom Quell-Host, Redirects für stabile Download- und
   Updater-Adressen unter `speccify.io/download/…`, kein GitHub Pro nötig.
   Bestehendes Netlify-Konto (Personal-Plan, 1000 Credits/Monat, ein
   Mitglied); Deploy per CLI aus der CI, nicht per Git-Anbindung (die gäbe es
   für ein selbst gehostetes GitLab nur im Enterprise-Plan).
3. 2026-09-26: Download-Pfad `/download/`, nicht `/releases/`, weil unter
   `/releases/<x-y-z>/` die Release-Notes liegen.

## Tasks

Brücke (GitHub privat):

- [x] Netlify-Site `speccify` angelegt, erster Deploy, Redirects/Header,
      `pages.yml` deployt zusätzlich nach Netlify (Job überspringt sich ohne Token).
- [ ] `NETLIFY_AUTH_TOKEN` als GitHub-Secret (Token legt der Nutzer an).
- [ ] DNS bei domainfactory umstellen, Domain in Netlify verifiziert, Pages-Job
      und `public/CNAME` entfernen.
- [ ] Öffentliches Repo `speccify-releases`, Release-Workflow veröffentlicht
      dorthin, `_redirects` und Updater-Endpunkt (`speccify.io/download/latest.json`)
      darauf, Download-Seite ohne GitHub-API und ohne `git clone`.
- [ ] Windows-CI nur bei Pull Requests und Tags; arm64-Linux-Job für privates
      Repo klären.
- [ ] Lizenz, README, Community-Dateien; 2009er `master` in eigenes
      öffentliches Repo abzweigen.
- [ ] Peter einladen, `speccify` und `speccify-qa` privat stellen, installierte
      Apps einmal von Hand heben.

Zielbild (GitLab), sobald die Runner stehen:

- [ ] Fragen Q1–Q4 klären und Entscheidungen festhalten.
- [ ] GitLab-Projekt(e) anlegen, Historie und Branches übertragen, Remotes
      und Register umstellen (App zu dem Zeitpunkt beendet).
- [ ] `.gitlab-ci.yml` (Prüfungen) und Runner für macOS/Windows einrichten.
- [ ] Release-Pipeline, Secrets, Update-Endpunkt, Download-Host.
- [ ] Website-Hosting und DNS, GitHub-Verweise ersetzen.
- [ ] Lizenz, README, Community-Dateien.
- [ ] Erster GitLab-Release, installierte Apps heben, GitHub-Repo privat/löschen.

## Verification

Noch nichts geprüft.

## Questions

### Q1 · open · 2026-09-25T10:30:00Z
Wohin genau im itsd-GitLab: in die Gruppe `private-ai` neben `app`/`portal`/
`infra` oder in eine eigene Gruppe (z. B. `speccify`)? Soll `speccify-qa` als
eigenes Projekt daneben umziehen? Wer soll Maintainer sein (Du, Peter)?

### Q2 · open · 2026-09-25T10:30:00Z
Womit werden macOS- und Windows-Releases gebaut? Optionen: (a) eigene
GitLab-Runner: ein Mac (Dein Rechner, Peters oder ein Mac mini) für
Signatur/Notarisierung und eine Windows-VM (Parallels) — vollständig bei itsd;
(b) übergangsweise ein privates GitHub-Repo nur als Build-Spiegel (macOS-
Minuten kosten das Zehnfache, für interne Releases tragbar); (c) Releases
vorerst von Hand mit dem `release`-Skill vom Mac aus. Empfehlung: (a), bis
dahin (c).

### Q3 · open · 2026-09-25T10:30:00Z
Website: Bleibt `speccify.io` als öffentliche Produktseite bestehen? Wenn ja,
Hosting auf itsd-Infrastruktur (statischer Container hinter Traefik, DNS
umstellen) oder GitLab Pages, falls die Instanz es anbietet? Wenn nein, welche
Seite ersetzt sie (Download-Links für interne Nutzer)?

### Q4 · open · 2026-09-25T10:30:00Z
Lizenz und Urheber: Welcher proprietäre Lizenztext, und steht künftig itsd
oder Du als Rechteinhaber in LICENSE, Manifesten und Bundle? Soll das
GitHub-Repo privat werden (Historie und der 2009er `master` bleiben Dir) oder
gelöscht werden?
