---
description: Lebende Bestandskarte mit Architektur, vollständigem funktionalem UI-Baum, Prüfstand und bekannten Grenzen.
---
# Speccify: aktueller Stand und UI-Baum

Bestandsdatum: **2026-09-10**. Basiscommit `0fbfee3`, Desktop-Version im Repo
`0.6.0`, **einschließlich lokaler, noch nicht committeter Änderungen an Specs 007/013**.
Das ist kein Nachweis, dass diese Funktionen bereits als Release verteilt sind.

Schnelleinstieg: [Fähigkeiten](#fähigkeiten-vorhanden-geprüft-offen) ·
[UI-Baum](#vollständiger-funktionaler-ui-baum--ist) · [Specs](#stand-der-specs) ·
[Prüfstand](#verifikation-und-verbleibende-risiken) ·
[UI-Ausbau](#vorgeschlagener-ui-ausbau--nicht-implementiert).

Ziele und Ausbauentscheidungen stehen im
[Playbook Produktvision und Weiterentwicklung](weiterentwicklung.md).
Dieses Dokument beschreibt den Ist-Zustand; geplante Ergänzungen stehen getrennt
am Ende. Bei Änderungen an Navigation, Fähigkeit oder Abnahme im selben
Änderungssatz nachführen. Historische Befunde bleiben in den jeweiligen Specs.

## Kurzurteil

Speccify hat bereits ein substanzielles Desktop-Arbeitsfenster: Spec-Board,
Datei-Editor, Git, Skills/Quellen/Export, Playbooks, Tool-Verträge, Aktionen,
MCP-Konfiguration und ein natives Agent-Terminal. Es ist keine bloße Konzept-App.

**„Perfekt im Agent-Terminal arbeiten“ ist noch nicht belegt.** Die Startumgebung
ist lokal implementiert und automatisiert geprüft. Verlässliche Wiederaufnahme,
Workflow-Konsistenz, einheitlicher Prüfstatus und eine quittierte Kontextübergabe
sind weiterhin offene Arbeit. Die vollständige Abnahme im echten Fenster mit
einem angemeldeten Host auf den Zielplattformen steht aus.

## Architektur und Datenhoheit

| Bereich | Aufgabe und kanonischer Ort |
|---|---|
| Python-Domäne | `core/`: Skill-Auflösung, Quellen, Lock/Bundle, Expand, Export, Verify, Tool-Prüfung |
| Adapter | `cli/` (Typer), `mcp/` (MCP), über dieselbe Domänenlogik |
| Native Dienste | `crates/`: Exec, Discovery, Toolbox und Parallels; Desktop-Rust für Dateien, Git, PTY, Workflow, Engine, Supervisor |
| Desktop | `apps/desktop/src/` React; `apps/desktop/src-tauri/` Tauri 2 |
| Website/Hilfe | `apps/marketing/`: Astro/Starlight, EN/DE; Desktop-Hilfe separat über den nativen Hilfe-Vertrag |
| Projektwissen | `.agent/agent.md`, `.agent/playbooks/`, `.agent/specs/<NNN-slug>/SPEC.md` + `history.jsonl` |
| Skills/Tools | `.agent/skills/<name>/SKILL.md`, `.agent/tools/<name>/TOOL.md` + Plattformimplementierungen |
| Herkunft/Prüfung | `speccify.yaml`, Lockdateien, `.agent/speccify/expansions.yaml`; Status nicht von Hand erfinden |
| Host-Adapter | `AGENTS.md`/`CLAUDE.md`; `.agents/skills` und `.claude/skills` verweisen auf `.agent/skills` |
| Ausführung | `.agent/actions.json`, Exec-Allowlist und Interaktionen; nicht gleichbedeutend mit beliebigen Host-Berechtigungen |
| Rechnerpräferenzen | globale Einstellungen/Quellen, lokale Checkouts; Fensterlayout, Entwürfe und Sitzungsmerker teilweise in lokalem UI-Speicher |

Ein Projektfenster erhält heute **einen Projektpfad**. Es gibt mehrere separat
öffnbare Projekte, aber noch kein gemeinsames Workspace-/Multi-Repo-Domänenmodell.
Speccify-Server starten und Host-Konfiguration anzeigen ersetzt nicht automatisch
deren Einrichtung oder Verfügbarkeit im gewählten Agenten.

## Fähigkeiten: vorhanden, geprüft, offen

„Vorhanden“ bezeichnet Code und erreichbare UI-Pfade, nicht pauschale Qualität
oder vollständige Plattformabnahme.

| Fähigkeit | Ist-Stand | Grenze / Folgeschritt |
|---|---|---|
| Projekte | Ordner/Pfad öffnen, zuletzt verwendete Projekte, eigenes Fenster | keine automatische Verbunderkennung oder gemeinsame Board-Sicht; V1-01 |
| Specs | Gesamtliste links, Suche/Themenfilter, Backlog/Doing/Done, gemeinsamer Task-Vertrag, Fragen und pfadgenaue Historie; Altbestand lesbar, kein Archivierungsschritt | keine Sperre gegenüber externen Editoren; Team-/Branch-Sicht fehlt |
| Workflow-Setup | Policy v5 ohne Archivierungsschritt, versionierte Skills, bekannte Vorlagen sicher migrieren, konkrete Link-/Anpassungsdiagnose | individuelle/neue unbekannte Vorlagen und fremde Links bleiben zur manuellen Prüfung erhalten |
| Playbooks | Liste, Markdown lesen/bearbeiten, neu/löschen, als Prompt kopieren | keine Workspace-Herkunft oder Team-Verteilung |
| Editor/Git | mehrere offene Dateien, Entwürfe, Suche, Dateioperationen, Diff, Staging auch pro Hunk, Commit, Branches, Remotes, Historie/Blame | echte IDE-Abnahme 002 offen; kein belegtes LSP-/Debugger-/Konfliktlösesystem |
| Skills | Projektliste, Bibliotheken durchsuchen, globale/projekteigene Quellen, Import/Expand, Exportkommando | keine explizite Source-/Target-Rolle; Teile von 004 noch abnehmen |
| Tools | Verträge, Plattformimplementierungen und Prüfstatus sichtbar | drei lokale Tool-Implementierungen fehlen laut Basisprüfung; 010 vereinheitlicht Meldungen |
| Aktionen | bestätigte Kommandos, Formulare, Allowlist-Freigabe, Live-Ausgabe, Stop, einfache Diagramme, Toolbar | `toolui:` und Parallels-Aktionsziele in dieser UI noch Platzhalter; V1-06 |
| MCP | Serverübersicht/Supervisor, Client-Config, projektspezifische Claude-/Codex-Konfiguration, Allowlists | Portstatus ist kein erfolgreicher Handshake; kein itsdcloud-Adapter |
| Lokale MCP-HTTP-Grenze | 014: gemeinsame Host-/Origin-/Methoden-/JSON-/1-MiB-Prüfung für Rust-MCPs, vor RPC und Exec-Stream | Keine Browserfreigaben oder Client-Authentifizierung; kein vollständiger DoS-/Konformitätsschutz; [Vertrag](../../docs/exec-mcp-contract.md) |
| Terminal | native PTY, Host-Voreinstellungen/freies Kommando, Shell-only, Projekt-cwd, rechts/unten, Neustart | UTF-8-Chunking, genaue Sitzungsidentität und Roundtrip offen; 009/012 |
| Startdiagnose | Runtime-Auswahl, Host-/CLI-Probe, Fehler/Warnungen vor Start und im Terminal; lokal neu in 007 | Version/Startfähigkeit beweisen weder Anmeldung noch erfolgreiche Fortsetzung |
| Lokaler Betrieb | 013: Status vor Build, expliziter Fragen-MCP-Port, gebündelte App ohne Watcher, Wiederöffnen und Schutz laufenden Bundles | macOS lokal geprüft; kein Autostart-Dienst oder gleichzeitiger Betrieb zweier App-Instanzen |
| Repo-Demoaktionen | 017: Tests (Toolbar), Desktop-Tests, Typecheck, Git-Überblick, Live-Diagramm in `.agent/actions.json` | Prepared macOS-/Unix-venv; individuelle Toolbar-Auswahl kann Default übersteuern; kein App-Neustart erforderlich |
| Umgebung | Doctor, Python-Erkennung/Installation, gebündelte Python-Engine installieren/reparieren | Zielplattform und installierte Version jeweils praktisch prüfen |
| Updates | bedingt aktiviertes Plugin, manuelle Suche + direkte Installation, Release-Konfiguration | Basisconfig ohne Public Key; Release-Secrets nicht geprüft; kein belegter automatischer Rollout |
| Knowledgebases | lokale Buch-/Indexliste, Metadaten, Bücher öffnen, Abfragekommandos kopieren | Legacy-`dotagent kb`-Bezug; kein automatisch geladener itsdcloud-Projektkontext |
| Feedback/Integrationen | allgemeine technische Grundlagen vorhanden | kein Feedback-Tab, kein kontextsensitiver Feedback-Composer, keine itsdcloud-UI |
| Hilfe/Tutorial | integrierte Hilfe, Website, EN/DE-Tutorial | Tutorial und Teile der deutschen App-Doku noch auf Plänen/Tickets |

## Vollständiger funktionaler UI-Baum — Ist

Abdeckung: sämtliche aktuellen Dashboard-Seiten und Projekt-Tabs einschließlich
Navigatoren, Inspektoren, Dialogen und gemeinsamen Bedienflächen. Dies ist ein
**Funktions-/Navigationsbaum aus dem Code**, kein DOM-Baum und keine Behauptung
einer visuellen Vollabnahme. Wiederverwendete Knöpfe und Lade-/Leer-/Fehlerzustände
werden nicht bei jedem Vorkommen wiederholt. Bedingte Elemente sind entsprechend markiert.

### Dashboard-Fenster

Quelle: [App.tsx](../../apps/desktop/src/App.tsx),
[Dashboard-Views](../../apps/desktop/src/views/).

```text
Speccify · Dashboard
├── Hauptnavigation / Inhaltsbereich
│   ├── Projekte
│   │   ├── Projektpfad eingeben → öffnen
│   │   ├── Verzeichnisdialog → wählen und öffnen
│   │   └── Zuletzt geöffnet → eigenes Projektfenster
│   ├── Bibliothek
│   │   ├── Globale Skill-Quellen
│   │   │   ├── Git-URL oder lokaler Ordner hinzufügen
│   │   │   └── Quelle: Herkunft/Pfad/Status · aktualisieren · entfernen
│   │   ├── Toolbox: Aktualisieren · Tag-Filter
│   │   ├── Gruppen: Tools / MCP-Server / Knowledgebases
│   │   │   └── Karte: Name/Art/Herkunft · Beschreibung · Requirements · Run · Tags
│   │   └── Neues Manifest: Slug · Art · Name → im Working Dir anlegen
│   ├── Knowledgebases
│   │   ├── Aktualisieren · Basisverzeichnis · KB-Auswahl
│   │   └── Detail: Pfad · Bücher/Chunks/Indexgröße
│   │       ├── dotagent kb search / ask → Kommando kopieren
│   │       └── Bücherliste → Buch extern öffnen
│   ├── Umgebung
│   │   ├── Aktualisieren / Diagnose
│   │   ├── Fragen-MCP dieser App: konfigurierter Endpoint / Hinweis zu bestehenden Configs
│   │   ├── Speccify-Version / Updater
│   │   │   ├── konfiguriert: suchen → herunterladen/installieren → Neustarthinweis
│   │   │   └── nicht konfiguriert: Hinweis auf fehlenden Signaturschlüssel
│   │   ├── Python-Engine: Status · installieren/reparieren · Fortschritt/Log
│   │   ├── Werkzeug-Checks: Fundort/Version/Fehler · Installkommando kopieren
│   │   └── Python-Versionen: vorhanden/verfügbar · Auswahl · installieren
│   ├── Server
│   │   ├── Aktualisieren · MCP-Serverkarten aus Toolbox
│   │   └── Server: Port/stdio · Status · Binary-Herkunft
│   │       ├── HTTP starten / eigenen Prozess stoppen · externe Prozesse markieren
│   │       ├── stdio: Start durch Client erläutern
│   │       ├── Client-Config einblenden/kopieren
│   │       └── Supervisor-Log / fehlendes Binary
│   ├── Agents
│   │   ├── Claude: globale settings.json / CLAUDE.md
│   │   ├── Codex: globale config.toml / AGENTS.md
│   │   └── bekannte Datei auswählen → Text bearbeiten/speichern; fehlend anzeigen
│   ├── Settings
│   │   ├── Erscheinungsbild: System / Hell / Dunkel (fensterübergreifend)
│   │   ├── Agent-Sitzung: Dashboard-Fortsetzung nach Neustart
│   │   ├── Working Dir: Pfad / Verzeichnisdialog
│   │   ├── Skill-Quellen: Anzahl / Verweis auf Bibliothek
│   │   ├── Terminal-Agent: Autostart-Kommando / Presets
│   │   ├── Einstellungen speichern
│   │   └── Agent-Einweisung im Working Dir: vorhandene Dateien / fehlende anlegen
│   └── Hilfe
│       └── Dokumentliste → Markdown-Inhalt / Quellenpfad
└── Terminal-Seitenleiste (ein-/ausblendbar)
    ├── Frageanzeige / Anzahl offener Interaktionen
    ├── AskBoPanel: Einzelwahl / Mehrfachwahl / Formular · Antwort senden
    └── Agent-Terminal: Working Dir · Startumgebung · PTY · Fehler · Neu starten
```

### Projektfenster: Rahmen und gemeinsame Bedienflächen

Quellen: [ProjectShell.tsx](../../apps/desktop/src/ProjectShell.tsx),
[Layout](../../apps/desktop/src/lib/layout.ts),
[SettingsSheet](../../apps/desktop/src/components/SettingsSheet.tsx).

```text
Projektfenster · ein Projektpfad (Startbereich: Specs)
├── Toolbar
│   ├── Projekttitel / vollständiger Pfad
│   ├── konfigurierbare Knöpfe: Pull · Push · Commit · Agent · Projektaktionen
│   ├── Aktivität → Popover: laufende/beendete Vorgänge in diesem Fenster
│   ├── Navigator ein/aus · Terminal unten ein/aus · Inspektor ein/aus
│   ├── Hell/Dunkel umschalten
│   └── Einstellungen-Popover
│       ├── Erscheinungsbild: System / Hell / Dunkel
│       ├── Agent-Terminal: Unten / Rechts
│       ├── Agent-Sitzung: automatisch fortsetzen
│       ├── Toolbar: Knöpfe aktivieren/deaktivieren · Reihenfolge ändern
│       └── Layout zurücksetzen · Schließen
├── Navigator links: Bereichsgruppen → Unter-Tabs → tabbezogene Liste
│   └── Farbkonzept v1: Bereichs-Icons und getönte Auswahl, Hell/Dunkel (019)
├── Inhaltsbereich
│   ├── Workflow-Banner (falls fehlend/veraltet/angepasst)
│   │   └── strukturierte Befunde mit Pfad/Zustand · sichere Updates / manuelle Prüfung · Einrichten · Fehler
│   └── Inhalt des gewählten Tabs (siehe unten)
├── Rechte Seitenleiste mit horizontal scrollbarer Tab-Leiste
│   ├── Inspektor: auswahlabhängige Details / Aktionen / Unter-Tabs
│   ├── Aktionsausgaben: ein Tab je Aktion · Status · abgeschlossene Tabs schließen
│   │   ├── Start aus Toolbar oder Aktionskarte öffnet den Tab automatisch
│   │   └── Live-Text / Fortschritt / Diagramme / Exit / Dauer / Stop
│   └── bei rechtem Terminal-Dock: zusätzlich Terminal-Tab
├── Agent-Terminal (dieselbe Instanz, unten oder rechts)
│   ├── vor Start: Kommando / Presets · leer = Shell-only
│   ├── Startumgebung prüfen: Host, Pfad/Version, CLI/Quelle, Hinweise/Fehler
│   ├── Starten / Neu starten / Letzte Sitzung fortsetzen (wenn Merker vorhanden)
│   └── laufend: cwd · Startdetails · PTY · Neustart · Dock wechseln
└── Splitter: Größen ändern/zurücksetzen; Layout pro Projekt gespeichert
```

Gruppenwechsel über ⌘1–5 bzw. Strg+1–5; Navigator ⌘0 bzw. Strg+0,
Inspektor ⌥⌘0 bzw. Strg+Alt+0. Listen/Details können bei ausgeblendeten Panels
inline erscheinen; das sind keine zusätzlichen Produktbereiche.

### Projektfenster: alle Bereiche und Unteransichten

Quelle: [Projekt-Views](../../apps/desktop/src/views/project/).

```text
Navigator · fünf Gruppen, zehn Tabs
├── Dateien [Gruppe 1]
│   ├── Dateien
│   │   ├── Navigator: Dateibaum / Suche
│   │   │   ├── Dateiname filtern · Ordner auf/zu
│   │   │   ├── Dateityp-Symbole: Quelltext / Konfiguration / Dokument / Bild / neutral; Ordner Amber (019)
│   │   │   ├── Neue Datei / neuer Ordner (relativer Pfad)
│   │   │   └── Inhaltssuche: Text · Groß/Klein · Regex → Treffer nach Datei/Zeile
│   │   ├── Inhalt: offene Datei-Tabs · Editor · Entwurfs-/Fehlerzustand
│   │   │   └── Datei wählen/schließen · speichern (⌘S) · Binärdatei-Hinweis
│   │   └── Inspektor: Metadaten · als Prompt kopieren
│   │       ├── Datei: Blame am Rand · umbenennen · Löschen → Papierkorb bestätigen
│   │       └── Historie: Commitliste → Datei-Diff → als Prompt kopieren
│   └── Git
│       ├── ohne Repo: Repository anlegen
│       ├── Navigator: Branch · Commitbereich · Fetch/Pull/Push
│       │   ├── unstaged / staged Dateien → stagen / aus Index nehmen
│       │   └── Commit-Historie → Commit auswählen
│       ├── Inhalt: ausgewählter Datei-/Commit-Diff · Hunks
│       │   ├── Hunk stagen / unstagen
│       │   └── Remote-/Commit-Ausgabe mit Laufstatus, Fehler und Schließen
│       └── Inspektor (abhängig von Auswahl)
│           ├── Commit: Nachricht · gestagete Änderungen committen
│           │   ├── alles stagen und committen
│           │   ├── Commit-Auftrag an Agent-Terminal
│           │   └── Branches: auflisten/wechseln · neu anlegen und wechseln
│           ├── Datei: Git-Status/Index/Arbeitsbaum · öffnen · Diff kopieren
│           │   └── Änderungen / Historie · Dateiänderungen verwerfen (destruktiv)
│           └── Commitdetail: Hash · betroffene Dateien/Diffs · Nachricht anzeigen
├── Orga [Gruppe 2]
│   ├── Playbooks
│   │   ├── Navigator: Playbook-Liste · neues Playbook (Name)
│   │   ├── Inhalt: Markdown · Doppelklick/Bearbeiten → Editor
│   │   │   └── Beschreibung/Inhalt · Speichern / Abbrechen
│   │   └── Inspektor: Pfad/Metadaten · als Prompt kopieren · Bearbeiten · Löschen
│   └── Skills
│       ├── Modus: Im Projekt
│       │   ├── Navigator: Skill-Liste mit Metadaten/Status
│       │   ├── Inhalt: SKILL.md
│       │   └── Inspektor: Herkunft/Version · als Prompt kopieren · Tools ansehen · Export
│       │       └── Exportformular: Quelle wählen · Kategorie · Kommando-Vorschau
│       │           └── ins Terminal tippen / Kommando kopieren; Generalisierungshinweis
│       └── Modus: Quellen durchsuchen
│           ├── globale/projekteigene Quelle auswählen · Quelle hinzufügen
│           ├── Quelle aktualisieren / projektspezifische Quelle entfernen
│           ├── Navigator: Skills der Quelle · Inhalt: gewählte SKILL.md
│           └── Inspektor: Herkunft/Version · Import (add + expand ins Terminal)
├── Technik [Gruppe 3]
│   ├── Tools
│   │   ├── Navigator: Tool-Liste
│   │   ├── Inhalt: TOOL.md
│   │   └── Inspektor: Pfad · Plattformimplementierungen/Prüfstatus · Prompt kopieren
│   ├── Aktionen
│   │   ├── Navigator: bestätigte Aktionen · Anzahl Vorschläge
│   │   ├── Aktionskarte: Name/Befehl/Beschreibung · Eingaben
│   │   │   ├── Eingaben: Text / Auswahl / Datei / Verzeichnis
│   │   │   ├── ausführen · Toolbar an/aus · löschen
│   │   │   ├── Ausgabe anzeigen → zugehöriger Tab rechts neben dem Inspektor
│   │   │   └── Platzhalter: Parallels-Ziel · toolui:-App-Panel („folgt“)
│   │   ├── Vorschläge: vorgeschlagene Aktionen bestätigen
│   │   ├── abgelehnte Exec-Befehle: bestätigen + dauerhaft freigeben
│   │   ├── Neue Aktion: Name · argv-Kommando · Beschreibung → anlegen
│   │   └── Inspektor: Quelle/Ziel/Eingaben/letzter Lauf · ausführen · Toolbar
│   ├── MCPs
│   │   ├── Navigator: Server nach Host-Konfiguration
│   │   ├── Inhalt: Serverkarten aus .mcp.json / .codex/config.toml
│   │   ├── Claude-Allowlists: settings.json / settings.local.json
│   │   └── Inspektor: Host/Pfad/Startkonfiguration · JSON kopieren
│   └── Agent
│       ├── Agent-Kommando / Presets (für nächsten Start)
│       ├── Startumgebung prüfen / Diagnosebericht
│       ├── Navigator: Projekt-Einweisungsdateien
│       ├── Inhalt: gewählte Einweisung als Markdown
│       └── Inspektor: Pfad/Rolle/Terminal-Kommando · als Prompt kopieren
├── Specs [Gruppe 4; ein Tab]
│   ├── Navigator: jede Spec als Listeneintrag · Nummer/Titel/Station/Tasks/Flags
│   │   └── Altbestand in derselben Liste · Herkunft im Detail · nur lesen
│   ├── Filter über Board: Suche (Titel/Nummer/Pfad) · Ober-Spec · braucht mich · zurücksetzen
│   ├── Lauf-Kennzahlen → Liste jüngster Läufe (wenn History Daten enthält)
│   ├── unnummerierte Specs nummerieren (falls vorhanden)
│   ├── Board: Backlog / Doing / Done (v1: Slate / Blau / Grün; getönte Flächen)
│   │   ├── Karten: Nummer/ID · Titel · Status-Badges · Aufgabenfortschritt
│   │   ├── Drag-and-drop zwischen Stationen
│   │   └── Done nach Parent gruppiert; unbekannte Alt-Stationen unverändert als zusätzliche Lesespalten
│   ├── + Spec / Doppelklick → Spec-Dialog
│   │   ├── Titel · Station · order · parent · bereit · braucht BO
│   │   ├── Markdown-Inhalt / Standardvorlage
│   │   └── Speichern / Abbrechen / gesamten Spec-Ordner löschen
│   └── Inspektor: Metadaten · Markdown · Tasks abhaken
│       ├── Fragen beantworten · Historie
│       └── Prompt kopieren · bearbeiten; Altbestand ohne Schreibaktionen, kein Archivieren
└── Hilfe [Gruppe 5; ein Tab]
    └── Navigator: Dokumentliste → Inhalt/Inspektor: Dokument und Quellenpfad
```

Es existiert noch **kein allgemeines Rechtsklick-Feedback-Menü**. „Als Prompt
kopieren“ ist meistens Clipboard, während andere Aktionen Kommandos ins Terminal
tippen. Beides ist noch kein einheitlich quittierter Agent-Auftrag (Spec 011).
Das AskBoPanel im Dashboard und die Spec-Fragen im Projekt sind unterschiedliche
Bedienwege; nicht als bereits vereinheitlichte Fragen-Inbox darstellen.

### Website und Dokumentation

Quellen: [Astro-Navigation](../../apps/marketing/astro.config.mjs),
[Seiten](../../apps/marketing/src/pages/),
[Dokumente](../../apps/marketing/src/content/docs/).
Dateistämme unten identifizieren die tatsächlichen Inhalte; übersetzte Titel
und Starlight-Standardbedienung (Suche, Sprache, Theme, Inhaltsverzeichnis) kommen hinzu.

```text
Website
├── Landingpage Englisch (/), Deutsch (/de/)
├── Download (/download/)
├── Rechtliches: Impressum / Datenschutzerklärung
└── Dokumentation (EN; DE teilweise übersetzt)
    ├── Tutorial: Zero to App Store / Von null in den App Store
    │   └── intro · prerequisites · project-setup · plan-and-tickets
    │       · importing-skills · working-and-commits · exporting-skills
    │       · fastlane-and-asc · i18n · submission (je EN/DE)
    ├── Fundamentals / Grundlagen
    │   └── overview · skills · tools · mcps (je EN/DE)
    ├── Speccify
    │   └── overview · walkthrough · expand · execute · evaluate (je EN/DE)
    │       · export (EN)
    ├── The app / Die App
    │   ├── EN: overview · files-and-git · specs · actions · questions · skills-tab
    │   └── DE: overview · board · plans · actions · questions · skills-tab
    ├── Git sources & discovery: index (EN)
    ├── CLI Reference (EN)
    │   └── index · init · add · pull · lock · expand · verify · export
    │       · link · search · show · check · lint · tool-check
    └── MCP Reference: index (EN)
```

**Bekannte Drift:** Die deutsche App-Doku hat noch `plans`/`board` statt der
aktuellen englischen `specs`/`files-and-git`. Das 4Notice-Tutorial nennt noch
das frühere Plan-/Ticket-Modell. Vorhandene Seiten sind kein Nachweis, dass
alle beschriebenen Durchläufe mit der heutigen App erneut funktioniert haben.

## Stand der Specs

Momentaufnahme; für Aufgaben und spätere Statusänderungen die jeweilige Spec lesen.
Diese Tabelle verändert keine Station oder Reihenfolge.

| Spec | Station am Bestandsdatum | Bedeutung |
|---|---|---|
| [001 Skills/Tools](../specs/001-skills-und-tools/SPEC.md) | Backlog | große Teile vorhanden, Wissens-/Tool-Roundtrips und Restarbeit offen |
| [002 IDE](../specs/002-ide-im-projektfenster/SPEC.md) | Doing | implementierter Ausbau, menschliche UI-Abnahme offen |
| [003 Website DE](../specs/003-website-de/SPEC.md) | Backlog | ältere Planung, mit aktuellem Website-Stand abgleichen |
| [004 Quellen/Export](../specs/004-skill-quellen-und-export/SPEC.md) | Doing | Quellen-/Exportbasis vorhanden, Restprüfung offen |
| [005 Spec-Workflow](../specs/005-spec-workflow/SPEC.md) | Doing | implementierter Wechsel, menschliche App-Abnahme offen |
| [006 Bestandsaufnahme](../specs/006-bestandsaufnahme-agent-terminal/SPEC.md) | Done | geprüfter Ausgangspunkt, kein Beleg für beseitigte Befunde |
| [007 Startumgebung](../specs/007-agent-startumgebung/SPEC.md) | Doing, ready, needs_human | lokal implementiert und automatisiert geprüft; reale Startwege offen |
| [008 Workflow-Konsistenz](../specs/008-workflow-konsistenz/SPEC.md) | Doing, ready, needs_human | Aufgaben-/Setup-Vertrag geprüft, Repo v4/current; neuer App-Build läuft, Wiederaufnahme wartet auf macOS-Schreibtischfreigabe |
| [009 Terminal/Sitzungen](../specs/009-terminal-und-sitzungen/SPEC.md) | Backlog | UTF-8 und eindeutige Fortsetzung; Listener-Reihenfolge teilweise in 007 vorgezogen |
| [010 Prüfstatus](../specs/010-einheitlicher-pruefstatus/SPEC.md) | Backlog | identische Befunde für CLI/MCP/UI |
| [011 Auftragskontext](../specs/011-auftragskontext/SPEC.md) | Backlog | strukturierte Übergabe mit Ziel, Revision und Empfangsbestätigung |
| [012 Praxisabnahme](../specs/012-agent-terminal-praxisabnahme/SPEC.md) | Backlog | vollständiger Durchlauf im echten Agent-Terminal |
| [013 Lokale App/Startdiagnose](../specs/013-lokale-app-und-startdiagnose/SPEC.md) | Doing, ready, needs_human | App ohne Watcher auf 18768 gestartet und offen gelassen; Sicht-/Terminal-Abnahme offen |
| [014 MCP-Transportgrenzen](../specs/014-lokale-mcp-transportgrenzen/SPEC.md) | Done | gemeinsame HTTP-Grenzen implementiert; 97 Rust-Tests und 28 Vergleichsszenarien grün, App/Sidecars aktualisiert, Live-Smoke grün |
| [015 Workspace/Projekterkennung](../specs/015-workspace-projekterkennung/SPEC.md) | Backlog | D-MR-01 bestätigt: Repos separat erkennen, frei gruppierbar; Umsetzung offen |
| [016 Gemeinsames Spec-Register](../specs/016-gemeinsames-spec-register/SPEC.md) | Backlog | D-TEAM-01 bestätigt: separates Spec-Repo als Pilot; Umsetzung offen |
| [017 Demoaktionen](../specs/017-projektaktionen-fuer-demo/SPEC.md) | Doing | fünf Projektaktionen und Tests-Knopf, Live-Dateiänderung ohne Neustart; Sichtabnahme offen |
| [018 Ausgabetabs](../specs/018-aktionsausgabe-seitenleiste/SPEC.md) | Doing | Aktionsausgaben rechts neben Inspektor; UI-Tests grün, lokale App aktualisiert und Projektfenster wieder geöffnet; Sichtabnahme offen |
| [019 Farbkonzept](../specs/019-farbkonzept/SPEC.md) | Doing, ready, needs_human | Navigation, Board, Dateisymbole für Hell/Dunkel; Kontrast-/UI-Tests grün, in lokaler App sichtbar |
| [020 Spec-Navigation](../specs/020-spec-navigation/SPEC.md) | Doing, ready, needs_human | Gesamtliste, Suche/Filter, Altbestand lesbar, pfadgenaue Historie und Policy v5; 107 Rust-Tests/vier UI-Suiten grün, lokale App aktualisiert |
| [021 Git-Arbeitsbereich](../specs/021-git-arbeitsbereich/SPEC.md) | Backlog | Commit-Composer auffindbar machen, Branch-Verwaltung und IDE-artige Anordnung |
| [022 Dateien/Refactoring](../specs/022-dateiauswahl-und-refactoring/SPEC.md) | Backlog | Ordnerauswahl und Kontextmenü; später sicherer Move und sprachbezogene Refactorings |

## Verifikation und verbleibende Risiken

**Nachtrag 020, 2026-09-10 18:37 UTC:** App PID 80479 auf 18768 aktualisiert und
offen; Fenster speccify/AVC wiederhergestellt. Native Sichtprüfung: 54/54 Specs
in der Gesamtliste, kein Archiv-Bedienweg. Policy-Diagnose current/v5, 107 Rust-
Tests bestanden/2 ignoriert, vier Browser-Suiten und Builds grün. Terminal-
Übernahmekonflikt unverändert offen (009). Zwischenstand b5764e1 gepusht, Website
deployed; drei CI-Plattformfehler gezielt korrigiert, Remote-Nachprüfung folgt.

**Nachtrag 019, 2026-09-10 18:14 UTC:** Farbschnitt lokal gebaut und gestartet,
PID 54016 auf 18768; native Fensterliste und gezielter Screenshot bestätigen
Speccify-Hauptfenster und Projekte speccify/AVC passend zur aktuellen gespeicherten
Liste. Drei Browser-UI-Suiten, neue Akzentkontraste, Typecheck, Build und Live-HTTP-
Smoke bestanden. Kein Zugriffsdialog im geprüften Projektfenster. Terminal zeigt
eine bereits in anderer App geöffnete Conversation; kein Nachweis nahtloser
Sitzungsfortsetzung, keine automatische Übernahme. 019 zur menschlichen Abnahme.

**Neue UI-Findings:** [UI-Konzept](ui-gestaltung.md) und Specs 019–022 trennen
erste Farbänderungen von noch ausstehender Interaktion. Spec 020 liefert nun
die Gesamtliste ohne Archiv-Bedienweg; Altbestand bleibt ohne Umzug lesbar.
Projektübergreifende Sortierung folgt nach 015/016. Branch-Wechsel/-Anlegen und Commit-Nachrichten existieren
bereits im Inspektor, sind zu versteckt. Ordner sind bisher nur aufklappbar;
Ordnerauswahl, Kontextmenü und semantische Refactorings sind noch nicht geliefert.

**Nachtrag 008, 2026-09-10 17:15 UTC:** Workflow-Konsistenz implementiert;
105 Rust-Tests bestanden, 2 ignoriert (davon explizite Repo-Diagnose separat
bestanden). Workflow-UI und bisherige Ausgabetabs in isolierten Browser-Tests
grün; Typecheck, Format, Build und Live-HTTP-Smoke grün. Neue lokale App PID
30441 auf 18768 offen, wartet aber sichtbar auf macOS-Freigabe für den Ordner
Schreibtisch. Drei gespeicherte Projektpfade erhalten; Wiederaufnahme der
Fenster und exakte Terminal-Fortsetzung noch nicht bestätigt. Systemdialog
nicht automatisch bestätigt; menschliche Abnahme offen. Details in Spec 008.

**Nachtrag 013, 2026-09-10 12:43 UTC:** Lokale App unter
`target/debug/bundle/macos/Speccify.app`, PID 37974, auf Loopback-Port 18768
gestartet. Kein Vite-/Rust-Watcher. Initialize/initialized/tools-list erfolgreich;
Wiederöffnen behält dieselbe PID. Lima auf 8768 nicht verändert. 7 Script-Tests,
61 Desktop-Rust-Tests (1 ignoriert), Typecheck/Build und Formatprüfungen grün.
Menschliche Sicht- und Agent-Terminal-Abnahme bleibt offen. Vor späterer Arbeit
Status erneut prüfen; eine hier genannte PID ist nur die damalige Beobachtung.

Übernommene Prüfergebnisse vom 2026-09-10, Details und Grenzen in 006/007:

- Python-Basis: 216 Tests bestanden, ein Test abgewählt; keine neue vollständige
  Python-Suite für diesen reinen Dokumentationsschritt ausgeführt.
- Desktop-Rust nach 007: 59 Tests bestanden, ein bestehender Test ignoriert;
  Formatprüfung bestanden. Starttests verwenden isolierte Shell-Profile/Fake-Binaries.
- Frontend-Typecheck und Build bestanden; bestehende Vite-Warnung zu großem Chunk.
- `dev.sh`-Syntax und `--check` bestanden. Frischer Installations-Fixture:
  `pnpm install --frozen-lockfile`, esbuild-Transformation und sharp-PNG-Erzeugung bestanden.
- **Nicht abgenommen:** Start aus Finder mit realem Host, zweiter Mac, Windows-
  Oberfläche, exakte Session-Fortsetzung und kompletter Board-/Skill-/Tool-Roundtrip.
  Auch installierte Release-Updates wurden nicht durchgespielt.

Zur ursprünglichen Setup-Frage: **esbuild und sharp sind keine alternativen
Buildsysteme.** Die Abfrage betraf Buildskript-Freigaben von Abhängigkeiten.
Der lokale Stand erlaubt beide ausdrücklich, pinnt pnpm auf `10.33.3`, setzt
Node mindestens `22.12.0` und nutzt strikte/frozen Installationen. Unbekannte
Buildskripte bleiben gesperrt. Das ist erst nach Übernahme dieser Änderungen
auch im Checkout des Kollegen wirksam.

Noch relevante Befunde:

- GitHub meldete beim Push von b5764e1 am 2026-09-10 insgesamt 47 Dependabot-
  Warnungen (2 kritisch, 21 hoch, 16 mittel, 8 niedrig). Paket-/Laufzeitbetroffenheit
  und Upgradepfade noch separat zu prüfen; kein ungeprüftes Sammel-Upgrade im UI-Schnitt.
  [Repository-Sicherheitsübersicht](https://github.com/mhennemeyer/speccify/security/dependabot).

- Globale Speccify-CLI im Basisbefund veraltet; Workspace-Runtime verwenden.
  007 priorisiert Projekt-venv, installierte Engine, dann Login-Shell-PATH.
- Eigenes Repo ist seit Spec 020 auf Policy v5 und versionierten Workflow-Skills;
  Diagnose prüft Linkziele und bewahrt Anpassungen. Alte status/resume-Dokumente
  tragen einen Historienhinweis und sind keine aktuelle Anweisung.
- Aufgaben folgen nativ Markdown-Tasklisten, auch außerhalb Tasks; Codebeispiele
  werden ignoriert. Klick-Konflikte laden neu. Das ersetzt keine atomare Sperre
  gegenüber gleichzeitig schreibenden externen Programmen.
- Sitzungsmerker ist keine Session-ID; `--last`/`--continue` beweisen nicht die
  beabsichtigte Sitzung. Dashboard und Projektstart sind noch nicht gleich robust.
- PTY-Ausgabe dekodiert UTF-8 derzeit pro Chunk; geteilte Zeichen bleiben ein Risiko.
- `verify`-Warnungen zu fehlenden Tools werden zwischen CLI/MCP/UI nicht vollständig
  gleich transportiert. Lock-Konsistenz ist nicht Plattform-Ausführbarkeit.
- Fehlende Implementierungen im Basisbefund: `build-libgit2`, `verify-signatures`,
  `verify-stream`. Keine Signierungs- oder Tool-Reparatur durch dieses Playbook.
- Neue Multi-Repo-Sicht darf diese lokalen Zustände nicht fälschlich als gemeinsame
  Team-Wahrheit ausgeben. Die aktuelle App liest den jeweiligen Arbeitsbaum.
- Spec 014 behebt die zuvor fehlende Origin-/Host-Abweisung im gemeinsamen
  Rust-MCP-HTTP-Handler; nach Update erhält der Negativtest 403. Native Clients
  funktionieren weiter. Noch keine lokale Client-Authentifizierung oder
  umfassenden Header-/Verbindungs-/Slow-client-Limits; Browserfreigaben bleiben leer.

## Vorgeschlagener UI-Ausbau — nicht implementiert

Die Produktentscheidungen für anpassbare Repo-Gruppierung und ein separates
gemeinsames Spec-Repo sind seit 2026-09-10 bestätigt (D-MR-01/D-TEAM-01).
Die nachfolgende UI und die entsprechenden Fähigkeiten sind noch nicht umgesetzt.

Die bestehende Navigation zunächst erhalten und projektbezogen erweitern;
die Platzierung neuer Bereiche ist ein Diskussionsvorschlag, kein finales UI-Design.

```text
Workspace-Fenster
├── Workspace-/Projektumschalter: Alle / Projekt A / Projekt B
├── bestehende Bereiche mit Projekt-/Repo-/Quellenkennzeichnung
│   ├── Specs: gemeinsame Sicht · Filter · Branch/PR/Sync/Abnahmebezug
│   ├── Dateien/Git: Projekt → Repository → Worktree
│   └── Playbooks/Skills: Eigentümer · Herkunft · Source/Target
├── Integrationen
│   ├── itsdcloud: lokale Verbindung · Projektbindung · Gedächtnis · Aktualität
│   │   └── Berechtigungen · Kontextvorschau · bestätigte Entwicklungsnotizen
│   └── später weitere Adapter, z. B. iKanban
├── Feedback
│   ├── Liste/Suche/Filter → Detail/Kommentare/Duplikat/Status
│   └── Composer mit kontrollierbarer Kontextvorschau
├── Aktionen → Ad-hoc-Panel (z. B. Profiling, Echtzeitdiagramme, Stop)
├── Agent-Terminal mit sichtbarem Projekt-/Auftragskontext und Session-Identität
└── übergreifend
    ├── Rechtsklick auf unterstützte Fläche → Feedback → gleicher Composer
    ├── Update-Hinweis → Details/Download → koordinierter Neustart
    └── Offline-/Sync-/Konfliktzustände ohne Verlust lokaler Arbeit
```

Vision 2 ergänzt Workflow-Herkunft und Fähigkeitshinweise für OpenSpec/Spec Kit
sowie Skill-Import-/Exportprofile. Sie benötigt keine vorgezogene Umschreibung
der heutigen `.agent`-Struktur.

## Pflegecheck

Bei der nächsten Änderung prüfen: Sind alle Dashboard-Seiten, Projekt-Tabs,
Dialogsichten und Platzhalter noch richtig eingeordnet? Wurde aus einem
Platzhalter eine echte Fähigkeit? Wurde die Spec wirklich abgenommen? Stimmen
DE/EN-Hilfe und App überein? Neue Erkenntnisse im Bestandsbuch festhalten,
Zieländerungen im Visionsbuch, Prüfergebnisse in der betroffenen Spec.

Dokumentationsprüfung am 2026-09-10: lokale Markdown-Links und geschlossene
Codeblöcke geprüft, alle neun V1- und beide V2-Punkte im Visionsbuch vorhanden;
Spec-Stationen gegen Frontmatter abgeglichen. Der UI-Baum wurde gegen Navigation,
Views und gemeinsame Komponenten gelesen; keine neue visuelle Abnahme durchgeführt.
