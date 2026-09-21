---
station: Backlog
order: 62
created: 2026-09-21
needs_human: true
---
# Spike: Agent-Terminal im Container, bedient aus dem Browser

## Why

BO 2026-09-21: Speccify soll verteilt und web-/cloudfähig werden; Ziel ist die
Integration in itsdcloud. Erster Schnitt: weiterhin bedient ein **Mensch** den
Agenten, mit seinem **eigenen** Claude- bzw. Codex-Konto — nur liegen Repo,
Agent und PTY in einem Docker-Container und das Terminal läuft im Browser.
KI-Mitarbeiter als Entwickler und unbeaufsichtigte Läufe sind zurückgestellt.

Die Recherche (`~/Desktop/Work/Agents-Research/2026-09-21 Speccify verteilt –
Container-Service, Browser-Client und itsdcloud-Mitarbeiter.md`) hält das für
machbar, stützt sich aber nur auf Code-Lektüre und Anbieter-Doku. Dieser Spike
beantwortet die Risikofragen praktisch, bevor Bestand umgebaut wird
(`bridge.ts`, Service-Crate, Server).

## What

Ein Wegwerf-Prototyp, getrennt vom Produkt:

- Docker-Image (Linux) mit Git, `claude`, `codex`, unprivilegiertem Nutzer,
  Arbeitsverzeichnis `/workspace` (Test-Repo) und Home als Volume.
- Kleiner Terminal-Server im Container: PTY (`portable-pty`, wie
  `terminal.rs`), WebSocket für Ein-/Ausgabe und Resize, ein statischer
  Bearer-Token. Der **Server** vergibt die Sitzungs-ID und hält die PTY
  unabhängig von der Verbindung; Replay-Puffer nur im Speicher.
- Minimale Browser-Seite mit xterm.js (kein Speccify-UI), die verbindet,
  wiederverbindet und den Puffer nachspielt.

Zu beantworten:

1. Anmeldung an der **unveränderten** Claude-Code-CLI im Container mit
   persönlichem Abo: URL im Browser-Terminal öffnen/kopieren, Code am Prompt
   einfügen. Überlebt der Login den Container-Neustart (Volume)?
2. Dasselbe für Codex mit `codex login --device-auth`.
3. Browser-Tab schließen und neu verbinden: dieselbe laufende Sitzung, Bildschirm
   per Replay wiederhergestellt — auch bei Vollbild-/Alternate-Screen-Ausgabe
   des Agenten. Reicht ein Byte-Ringpuffer, oder braucht es ein kopfloses
   Terminal mit Serialisierung?
4. Speccify-Eigenheiten über WebSocket: Bracketed-Paste-Übergabe
   (`handover.ts`), Shift+Enter als CSI-u, Resize, Kopieren/Einfügen über die
   Browser-Zwischenablage, anklickbare Links, OSC 9/777 und Bell.
5. Wiederaufnahme (`--session-id` / `--resume`, `codex resume`) nach
   Container-Neustart.
6. Was vom Login im Replay-Puffer landet (URL, Code, ggf. `setup-token`-Ausgabe)
   und wie man es heraushält.

Außerhalb: `bridge.ts`, Herauslösen eines Service-Crates, Speccify-UI im
Browser, Board/Dateien/Git über HTTP, Mehrbenutzerbetrieb, OIDC/Keycloak,
Einbettung in itsdcloud, unbeaufsichtigte Läufe, KI-Mitarbeiter, TLS/Reverse-Proxy,
Windows-/macOS-Container. Keine Änderung an `apps/desktop`, `crates/` oder `core/`.

## Acceptance

- Wenn der Container frisch gestartet ist und der Mensch `claude` im
  Browser-Terminal startet, dann kann er sich ohne Hilfsmittel außerhalb des
  Browsers mit seinem eigenen Konto anmelden, und `/status` zeigt das Abo.
- Wenn der Container danach neu gestartet wird, dann ist der Login noch gültig
  und `--resume <id>` setzt die vorige Sitzung fort.
- Wenn der Browser-Tab während einer laufenden Agent-Antwort geschlossen und
  nach mindestens 30 s neu geöffnet wird, dann läuft der Agent weiter und der
  Bildschirm ist ohne Darstellungsfehler wiederhergestellt; ein zweiter Auftrag
  wird dabei nicht ausgelöst.
- Wenn ein mehrzeiliger Auftrag per Bracketed Paste übergeben wird, dann
  erscheint er als ein Einfügeblock und wird erst mit Enter des Menschen gesendet.
- Wenn ohne oder mit falschem Token verbunden wird, dann lehnt der Server ab,
  bevor eine PTY entsteht.
- Wenn der Spike abgeschlossen ist, dann steht in `## Verification` je Frage
  1–6 ein Befund (geht / geht mit Einschränkung / geht nicht, mit Beleg) und
  eine Empfehlung, ob und womit die Stufen „bridge.ts“ und „Service-Crate“
  beginnen sollen.

## Decisions

1. 2026-09-21: Prototyp liegt unter `experiments/remote-terminal/`, außerhalb
   des Cargo-/pnpm-Workspace und außerhalb von Release und Website. Er ist
   Wegwerfcode; übernommen werden Befunde, nicht Dateien.
2. 2026-09-21: PTY + unveränderte CLI ist gesetzt, keine SDK-Chat-Oberfläche:
   Nur so ist die Anmeldung mit persönlichem Abo von den Anbieterbedingungen
   gedeckt (Quellen in der Recherche-Notiz, Nachtrag).
3. 2026-09-21: Der Spike-Server liest, kopiert oder setzt keine
   Anbieter-Zugangsdaten. Anmeldung ausschließlich durch den Ablauf der CLI.
4. 2026-09-21: Die Anmeldungen (Fragen 1, 2) führt der Mensch mit seinem
   eigenen Konto aus; der Agent bereitet vor und protokolliert das Ergebnis.
   Deshalb `needs_human: true`.

## Tasks

- [ ] Dockerfile + Startskript: Image, Nutzer, Volumes (`/workspace`, Home), Test-Repo.
- [ ] Terminal-Server: PTY, WebSocket, Token-Prüfung, serverseitige Sitzungs-ID, Ringpuffer.
- [ ] Browser-Seite: xterm.js, Verbinden/Wiederverbinden, Replay, Resize, Zwischenablage, Links.
- [ ] Frage 3: Replay mit Alternate Screen prüfen; bei Darstellungsfehlern kopfloses Terminal mit Serialisierung gegentesten.
- [ ] Frage 4: Bracketed Paste, Shift+Enter, OSC 9/777, Bell.
- [ ] Mensch: Claude-Login im Container, Neustart, `--resume` (Fragen 1, 5).
- [ ] Mensch: Codex-Login per `--device-auth`, Neustart, `codex resume` (Fragen 2, 5).
- [ ] Frage 6: Pufferinhalt nach Login sichten; Gegenmaßnahme vorschlagen.
- [ ] Befunde und Empfehlung in `## Verification`; Recherche-Notiz und Draft `speccify-web-app.md` um die Befunde ergänzen (Status bleibt `draft`).

## Verification

Noch nichts ausgeführt.

## Questions
