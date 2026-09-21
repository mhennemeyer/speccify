---
station: Doing
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
5. 2026-09-21 (Spec-Prüfung vor dem Bau): Server in **Rust** mit `portable-pty`
   — dieselbe PTY-Schicht wie `terminal.rs`, damit die Befunde auf den späteren
   Server übertragbar sind. Eigenes Cargo-Paket mit leerem `[workspace]`, damit
   das Root-`Cargo.toml` unberührt bleibt.
6. 2026-09-21: Ausgabe als **binäre** WebSocket-Frames (rohe PTY-Bytes), Eingabe
   und Resize als JSON-Text. xterm.js setzt geteilte UTF-8-Folgen selbst
   zusammen; ob der `Utf8Chunker` damit entfällt, ist Teil des Befunds.
7. 2026-09-21: Frage 3 wird mit zwei umschaltbaren Replay-Arten beantwortet:
   Byte-Ringpuffer und Bildschirmzustand aus einem mitlaufenden Parser (Crate
   `vt100`). Ohne Anbieter-Login prüfbar mit Vollbildprogrammen (`vim`, `less`)
   und dem Anmeldebildschirm der CLI; die Prüfung mit laufender Agent-Antwort
   gehört zu den Menschen-Tasks.
8. 2026-09-21: Token im Spike als Bearer-Header (HTTP) bzw. Query-Parameter
   (WebSocket — Browser können dort keine Header setzen). Für das Produkt ist
   das ungeeignet (Token in Logs/History); die Alternative wird im Befund benannt.
9. 2026-09-21: Port 8791, auf dem Host nur an `127.0.0.1` veröffentlicht.
   CLIs per npm (`@anthropic-ai/claude-code`, `@openai/codex`) unverändert
   installiert; keine Zugangsdaten im Image.

## Tasks

- [x] Dockerfile + Startskript: Image, Nutzer, Volumes (`/workspace`, Home), Test-Repo.
- [x] Terminal-Server: PTY, WebSocket, Token-Prüfung, serverseitige Sitzungs-ID, Ringpuffer.
- [x] Browser-Seite: xterm.js, Verbinden/Wiederverbinden, Replay, Resize, Zwischenablage, Links.
- [x] Frage 3: Replay mit Alternate Screen prüfen; bei Darstellungsfehlern kopfloses Terminal mit Serialisierung gegentesten.
  Beide Arten gebaut und verglichen (`vi`, Claude-Startbildschirm, 4-KiB-Ring).
- [x] Frage 4: Bracketed Paste, Shift+Enter, OSC 9/777, Bell.
- [x] (added) Replay-Rahmen: Client verwirft Terminal-Antworten während des Abspielens.
- [x] (added) Resize nur bei echter Größenänderung an die PTY geben.
- [x] (added) OSC 52 → Browser-Zwischenablage, OSC-8-Links ohne `confirm()`.
- [x] (added) `LANG=C.UTF-8` im Image.
- [ ] Mensch: Claude-Login im Container, Neustart, `--resume` (Fragen 1, 5).
  Vorbereitet bis zur URL-Anzeige; Checkliste in `experiments/remote-terminal/README.md`.
- [ ] Mensch: Codex-Login per `--device-auth`, Neustart, `codex resume` (Fragen 2, 5).
  `codex login --device-auth` zeigt im Container URL und Einmal-Code; nicht abgeschlossen.
- [ ] Mensch: Tab während laufender Agent-Antwort ≥ 30 s schließen, neu verbinden (Abnahme 3).
  (added) Braucht einen angemeldeten Agenten; ohne Login mit Shell-Ausgabe geprüft.
- [ ] Frage 6: Pufferinhalt nach Login sichten; Gegenmaßnahme vorschlagen.
  Bis zur URL gesichtet, Gegenmaßnahmen unten; offen: ob der eingefügte Code im Puffer steht.
- [ ] Befunde und Empfehlung in `## Verification`; Recherche-Notiz und Draft `speccify-web-app.md` um die Befunde ergänzen (Status bleibt `draft`).
  Zwischenstand unten; Notiz und Draft nach den Menschen-Tasks.

## Verification

Zwischenstand 2026-09-21, Agent-Teil. Umgebung: colima/Docker 29.2.1 linux/arm64,
Image `node:22-bookworm-slim`, Claude Code 2.1.278, codex-cli 0.155.1, xterm.js 5.5,
Playwright (Chromium) gegen `http://localhost:8791`. `cargo fmt --check` und
`cargo clippy` für das Spike-Paket ohne Befund.

**Abnahme „Token“ — erfüllt.** `GET /api/sessions` ohne Token → 401; WebSocket-Upgrade
mit falschem Token → 401; danach 0 Shell-Prozesse im Container.

**Abnahme „Bracketed Paste“ — erfüllt (gegen bash/readline).** Der dreizeilige Auftrag
steht als ein Block am Prompt und wird nicht ausgeführt. Gegen den angemeldeten Agenten: Menschen-Task.

**Frage 3 — geht, aber nicht mit dem Byte-Ringpuffer allein.**

- Trennen während laufender Ausgabe, 4 s Pause, neu verbinden: `tick-1…16` je genau
  einmal, `fertig` vorhanden, Sitzung lief mit 0 Betrachtern weiter, keine zweite Sitzung.
- `vi` (Alternate Screen): beide Replay-Arten stellen `buffer.type = alternate` und den
  Inhalt her; `:q` führt sauber zurück.
- Claude-Startbildschirm: Bildschirmtext nach beiden Replay-Arten identisch zum
  Live-Bild; Screenshot `experiments/remote-terminal/claude-first-run-after-replay.png`.
- **Ringpuffer bricht, sobald vorne abgeschnitten wird:** Mit 4 KiB und 12 Pfeiltasten
  in Claudes Auswahlmenü (≈ 28 KB Ausgabe, ≈ 2,4 KB je Tastendruck) ist der Bildschirm
  nach dem Replay zerstört; der Bildschirmzustand aus dem mitlaufenden Parser bleibt
  korrekt. Claude zeichnet fortlaufend relativ neu, jede endliche Puffergröße läuft in
  einer langen Sitzung über.
- **Rohes Replay beantwortet alte Terminal-Abfragen erneut:** xterm schickt beim
  Abspielen `\e[?1;2c` (DA1) und bei Claude zusätzlich `\e[I` (Fokus) als *Eingabe* in
  das laufende Programm; an der Shell stand danach `1;2c` am Prompt. Behoben durch
  Replay-Rahmen (`{"type":"replay","bytes":N}` vor dem Schnappschuss, Client verwirft
  `onData` bis zum Schreib-Callback); nachgeprüft: Prompt sauber, Antworten verworfen.
- **Bildschirmzustand aus Crate `vt100` verliert:** normalen Bildschirm und Scrollback,
  wenn während Alternate Screen verbunden wird; Fokus-Melde-Modus (`?1004`, von Claude
  gesetzt; Bracketed Paste bleibt); OSC-8-Hyperlinks (Login-URL nach Replay nicht mehr
  klickbar, mit Ringpuffer weiterhin).
- Folgerung: Der Server braucht einen **vollwertigen kopflosen Emulator mit
  Serialisierung** (Bildschirm, Scrollback, Modi, Hyperlinks). Kandidaten:
  `xterm-headless` + Serialize-Addon (derselbe Emulator wie im Client, aber Node-Prozess),
  `alacritty_terminal`, oder `vt100` plus eigene Modus-/Link-Verfolgung. Der Replay-Rahmen
  bleibt in jedem Fall nötig.

**Frage 4 — geht.** Shift+Enter kommt als `^[[13;2u` an (`cat -v`); OSC 9, OSC 777 und
Bell erreichen den Client; Resize wirkt. Ein-/Ausgabe als binäre Frames: Umlaute, `€`
und Emoji korrekt, **`Utf8Chunker` entfällt** (xterm setzt geteilte Folgen selbst
zusammen). Nebenbefunde: ohne `LANG=C.UTF-8` gibt readline Umlaute im Echo oktal aus;
eine umbrechende Kopfzeile der Testseite änderte die Höhe um eine Zeile und erzeugte
je Verbinden zwei SIGWINCH — Server gibt Resize jetzt nur bei Änderung weiter (0 nach
drei Wiederverbindungen).

**Frage 1 — vorbereitet, Login selbst offen (Mensch).** Die unveränderte CLI zeigt im
Container alle drei Anmeldewege. Die Login-URL ist **hart auf fünf Zeilen umbrochen**,
gewöhnliche Link-Erkennung würde eine abgeschnittene URL öffnen. Claude Code liefert
beide Auswege selbst: die URL ist als **OSC-8-Hyperlink** markiert (Klick auf eine
mittlere Zeile öffnet die vollen 465 Zeichen) und **`c` sendet OSC 52** mit der
vollständigen URL, die der Client in die Browser-Zwischenablage schreibt (bestätigt).
xterms Standard fragt bei OSC 8 per `confirm()`; eigener `linkHandler` nötig.

**Frage 2 — vorbereitet, Login offen (Mensch).** `codex login --device-auth` läuft im
Container und zeigt eine einzeilige URL plus Einmal-Code (15 min gültig).

**Frage 5 — teilweise.** Das Home-Volume überlebt Neuanlage des Containers (`~/.claude`
von 07:53 unverändert über mehrere `run.sh up` hinweg). `~/.claude.json` liegt **neben** `~/.claude/`: das
Volume muss das ganze Home umfassen (oder `CLAUDE_CONFIG_DIR`). PTY-Sitzungen überleben
einen Server-Neustart nicht; die Testseite versucht dann endlos neu zu verbinden (404) —
der Client muss „Sitzung gibt es nicht mehr“ von „Verbindung weg“ unterscheiden.
`--resume` nach Neustart: Menschen-Task.

**Frage 6 — Zwischenbefund.** Nach dem Anmeldedialog stehen im 10-KB-Puffer die
OAuth-URL 12× (mit `state` und `code_challenge`) und die OSC-52-Nutzlast. Keine
Zugangsdaten (das PKCE-Geheimnis bleibt in der CLI), aber der Puffer hält alles, was
über den Bildschirm lief — auch eine `setup-token`-Ausgabe. Vorschlag: Puffer nur im
Speicher, kein Dump-Endpunkt und kein Diagnoseexport im Produkt; OSC 52 nicht ins
Replay; ein Emulator-Zustand mit begrenztem Scrollback vergisst von selbst, ein
Byte-Log nicht; Aktion „Verlauf leeren“ nach der Anmeldung. **Decision 8 praktisch
belegt:** Der Query-Token stand in zwei Playwright-Konsolenlogs (WebSocket-URL) — im
Produkt Cookie oder kurzlebiges Ticket statt Token in der URL.

**Vorläufige Empfehlung.** Der Ansatz trägt: `portable-pty` wie in `terminal.rs`,
serverseitige Sitzungen und xterm im Browser funktionieren mit der unveränderten CLI,
und Claude Code bringt für den Container-Login alles Nötige mit. Mit `bridge.ts`
und dem Service-Crate kann begonnen werden, sobald die Logins bestätigt sind; vor dem
Sitzungsmanager ist die Emulator-Frage (oben) als eigene Entscheidung zu klären.

## Questions
