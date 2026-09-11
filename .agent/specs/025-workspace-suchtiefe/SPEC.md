---
station: Doing
order: 8
created: 2026-09-11
needs_human: true
ready: false
open_question: Q1
parent: 015-workspace-projekterkennung
---
# Workspace-Erkennung für tiefe Projektstrukturen

## Why

Beim ersten Team-Pilot itsdcloud werden app, infra und portal erkannt, aber
normale Quellcode- und Dokumentationsordner überschreiten die bisherige Grenze
von sechs Ebenen. Der pauschale Hinweis wirkt wie ein fehlgeschlagenes Öffnen.

## What

Standard-Suchtiefe auf 16 Ebenen erhöhen. Bei tatsächlich abgeschnittenen
Unterordnern konkrete relative Pfade nennen (höchstens acht Beispiele plus
Restanzahl). Bekannte Projekte bleiben nutzbar. Alle anderen Suchbudgets,
Symlink-Ausschlüsse, verschachtelte Repo-Erkennung und lokalen IDs erhalten.
Keine Projektdateien verändern, kein Team-Sync und kein automatisches Setup.

## Acceptance

- Eine itsdcloud-ähnliche Struktur mit drei Repos und zehn Verzeichnisebenen
  wird mit Standardlimits ohne Teilresultat oder Warnung erkannt.
- Repos unterhalb der früheren Sechs-Ebenen-Grenze werden weiterhin gefunden.
- Ein tatsächlicher Tiefenabbruch meldet konkrete übersprungene Pfade; auch
  gleichzeitig erreichte andere Budgets unterdrücken diesen Hinweis nicht.
- Erneute Erkennung entfernt alte Warnungen und erhält IDs, Namen und Gruppen.
- Die aktualisierte lokale App erkennt itsdcloud mit drei verfügbaren Repos
  ohne Warnung; bestehende Projektfenster werden nach Neustart wieder geöffnet.

## Decisions

- D1, 2026-09-11: Nutzer beauftragt unmittelbare Korrektur für den Team-Pilot.
  015 und 024 bleiben bereit zur menschlichen Abnahme; aktiver Schnitt ist 025.
- D2, 2026-09-11: Nicht pauschal innerhalb bekannter Repos aufhören oder Warnungen
  verbergen: Dort können weitere Repos liegen. Größere Tiefe bei unverändertem
  Eintrags-/Verzeichnis-/Zeitbudget; kein projektspezifischer Sonderfall.
- D3, 2026-09-11: Zwei native Start-Samples belegen zusätzlich eine Blockade
  im bestehenden synchronen `project_board → spec_dirs → read_dir` auf dem
  UI-Thread. Diesen einzelnen lesenden Command im selben Schnitt auf einen
  Hintergrundthread verschieben; Parser und Rückgabe bleiben unverändert.

## Tasks

- [x] Standardtiefe und begrenzte, konkrete Suchlimit-Hinweise implementieren.
- [x] Regressionen für tiefe Strukturen, echte Limits und Warnungsbereinigung.
- [x] (added) Belegte Board-Startblockade vom UI-Thread entkoppeln und
  Gleichheit der synchronen Lesehilfe und asynchronen Command-Rückgabe testen.
- [ ] Native App aktualisieren und itsdcloud lesend erneut erkennen.
- [x] Vertrag, Playbooks und Verifikationsstand aktualisieren.

## Verification

- `speccify search workspace`: kein Treffer; bestehender nativer Vertrag bleibt
  Grundlage. Skills: spec-next, speccify (Suche, keine Expansion erforderlich).
- `cargo test -p speccify-desktop --offline`: 84 bestanden, 3 ignoriert
  (zwei bestehende Tests plus der ausdrücklich manuelle lokale Smoke-Test).
  Neue Regressionen: zehn Ebenen, drei Repos, tiefer verschachteltes Repo,
  Leaf am Limit, tatsächlicher Abbruch, acht Pfadbeispiele/Restanzahl,
  gleichzeitiges Eintragslimit, IDs/Gruppen/Namen und Bereinigung alter Warnungen.
- Echter nativer Scanner, ohne App oder Store-/Projekt-Schreibzugriffe:
  `SPECCIFY_DISCOVERY_SMOKE_ROOT=/Users/mhennemeyer/WorkLocal/itsdcloud cargo test
  -p speccify-desktop --offline discovery_local_workspace_smoke -- --ignored --nocapture`:
  bestanden, app/infra/portal jeweils Git, drei Wurzeln, keine Warnung/Teilresultate,
  Laufzeit des Tests 0,03 s. Dies ist kein UI-Rescan; die gespeicherte Revision 1
  mit alter Warnung wurde nicht manuell verändert.
- Typecheck, `cargo fmt --all --check`, beide Workspace-UI-Suites und die fünf
  bestehenden Projektfenster-Suites grün. UI prüft jetzt auch verständliche
  Limit-Hinweise mit Pfad und das Entfernen nach vollständiger erneuter Erkennung.
- `app-screenshots`, Iteration 2, ok: acht Motive visuell geprüft, im zweiten
  Capture alle bytegleich zum Bestand. Erste Tools-Rasterabweichung verschwindet
  im Wiederholungslauf. Marketing-Build (93 Seiten), responsive Landing/Features
  bei 1440/390/320 px und ohne JavaScript grün; keine Veröffentlichung.
- Erster lokaler App-Build mit `./scripts/dev.sh --app --prepared --ui-port=18768`
  erfolgreich. Reguläres Beenden musste erst abschließen, danach griff der
  Neubau ohne Umgehung der Schutzprüfung. Dieser Build enthält die Suchkorrektur.
  Zwei Starts (58059, 59071) zeigen leere Fenster; Samples belegen jeweils
  `project_board → spec_dirs → read_dir → open` auf dem UI-Thread. Nur diese
  blockierten App-Prozesse per SIGTERM beendet, keine Systemdienste verändert.
- Zusätzliche Board-Entkopplung auf `spawn_blocking` implementiert und Rückgabe-
  Gleichheit im bestehenden Board-Test geprüft; kompletter Testlauf erneut grün.
  Diese zusätzliche Korrektur ist noch nicht in der gebündelten App: `tccd` PID
  665 hält deren Binärdatei offen, das Startscript verweigert den Neubau korrekt.
  Keine fehlende Datenschutzfreigabe nachgewiesen und keine Freigabe umgangen.
- Vorhandenen Suchkorrektur-Build erneut geöffnet (70212, Port 18768). Fenster
  sind noch nicht bedienbar bestätigt; native Abnahme/gespeicherter Rescan und
  finale Board-Startkorrektur bleiben offen. UI-Testserver 1421 wieder beendet,
  bestehende Website-Vorschau unverändert. Windows nicht nativ geprüft.

## Questions

### Q1 · open · 2026-09-11T07:41:03Z

Siehst Du einen macOS-Dialog zu Speccify oder nur leere App-Fenster? Die Erkennung
ist am echten itsdcloud-Ordner geprüft. Für den finalen App-Neubau und UI-Rescan
muss die vom macOS-Dienst offengehaltene App-Datei wieder frei sein. Ohne belegte
Ursache keine pauschale Datenschutzänderung verlangen; keine Systemdienste beenden.
