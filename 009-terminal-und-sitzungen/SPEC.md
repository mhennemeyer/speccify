---
station: Doing
order: 3
created: 2026-09-10
needs_human: true
ready: true
open_question: null
parent: null
---
# Terminal-Ausgabe und Fortsetzen einer Sitzung verlässlich machen

## Why

Beim Arbeiten an Speccify können Rust-Rebuilds die App neu starten. Die
Fortsetzung soll die beabsichtigte Sitzung öffnen. Frühe Ausgabe und über
Byteblöcke geteilte Zeichen dürfen dabei nicht verloren gehen.

## What

Terminal-Lebenszyklus und Fortsetzung als überprüfbarer Vertrag für Codex und
Claude: Host, Projekt, bekannte Sitzungsidentität, Start-/Endzustand und
Fehler. Bestehende Host-Protokolle weiterverwenden, keine eigene Kopie des
Chatverlaufs führen. Unbekannte freie Kommandos bleiben explizit unterstützt,
aber ohne erfundene Resume-Garantie. Baut auf der Startdiagnose aus 007 auf.

## Acceptance

- Wenn direkt nach PTY-Start Ausgabe entsteht, kommt sie vollständig im
  Terminal an, auch bevor die Startantwort an das Frontend zurückkehrt.
- Wenn UTF-8-Zeichen auf mehrere Lesevorgänge verteilt sind, erscheinen sie
  unverändert. Ein unvollständiges letztes Zeichen wird definiert behandelt.
- Wenn zwei Sitzungen im selben Projekt existieren, öffnet Fortsetzen die
  zugeordnete Sitzung. Ist sie unbekannt oder verschwunden, wird dies sichtbar
  und die Auswahl erfolgt ausdrücklich; es gibt keine unbemerkte Ersetzung.
- Wenn Host-Kommando oder Optionen geändert werden, wird kein ungültiger
  Resume-Aufruf durch bloßes Anhängen gebaut; freie Kommandos bleiben erhalten.
- Wenn der Start scheitert, meldet die UI einen Fehler statt bereits
  „fortgesetzt“. Terminal-Ausgabe allein gilt nicht als erfolgreicher Auftrag.
- Wenn neu gestartet oder beendet wird, bleiben keine verwaisten Listener
  oder durch diesen Terminal-Lebenszyklus verursachten Prozesse zurück.

## Decisions

- D1 (2026-09-10): Unterstützte Resume-Syntax und verfügbare Sitzungsmetadaten
  an den installierten Host-Versionen verifizieren.
- D2 (2026-09-10): Falls eine Host-Version keine belastbare Identifikation
  erlaubt, ist sichtbare Auswahl der Fallback; `--last` bleibt eine kenntliche
  Komfortfunktion und wird nicht als exakte Wiederherstellung bezeichnet.
- D3 (2026-09-10): Rust-Änderungen bündeln und den möglichen Dev-Neustart ankündigen.
- D4 (2026-09-12): Sitzungsidentität je Host, an den installierten Versionen
  geprüft (Claude Code 2.1.269, Codex 0.154.0): Claude erhält beim Start eine
  von der App erzeugte UUID (`--session-id`), das Fortsetzen ruft genau diese
  Sitzung (`--resume <id>`); die App prüft vorher, ob `~/.claude/projects/*/<id>.jsonl`
  existiert. Codex vergibt beim Start keine wählbare ID; dort ist die sichtbare
  Auswahl (`codex resume`, vom Host auf das Projektverzeichnis gefiltert) der
  Weg, `resume --last` bzw. `claude --continue` bleiben als „neueste Sitzung des
  Hosts“ gekennzeichnete Komfortfunktion und werden nie automatisch gestartet.
- D5 (2026-09-12): Der Resume-Aufruf wird nativ aus dem geprüften Startkommando
  gebaut (gleicher Vertrag wie die Startdiagnose). Freie Kommandos, Kommandos
  mit eigener Resume-Option und ein Hostwechsel seit der gemerkten Sitzung
  liefern einen Fehler statt eines angehängten Flags. Der Sitzungsmerker im
  lokalen UI-Speicher wird zu `{host, id, command, startedAt}`; ein alter Merker
  `"1"` gilt als Sitzung ohne Identität (Auswahl statt Automatik).
- D6 (2026-09-12): PTY-Ausgabe wird inkrementell dekodiert; ein am Blockende
  unvollständiges Zeichen wartet auf den nächsten Block, bei Prozessende wird es
  als U+FFFD ausgegeben. Pro Fenster gibt es einen Zerstörungs-Listener, der
  alle Terminals des Fensters beendet; der Reader-Thread wartet den Kindprozess
  ab, damit keine Zombies bleiben.

## Tasks

- [x] Start-/Ausgabe-/Ende-Protokoll einschließlich Listener-Reihenfolge festlegen.
      Frontend registriert `term-out`/`term-exit` vor `terminal_open`; der
      Reader-Thread läuft, bevor die Antwort zurückkehrt (Kommentar in
      `terminal.rs`); `term-exit` kommt erst nach `child.wait()`.
- [x] Inkrementelle UTF-8-Verarbeitung und frühe Ausgabe absichern.
      `Utf8Chunker` in `agent_session.rs`, Tests über alle Schnittstellen
      von „ä€😀“, ungültiges Byte, unvollständiger Rest bei EOF.
- [x] Hostbezogene Start-/Resume-Aufrufe und Sitzungszuordnung implementieren.
      `session_launch` + `session_exists` (Claude: `--session-id`/`--resume <id>`
      gegen `~/.claude/projects/*/<id>.jsonl`; Codex: `resume <id>` gegen
      `~/.codex/sessions/**/rollout-*-<id>.jsonl`, Picker ohne ID); Command
      `agent_session_check`; `terminal_open` nimmt `session` und liefert
      `session`/`launch` zurück.
- [x] Fehler, unbekannte Sitzung und freie Kommandos in der UI abbilden.
      `SessionChoice` + `useSessionState` (Projektfenster und Dashboard);
      Merker `{host,id,command,startedAt}`; abgelehnter Start → Startansicht
      mit Fehler und allen ausdrücklichen Wegen; `continueCommand` entfernt.
- [x] Ein Destroyed-Listener je Fenster statt je Start; Kindprozess nach EOF
      abwarten (added).
- [x] Mock-Fixture `?session=…` und Browser-Suite `test_terminal_session`;
      Hilfe, Website-Doku und UI-Baum angepasst (added).
- [ ] Neustart, zwei Sitzungen, Ctrl-C und Prozessende in der echten App prüfen.
      Gebündelte App neu gestartet (siehe Verification); Klick-Durchlauf mit
      zwei Claude-Sitzungen im selben Projekt bleibt menschliche Abnahme.

## Verification

2026-09-12, Arbeitsbaum auf `503224c`:

- Installierte Hosts: Claude Code 2.1.269 (`--session-id <uuid>`, `-r/--resume
  [id]`, `-c/--continue`, `--fork-session`), Codex 0.154.0 (`resume [SESSION_ID]`,
  `--last`, cwd-Filter im Picker, `--all` hebt ihn auf; keine Option, die ID beim
  Start zu wählen). Probe mit dem echten Host im Scratchpad: `claude -p
  --session-id <uuid>` legt `~/.claude/projects/<encoded cwd>/<uuid>.jsonl` an,
  `claude -p --resume <uuid>` setzt fort, unbekannte ID → „No conversation found
  with session ID“. Die Pfadkodierung ist Hostsache; die App sucht daher über
  alle Projektordner.
- `cargo test -p speccify-desktop`: 97 bestanden, 3 ignoriert (vorher 90); neu:
  Chunker (alle Splits, ungültige Bytes, EOF-Rest), Store-Lookup je Host inkl.
  Pfad-Trick, neue Identität nur bei Claude, exaktes Resume, sichtbare Fehler
  (Hostwechsel, verschwundene Sitzung, vorhandene Sitzungsoption, freies
  Kommando), Picker/Latest ohne Identität. `cargo fmt --check` grün.
- `pnpm --filter speccify-desktop typecheck` grün.
- Browser-Suiten gegen `dev/mock.html` (Vite 127.0.0.1:1421): neue Suite
  `test_terminal_session` (exakt → automatisch `resume` mit ID nach
  `agent_session_check`; verschwunden/alt/Codex/Hostwechsel → Hinweis, kein
  Autostart, `pick`/`latest`/`new` ausdrücklich; abgelehnter Start → Fehler in
  der Startansicht, Neustart merkt neue ID; Dashboard gleich) plus die zehn
  bestehenden Suiten grün (`workflow_ui`, `action_output`, `workspace_shell`,
  `workspace_ui`, `workspace_layout`, `spec_navigation`, `git_workspace`,
  `ui_colors`, `workspace_board`).
- Lokale App: per Quit beendet, `./scripts/dev.sh --app --prepared
  --skip-engine --ui-port=18768` neu gebündelt (Rust-Build 17 s) und gestartet;
  Prozess läuft, Desktop-UI-MCP `initialize` antwortet 200.
- Nicht geprüft: nativer Klick-Durchlauf (zwei Claude-Sitzungen im selben
  Projekt, Ctrl-C, Prozessende, Neustart mit `--resume <id>`), Windows.
  Deshalb `Doing` mit `ready: true` — menschliche Abnahme.

F6–F7 in [006](../006-bestandsaufnahme-agent-terminal/SPEC.md).
Der vorhandene PTY-Test besteht; er prüft nicht die Tauri-Eventzustellung oder
Codex-/Claude-Resume. Umsetzung und echte Host-Fortsetzung noch nicht geprüft.

## Questions

Keine blockierende Frage für den Entwurf; technische Host-Grenzen bei
Umsetzung dokumentieren.
