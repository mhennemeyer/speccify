---
station: Done
created: 2026-09-10
needs_human: false
ready: false
open_question: null
parent: null
---
# Bestandsaufnahme und Ausbauplan für das Agent-Terminal

## Why

Vor dem weiteren Ausbau braucht Speccify einen überprüften Ausgangspunkt.
Die zentrale Frage lautet: Kann eine frische Codex-Sitzung im Speccify-Terminal
das Projekt verstehen und den vollständigen Arbeitsablauf zuverlässig nutzen?

## What

Stand: Commit `0fbfee3`, Desktop-Version `0.6.0`, Prüfung am 10. September 2026
auf macOS. Untersucht wurden Architektur, vorhandene Specs, Startumgebung,
Workflow-Einrichtung, Terminal, Kontextübergabe und CLI/MCP-Prüfstatus.
Ergebnis dieses Auftrags sind Bestandsaufnahme, Playbook und Backlog-Specs.
Die aufgeführten Produktkorrekturen sind noch nicht implementiert.

### Architektur und gelieferter Umfang

| Bereich | Im aktuellen Code vorhanden | Einordnung |
|---|---|---|
| `core/` | Skill-/Tool-Formate, Quellen, Resolver, Lockfile, Expand, Export, Tool-Prüfung | Der fachliche Kern steht. |
| `cli/` und `mcp/` | CLI und 16 registrierte MCP-Tools für Bibliothek, Quellen, Projekte und Tools | MCP ist in dieser Sitzung erreichbar; bei `verify` gehen Statushinweise verloren. |
| `apps/desktop/` | Projektfenster, Specs-Board, Editor, Git, Aktionen, Skills/Tools/MCPs, Agent-Terminal | Für tägliche Arbeit sind die wesentlichen Bausteine implementiert. |
| Rust-Desktop | Native PTYs, System-Git, Dateizugriff, Workflow-Setup, Watcher, Engine-/Sidecar-Verwaltung | Die App liest und schreibt Projektdateien; sie führt keinen eigenen Agent-Loop. |
| `apps/web/backend/` | Bibliotheks-/Viewer-Backend, unter anderem für die ältere Viewer-Kontextbrücke | Dessen `viewer_selection` ist kein allgemeiner Kontext des Desktop-Projektfensters. |
| `apps/marketing/` | Website und Dokumentation | Keine vollständige Inhalts- oder Release-Abnahme in diesem Auftrag. |
| `.agent/` | Elf expandierte Bibliotheks-Skills, drei Tool-Verträge und fünf bisher aktive Specs | Workflow-Vorlagen existieren im Produkt, sind im eigenen Repo aber nicht vollständig eingerichtet. |

### Bestehende Arbeit erhalten

| Spec | Station vor dieser Bestandsaufnahme | Tatsächlicher offener Rest |
|---|---|---|
| [001](../001-skills-und-tools/SPEC.md) | Backlog | M2: vollständiger Skill-/Tool-Einsatz beim Neubau eines alten Projekts. |
| [002](../002-ide-im-projektfenster/SPEC.md) | Doing | Menschliche App-Prüfung von Terminal-Links, Papierkorb und Hunks. |
| [003](../003-website-de/SPEC.md) | Backlog ohne Reihenfolge | Website-/Domain-Entscheidungen und Umsetzung. |
| [004](../004-skill-quellen-und-export/SPEC.md) | Doing | Anzeige neuerer Quellversionen; benötigt strukturierten Verify-Status. |
| [005](../005-spec-workflow/SPEC.md) | Doing | Menschliche Prüfung des neuen Spec-Workflows in der App. |

Diese Stationen werden durch einen Überblicksauftrag nicht umsortiert.
Mehrere `Doing`-Specs sind kein Beweis für gleichzeitig laufende Sitzungen.

### Würde Codex im Agent-Terminal schon zuverlässig arbeiten können?

Grundsätzlich ja: `ProjectShell.tsx` reicht die Projektwurzel und das gewählte
Kommando an `TerminalPanel` weiter; `terminal.rs` startet eine Login-Shell mit
diesem Arbeitsverzeichnis. Das Codex-Preset lautet auf macOS `codex`.
`AGENTS.md` verweist auf `.agent/agent.md`, und `.agents/skills` zeigt hier
korrekt auf `../.agent/skills`. Die offizielle Dokumentation bestätigt
AGENTS.md als Einstieg sowie `.agents/skills` einschließlich Symlinks als
Skill-Suchpfad. Quellen: [Projektanweisungen](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[Skill-Erkennung](https://learn.chatgpt.com/docs/build-skills), gelesen am 10.09.2026.

Vollständig verlässlich ist der Ablauf noch nicht. Eine CLI-Sitzung in einem
PTY erhält ihre Fähigkeiten, Anmeldungen und Berechtigungen vom jeweiligen
Host und dessen Konfiguration. Die Werkzeuge dieser aktuellen Sitzung sind
kein Nachweis dafür, dass eine neue Sitzung im App-Terminal dieselben hat.

| Befund | Beleg und praktische Folge | Folgespec |
|---|---|---|
| F1: CLI-Installation ist nicht eindeutig | `command -v speccify` ergibt lokal eine Installation unter `.local/bin`; deren Hilfe enthält kein `expand`, `export`, `link` oder `tool`. `uv run --frozen --no-sync speccify --help` enthält alle vier. `terminal_open` erzwingt keine passende Speccify-Runtime. Ein Agent kann trotz korrektem Skill die falsche CLI verwenden. | [007](../007-agent-startumgebung/SPEC.md) |
| F2: Eigener Workflow unvollständig | Vor dieser Dokumentation fehlten `.agent/playbooks/`, `spec-next`, `spec-ask` und der installierte Workflow-Marker. Die vollständige Policy steht lediglich unter `apps/desktop/src-tauri/templates/`. `.agent/status.md` und `.agent/resume.md` erzählen ältere Produktphasen. | [008](../008-workflow-konsistenz/SPEC.md) |
| F3: Setup prüft Links zu oberflächlich | `skills_link_present` akzeptiert auch einen defekten Symlink oder irgendein Verzeichnis. `ensure_skills_link` erhält bestehende Links ungeprüft. Nach vorhandenem Policy-Marker und Skills kann ein falsches Ziel als aktuell gelten. Angepasste Skills sollen erhalten bleiben, deren Versionszustand wird aber nicht ausgewiesen. | [008](../008-workflow-konsistenz/SPEC.md) |
| F4: Vorlagen enthalten widersprüchliche Regeln | Das Repo erlaubt Commit/Push ausdrücklich; die generische Policy endet mit einem Verbot ohne gesonderten Auftrag. Außerdem verlangt sie eine `agent_run`-Attribution, während lokale Vereinbarungen Herkunftsangaben untersagen können. Ein unverändert angehängter Block muss Projektregeln respektieren. | [008](../008-workflow-konsistenz/SPEC.md) |
| F5: Beispiel-Tasks beeinflussen echte Arbeit | Rust `count_tasks`, `project_spec_toggle_task` und TS `parseTasks` beachten keine Codezäune. Spec 005 enthält neun Checkboxzeilen, drei davon im Beispiel-Codeblock (Zeilen 72–74). Diese können in Fortschritt und Umschalten eingehen. | [008](../008-workflow-konsistenz/SPEC.md) |
| F6: Fortsetzen ist eine Heuristik | `agentSessionKey` speichert nur `1`, keine Host-Sitzungs-ID. `continueCommand` ergänzt `codex resume --last` bzw. `claude --continue`. Eine andere Sitzung desselben Projekts kann inzwischen die letzte sein. Die Erfolgsmeldung erscheint schon vor bestätigtem Start. | [009](../009-terminal-und-sitzungen/SPEC.md) |
| F7: Terminal hat offene Transport-Randfälle | `TerminalPanel` registriert Ausgabelistener erst nach `terminal_open`; frühe Events können verloren gehen. Rust dekodiert jeden Byteblock separat mit `from_utf8_lossy`; über Blockgrenzen geteilte UTF-8-Zeichen können beschädigt werden. Das sind Codebefunde, kein in der App reproduzierter Ausfall. | [009](../009-terminal-und-sitzungen/SPEC.md) |
| F8: CLI und MCP erzählen unterschiedlichen Prüfstatus | Workspace-CLI: Lockfile konsistent, drei Tools ohne Implementierung (`build-libgit2`, `verify-signatures`, `verify-stream`). MCP `verify`: `ok: true`, leere `problems`, keine Hinweise. Der Adapter verwendet `run_verify`, das den `ExpansionStatus` verwirft. | [010](../010-einheitlicher-pruefstatus/SPEC.md) |
| F9: Auswahl ist nicht automatisch Auftragskontext | Das Board kopiert Pfad und Body in die Zwischenablage; andere Ansichten verwenden `speccify:type-command`. Es gibt keinen gemeinsamen Vertrag mit bestätigter Zustellung, Projekt, Spec und Auftragsart. Ein Board-Klick ist für den Agenten kein verlässlich sichtbarer Auftrag. | [011](../011-auftragskontext/SPEC.md) |
| F10: Vollständige Abnahme fehlt | Vorhandene Tests belegen Core, Adapter, PTY-Grundmuster und Setup. Ein aktueller Durchlauf vom frischen Projekt über Codex, Spec, Skill und Tool bis zum App-Neustart ist damit nicht belegt. | [012](../012-agent-terminal-praxisabnahme/SPEC.md) |

F1 und F8 sind direkt beobachtete Ergebnisse in dieser Umgebung. F2–F7 und
F9 beruhen auf Dateien und Code; ihre Auswirkungen sind teilweise noch in
der echten App zu reproduzieren. Die drei fehlenden Tool-Implementierungen
blockieren nicht jede Codearbeit: Sie werden erst für die jeweiligen Skills
benötigt und gehören zum offenen M2 aus Spec 001.

### Reihenfolge des Ausbaus

Zuerst [007](../007-agent-startumgebung/SPEC.md) (passende Runtime) und
[008](../008-workflow-konsistenz/SPEC.md) (verlässliche Einweisung), dann
[009](../009-terminal-und-sitzungen/SPEC.md) (Sitzungen und Transport),
[010](../010-einheitlicher-pruefstatus/SPEC.md) (ehrlicher Prüfstatus),
[011](../011-auftragskontext/SPEC.md) (konkreter Auftrag) und
[012](../012-agent-terminal-praxisabnahme/SPEC.md) (durchgehende Abnahme).
Die Reihenfolge ist ein Vorschlag im Backlog, keine gestartete Implementierung.
Spec 010 liefert die Voraussetzung für den offenen UI-Rest aus Spec 004.
Spec 012 liefert einen kleinen nachweisbaren Vorlauf zum größeren M2 aus 001.

## Acceptance

- Wenn die Bestandsaufnahme gelesen wird, sind implementierte Funktionen,
  beobachtete Mängel und noch nicht belegte Abläufe unterscheidbar.
- Wenn die nächste Sitzung beginnt, findet sie ein wiederverwendbares Playbook
  und priorisierte Specs mit prüfbaren Akzeptanzkriterien.
- Bestehende offene Umsetzung und menschliche Abnahmen bleiben erhalten.

## Decisions

- D1 (2026-09-10): Diese Arbeit liefert Überblick und Planung. Umsetzung der
  sechs Folgespecs beginnt erst mit einem entsprechenden Auftrag.
- D2 (2026-09-10): Zuverlässige Arbeit im eigenen Terminal hat Vorrang vor
  weiteren IDE-Funktionen oder einer eigenen Agent-Orchestrierung.
- D3 (2026-09-10): Das [Playbook](../../playbooks/weiterentwicklung.md) hält
  den Ablauf fest; diese Spec hält den datierten Befund fest.
- D4 (2026-09-10): Die Historie verwendet neutrale Ereignisse und keine
  Herkunftsangaben oder erfundenen Nutzungsdaten.

## Tasks

- [x] Architektur und bestehende Specs gegen den Code prüfen.
- [x] Codex-Einstieg, Skill-Verweise, Runtime und MCP-Verfügbarkeit prüfen.
- [x] Setup, Terminal, Resume und Kontextübergabe untersuchen.
- [x] Vorhandene Python-/Desktop-Tests und Typecheck ausführen.
- [x] Playbook und abgegrenzte Folgespecs erstellen.
- [x] Dokumentstruktur, Verweise und Nummerierung prüfen.

## Verification

- `speccify --help`: globale Installation ohne vier benötigte Befehle;
  `speccify search 'agent terminal'`: kein Treffer in einem Index.
- `uv run --frozen --no-sync speccify --help`: aktuelle Workspace-Befehle
  vorhanden. Der Speccify-Ablauf ist für die lokale Bestandsprüfung nutzbar;
  eine neue Skill-Expansion ist für diesen Dokumentationsauftrag nicht nötig.
- `uv run --frozen --no-sync speccify verify`: Exit 0, Lockfile konsistent,
  drei fehlende Implementierungen ausdrücklich genannt.
- Erreichbares MCP `verify` am Projekt: `ok: true`, `problems: []`; die
  Implementierung bestätigt den Verlust der zusätzlichen CLI-Statusdaten.
- `uv run --frozen --no-sync pytest core/tests cli/tests mcp/tests --tb=short
  -o addopts='-m "not links"'`: **216 passed, 1 deselected**, zwei
  Deprecation-Warnungen. Erster Sandbox-Lauf scheiterte an Cachezugriff und
  lokalen Testports; erneuter freigegebener Lauf war grün.
- `cargo test -p speccify-desktop -- --nocapture`: **55 passed, 1 ignored**,
  einschließlich PTY- und Workflow-Setup-Tests; `venv_bin` unbenutzt.
- `pnpm --filter speccify-desktop typecheck`: Exit 0.
- Checkboxen in Spec 005: neun durch aktuellen Algorithmus erkennbare Zeilen,
  davon drei im Codeblock; Quelltext von Zähler und Umschalten gegengeprüft.
- Dokumentprüfung: sieben neue Specs mit kanonischen Abschnitten, sieben
  gültige JSONL-Historien, ein Playbook, 30 aufgelöste interne Links und
  eindeutige Nummern einschließlich Archiv. `git diff --check`: grün.
- Nicht geprüft: kompletter Python-Web-Backend-/Dokutestumfang, Release-Build,
  echte Codex-TUI im Speccify-Fenster, anderer Mac, Windows und Login/Resume
  beim Kollegen. Auf Port 8768 lauschte lokal `limactl`; das ist kein Beleg
  für eine laufende native Speccify-App.

## Questions

Keine blockierende Frage für diese Bestandsaufnahme. Die erste empfohlene
Umsetzungsarbeit ist Spec 007; die offenen Produktentscheidungen aus den
bisherigen Specs bleiben dort dokumentiert.
