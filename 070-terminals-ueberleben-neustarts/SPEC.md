---
station: Doing
order: 70
created: 2026-09-25
needs_human: true
ready: true
modules: terminal
parent: 051-terminal-findings-08
---
# Terminals überleben App-Neustarts

## Why

In der aktiven Entwicklungsphase wird die lokale App mehrmals täglich neu
gebaut und gestartet. Jeder Neustart tötet die Agent-Terminals, weil die PTYs
dem App-Prozess gehören; ein laufender Auftrag bricht ab, „Sitzung fortsetzen“
ist nur ein Warmstart mit Gedächtnis. Solange eine Änderung den Agenten nicht
selbst betrifft, soll er weiterlaufen (Nutzerauftrag 2026-09-25). Außerdem
sollen Fensterpositionen und -größen auch harte Abbrüche überstehen.

## What

Ein eigener Prozess `speccify-pty-host` (Rust-Sidecar wie die MCPs) besitzt die
PTYs. Die App spricht ihn über einen Loopback-Socket mit Token an (Vertrag wie
QA-Brücke), der Host hält je Sitzung einen Ringpuffer der Ausgabe und
Metadaten (Fenster, Projektwurzel, Startkommando, Sitzungsidentität). Beim
App-Ende trennt sich die App nur; beim nächsten Start findet das Projekt- oder
Workspace-Fenster seine lebende Sitzung, hängt sich wieder an, spielt den Puffer
ins xterm und streamt weiter. Der Host beendet sich selbst, sobald keine
Sitzung mehr läuft und kein Client verbunden ist.

Opt-in über die Terminal-Einstellungen („Terminals überleben App-Neustarts“);
ohne die Einstellung bleibt alles wie heute (PTY im App-Prozess). Bewusstes
Schließen eines Fensters und „Neu starten“ beenden die Sitzung weiterhin; nur
das App-Ende trennt. Gehostete Sitzungen blockieren keine Update-Installation,
weil sie den Neustart überleben; „Alles stoppen“ beendet auch sie.

Fensterzustand: zusätzlich zum Speichern beim Beenden wird nach Verschieben
oder Größenänderung entprellt gesichert.

Nicht enthalten: Oberfläche vom Vite-Dev-Server laden (Hot Reload, eigene
Spec), Windows-Nativabnahme, Wiederanhängen des Dashboard-Terminals.

## Acceptance

- Wenn die Einstellung aktiv ist und im Projektfenster ein Agent läuft, dann
  läuft der Agent nach Beenden und Neustart der App weiter, das Fenster zeigt
  seine bisherige Ausgabe und nimmt Eingaben entgegen, ohne dass der Agent
  neu gestartet wurde.
- Wenn die App neu gebaut wurde (nur Frontend oder nur Rust ohne Host-Änderung),
  dann gilt dasselbe.
- Wenn die Einstellung aus ist, dann verhält sich die App wie zuvor.
- Wenn ein Fenster bewusst geschlossen oder „Neu starten“ gedrückt wird, dann
  endet die Sitzung wie heute.
- Wenn keine Sitzung mehr läuft und keine App verbunden ist, dann beendet sich
  der Host innerhalb einer Minute; keine verwaisten Prozesse.
- Wenn ein Fenster verschoben oder vergrößert wurde und die App danach hart
  beendet wird, dann startet das Fenster an der neuen Position.
- Wenn der Host nicht startbar ist, dann fällt das Terminal sichtbar auf den
  App-Prozess zurück statt still zu scheitern.

## Decisions

1. 2026-09-25: Eigener Host-Prozess statt tmux: plattformneutral (ConPTY läuft
   in einem eigenen Prozess genauso), keine verschachtelte Oberfläche, die
   Sitzungsidentität und Kontextdateien der App bleiben erhalten. tmux bleibt
   Notbehelf für heute (freies Kommando, ohne Sitzungs-ID/Kontext).
2. 2026-09-25: Protokoll zeilenweise JSON über TCP 127.0.0.1 mit Token aus
   `~/.speccify/pty-host.json` (0600), wie QA-Brücke; Ausgabe base64. Eine
   Verbindung je App, Sitzungen darüber gemultiplext; Puffer-Replay und
   Sink-Registrierung geschehen atomar, damit keine Ausgabe doppelt oder
   verdreht ankommt.
3. 2026-09-25: Trennen statt Töten nur bei App-Ende (`ExitRequested`), nicht bei
   Fenster-Schließen: ein versehentlich geschlossenes Fenster soll keinen
   unsichtbaren Agenten hinterlassen.
4. 2026-09-25: Workspace-Kontextdateien liegen im Host-Modus unter
   `~/.speccify/pty-host/`, nicht im Temp der App, weil sie den App-Prozess
   überleben müssen.

## Tasks

- [x] Crate `crates/pty-host`: Host (Sitzungen, Ringpuffer, Attach/Detach,
      Idle-Ende, Zustandsdatei) und Client, mit Tests gegen echte PTYs.
- [x] App: Host starten/finden, Terminal-Backend umschaltbar, `terminal_live`
      und `terminal_attach`, Trennen bei App-Ende, Einstellung und Sidecar-Bündelung.
- [x] Frontend: Wiederanhängen in Projekt- und Workspace-Fenster, Einstellung,
      Mock und Browser-Regression.
- [x] Fensterzustand entprellt sichern.
- [x] Lokale App bauen, Neustart mit laufendem Agenten prüfen, Doku/Playbooks.
- [x] (added) App trennt die Host-Verbindung, sobald keine gehostete Sitzung
      mehr läuft; `Client::drop` schließt den Socket auch für den Lese-Thread —
      sonst lief der Host mit der App endlos weiter (Befund im Nativtest).

## Verification

2026-09-25, lokaler Debug-Build 0.8.6 mit Sidecar `speccify-pty-host`
(Developer-ID-signiert, `codesign --verify --deep --strict` bestanden):

- `cargo test -p speccify-pty-host`: 5 Tests grün, darunter gegen echte PTYs:
  Trennen und Wiederanhängen mit lückenlosem Replay (tick 0…n ohne Lücke
  oder Dopplung), Exit-Code auch für späte Anhänger, Startkommando vor der
  ersten Ausgabe, Ringpuffer hält die Grenze, Token-Pflicht, Client-Drop
  meldet den Client beim Host ab.
- `cargo test -p speccify-desktop`: 134 bestanden (3 bestehende ignoriert);
  `cargo fmt --check` grün; `pnpm --filter speccify-desktop typecheck` grün.
- Browser: neu `scripts/test_terminal_reattach.mjs` (lebende Host-Sitzung →
  `terminal_attach` statt `terminal_open`, Puffer sichtbar, Eingabe geht
  durch, kein Sitzungsdialog; ohne Host unverändert; Einstellung round-trip);
  `test_terminal_preferences`, `test_action_output`, `test_workspace_layout` grün.
- Gebündelte App über die QA-Brücke, Einstellung an: Wegwerfprojekt, Shell im
  Host (`~/.speccify/pty-host.json` mit Port/Token/PID, Sitzung mit
  Fenster-Metadaten gelistet), Zähler `tick n` im Sekundentakt; App per
  `quit` beendet → Host und Sitzung leben weiter; App neu geöffnet → Fenster
  wiederhergestellt, Terminal per `terminal_attach` verbunden, Ausgabe ab
  tick 0 ohne Lücke bis zum lebenden Stand, Eingabe angenommen, kein
  Sitzungsdialog. Danach Fenster mit ⌘W geschlossen → Sitzung beendet,
  Zählerprozess weg, Host 61 s später von selbst beendet, Zustandsdatei
  entfernt, keine Restprozesse; App lief weiter.
- Fensterzustand: Hauptfenster per System Events verschoben, `.window-state.json`
  innerhalb von 2 s ohne Beenden aktualisiert (main x/y = neue Position).
- Ein zweiter Neubau (`dev.sh --app --prepared`) während eine Host-Sitzung
  lief verhielt sich wie das Beenden: Sitzung überlebte, Fenster hängte sich an.
- Offen: menschliche Sichtabnahme mit echtem Claude-Lauf, Windows/Linux
  (ConPTY im Host ungeprüft), Dashboard-Terminal hängt sich nicht wieder an.

Nachtrag 2026-09-26: Die App stürzte beim Öffnen eines Projektfensters ab
(kein Absturzbericht im System). Wahrscheinliche Ursache war das entprellte
Sichern des Fensterzustands aus einem Hintergrund-Thread; Fenstergeometrie
darf auf macOS nur der Main-Thread lesen. Das Sichern läuft jetzt über
`run_on_main_thread`. Nachgestellt im gebündelten Build: Projektfenster öffnen,
dreimal verschieben, Zustandsdatei aktualisiert, App lebt.

Nachtrag 2026-09-26 (zweiter Befund): Im Workspace-Terminal scheiterte Claude
mit „Append system prompt file not found“: die Startzeile nannte die
Temp-Kontextdatei, die mit dem Ende von `terminal_open` gelöscht wird, statt
der dauerhaften Kopie unter `~/.speccify/pty-host` (D4). Der Pfad wird jetzt
vor dem Bau der Startzeile festgelegt. Zweiter Befund derselben Runde: „Neu
starten“ nach einem Wiederanhängen versuchte erneut `terminal_attach` auf die
beendete Sitzung; Projekt- und Workspace-Fenster löschen die Attach-Anfrage
nach Öffnen oder Fehler (Browser-Regression erweitert). Nativ geprüft im
Apps-Workspace: Claude startet mit dem Host-Kontextpfad, Neustart öffnet eine
neue Sitzung.

## Questions

Keine.
