# Die Speccify-App bedienen

Diese Seite ist die Anleitung für die Desktop-App. Sie wird in der App
selbst angezeigt (Bereich *Hilfe*) und lebt als normale Markdown-Datei im
Repository — wer etwas ändern will, ändert diese Datei.

## Der schnelle Weg

1. **Projekt öffnen.** Im Dashboard unter *Projekte* das Projektverzeichnis
   wählen (oder einen Eintrag aus *Zuletzt geöffnet*). Jedes Projekt bekommt
   ein eigenes Fenster; offene Fenster kommen nach einem Neustart wieder.
2. **Einrichten.** Zeigt das Fenster oben einen gelben Workflow-Banner,
   einmal **Einrichten** klicken: Das legt die Workflow-Regeln in
   `.agent/agent.md`, die Skills `/ticket-next` und `/ticket-ask`, die
   Ordner `.agent/board` und `.agent/plans` sowie die Skill-Links für
   Claude Code und Codex an. Bestehendes wird nie überschrieben.
3. **Agent starten.** In der Leiste unten das Agent-Terminal starten:
   `Claude`, `Codex` oder ein freies Kommando; leer = nur Shell. Lief hier
   schon eine Sitzung, wird sie beim nächsten Öffnen von selbst fortgesetzt.
4. **Plan schreiben, Board arbeiten lassen.** Unter *Orga → Pläne* einen
   Plan anlegen (**+ Plan**), schreiben und **Aktivieren**. Dann dem Agenten
   im Terminal sagen: *„Folge dem Board-Workflow"* (oder `/ticket-next`).
   Er schneidet Tickets aus dem Plan und arbeitet sie einzeln ab — das
   Board zeigt alles live.

## Der Aufbau des Projektfensters

Das Fenster folgt dem Muster von Xcode und iKanban: **Navigator** links,
**Inhalt** in der Mitte, **Inspektor** rechts, **Agent-Terminal** unten,
**Toolbar** oben.

- **Navigator.** Oben eine Icon-Leiste mit fünf Bereichen — **Dateien**
  (Dateien, Git), **Orga** (Playbooks, Pläne, Skills), **Technik** (Tools,
  Aktionen, MCPs, Agent), **Board** und **Hilfe**; der Tooltip nennt den
  Namen und das Kürzel. Hat ein Bereich mehrere Tabs, stehen sie als
  zweite Zeile darunter; die App merkt sich je Bereich den zuletzt
  gewählten. Unter den Tabs die Liste des aktiven Tabs. Ist eine Liste
  leer, sagt die Seitenleiste, was fehlt, und bietet den nächsten Schritt
  an: „+ Plan", „+ Ticket", „Quellen durchsuchen", `git init` oder einen
  Prompt für den Agenten.
- **Inhalt.** Das Ausgewählte in voller Breite: das Board, ein Plan als
  Dokument, eine Datei im Editor, ein Diff.
- **Inspektor.** Zu allem, was links ausgewählt ist, Metadaten und die
  passenden Knöpfe — beim Ticket die Tabs *Übersicht* (Fragen und
  Beschreibung) und *Historie*, beim Plan Lifecycle, Status, Aktivieren,
  Archivieren, beim Skill die Herkunft, beim Tool die Plattform-Stände,
  bei der Aktion den letzten Lauf und *Ausführen*, im Git-Tab das
  Commit-Panel. Ist der Inspektor ausgeblendet, erscheint dasselbe als
  Kasten über dem Inhalt.
- **Agent-Terminal.** Unten unter dem Inhalt, höhenverstellbar; wer es
  lieber rechts hat, legt es mit *nach rechts* als zweiten Tab in die
  rechte Seitenleiste.
- **Toolbar.** Links der Projektname. In der Mitte die **Knöpfe**:
  eingebaute (*Pull*, *Push*, *Commit*, *Agent*) und Aktionen aus
  `.agent/actions.json` (im Aktionen-Tab mit *Toolbar* markiert, ein
  Klick startet sie). Welche Knöpfe in welcher Reihenfolge stehen, stellst
  Du im Zahnrad unter *Toolbar* ein — pro Projekt gemerkt. Daneben die
  **Aktivitätsanzeige**: was gerade läuft — eine Aktion, `git push`, das
  Einrichten, ein Speichern, das Agent-Terminal, solange Ausgabe fließt —
  mit Laufzeit; abgeschlossene Agent-Läufe aus der Ticket-History
  erscheinen mit Ticket und Tokens; ein Klick öffnet die Liste. Rechts
  die Schalter für Navigator, Terminal und Inspektor, Sonne/Mond für
  Hell/Dunkel und das Zahnrad für die Einstellungen. Auf macOS ist die
  Toolbar zugleich die Titelleiste; das Fenster lässt sich an ihr ziehen.

Alle Bereiche lassen sich am Rand ziehen (Doppelklick auf den Griff setzt
die Standardbreite zurück). Breiten, Sichtbarkeiten und Terminal-Position
merkt sich die App pro Projekt, auch über einen Neustart hinaus.

**Tastaturkürzel** (Windows: Strg statt ⌘): ⌘1 Dateien, ⌘2 Orga, ⌘3
Technik, ⌘4 Board, ⌘5 Hilfe; ⌘0 Navigator, ⌥⌘0 Inspektor, ⇧⌘Y Terminal
unten; im Editor ⌘S speichern, im Commit-Feld ⌘⏎ committen.

## Die Bereiche und ihre Tabs

### Dateien

- **Dateien** — der Projektbaum (`.gitignore` gilt, `.git` bleibt zu;
  Ordner laden beim Aufklappen, oben ein Namensfilter). Ein Klick öffnet
  die Datei als Tab über einem Code-Editor mit Syntaxfarben für Markdown,
  TypeScript, Python, Rust, JSON, YAML, HTML und CSS; Suche mit ⌘F.
  **⌘S speichert**, ein Punkt am Tab zeigt Ungespeichertes; jeder
  Tastenanschlag wird als Entwurf gesichert und kommt nach einem Neustart
  zurück. Der Inspektor nennt Größe, Zeilen, Änderungsdatum und
  Cursorzeile und bietet *Speichern*, *Verwerfen*, *Als Prompt kopieren*
  (mit `Pfad:Zeile`) und *Pfad kopieren*; sein Tab **Historie** listet die
  Commits, die die Datei berührt haben — ein Klick zeigt den Diff dieses
  Commits für genau diese Datei, *als Prompt* kopiert ihn. Im Tab *Datei*
  schaltet **Blame am Rand** Commit und Autor je Zeile im Editor ein;
  *Umbenennen…* und *Löschen…* (in den Papierkorb, zweiter Klick
  bestätigt) stehen daneben, **+ Datei** / **+ Ordner** oben im Navigator
  legen Neues an. Der Schalter **Suchen** im Navigator durchsucht
  Dateiinhalte (`Aa` = Groß/Klein, `.*` = regulärer Ausdruck,
  `.gitignore` gilt); ein Treffer öffnet die Datei an der Zeile. Genauso
  ist `pfad:zeile` in der Terminal-Ausgabe ein Link in den Editor (⌘-Klick
  bzw. Strg-Klick). Ändert der Agent eine offene, ungeänderte Datei, lädt
  sie nach.
- **Git** — Branch mit Upstream und ↑↓-Zählern, dazu *fetch*, *pull*,
  *push* mit Live-Ausgabe. Darunter die geänderten Dateien in *Staged* und
  *Änderungen*; **+** und **−** an der Zeile (oder *alle +* / *alle −*)
  stagen und entstagen. Ein Klick auf eine Datei zeigt ihren Diff — jeder
  Block hat **Hunk stagen** bzw. **Hunk zurücknehmen**, so wandern nur die
  Zeilen in den Commit, die zusammengehören. Der Inspektor nennt den
  Zustand mit *Stagen*, *Im Editor öffnen*, *Diff als Prompt* und
  *Verwerfen…* (zweiter Klick bestätigt; unversionierte Dateien werden
  gelöscht) und hat die Tabs **Änderungen** und **Historie** (Commits
  dieser Datei; ein Klick zeigt den Diff des Commits). Ein Klick auf einen
  Commit in *Letzte Commits* öffnet ihn im Inspektor: Dateiliste (Klick =
  Diff nur dieser Datei), Nachricht, *Hash kopieren*, *Diff als Prompt*.
  **Committen** im Inspektor (*Commit…* im Branch-Kopf springt hin):
  Nachricht schreiben und *Commit* (⌘⏎), *Alles committen* staged vorher
  alles, oder *Agent committen lassen* — der Auftrag landet im
  Agent-Terminal, dort mit Enter bestätigen, der Agent liest den Diff,
  schreibt die Nachricht und committet. Der Tab **Branches** daneben
  wechselt per Klick und legt mit *Anlegen* einen neuen an. Läuft über das
  installierte `git`;
  Zugangsdaten und SSH-Agent funktionieren wie im Terminal. Ohne
  Repository: `git init` per Knopf. Der Tab liest den Status beim
  Einblenden und alle paar Sekunden nach.

### Orga

- **Playbooks** — stehende Anleitungen aus `.agent/playbooks/` (Release,
  Deploy, Onboarding …). Anders als Pläne werden sie nicht abgearbeitet,
  sondern immer wieder benutzt. **+ Playbook** legt eins an, *Als Prompt
  kopieren* gibt den Ablauf dem Agenten ins Terminal.
- **Pläne** — alle Pläne aus `.agent/plans/`, das Archiv aufklappbar.
  **+ Plan** legt einen Entwurf an. **Aktivieren** macht einen Plan zum
  aktiven und parkt den bisherigen auf `onHold`; **Archivieren**
  verschiebt einen fertigen Plan nach `.agent/plans/archive/`. Ein rotes
  Banner heißt: Der Agent hat den Plan eskaliert — lesen, handeln,
  **Auflösen**. *Als Prompt kopieren* gibt Pfad und Inhalt dem Agenten.
- **Skills** — die expandierten Skills des Projekts samt Herkunft. Der
  Modus **Quellen durchsuchen** zeigt Skill-Repos: globale aus der
  Dashboard-**Bibliothek** und weitere nur für dieses Projekt (**+ Quelle**
  nimmt eine Git-URL — GitHub, GitLab, auch privat — oder einen Ordner).
  Git-Quellen werden einmal nach `~/.speccify/sources/` geklont und mit
  **Aktualisieren** nachgezogen; den Zugang regelt dasselbe `git` wie im
  Terminal (Credential-Helper oder SSH-Schlüssel). Ordner sind
  Kategorien, die Mitte die Vorschau, **Importieren (expand)** im Inspektor
  tippt das passende `speccify`-Kommando ins Agent-Terminal — dort mit
  Enter bestätigen. Das `add --source` darin merkt sich die Quelle in
  `speccify.yaml`, spätere `verify`/`expand`-Läufe brauchen keinen Pfad.
  Umgekehrt bringt **Exportieren…** im Inspektor eines Projekt-Skills ihn
  als allgemeinen Skill in eine Quelle: Quelle und
  Ordner wählen, `speccify export` landet im Terminal, streicht „In this
  project", setzt Version und Scope, nimmt Tools als Vertrag mit und
  listet Stellen, die noch projektspezifisch aussehen. Committen und
  Pushen passiert danach im Quell-Checkout — per Git-Tab oder Agent.

**Bearbeiten:** *Bearbeiten* im Inspektor oder **Doppelklick** auf den
Listeneintrag oder den Inhalt. Der Editor speichert von selbst — jeder
Tastenanschlag landet sofort als Entwurf im App-Speicher, gut eine
Sekunde nach dem Tippen in der Datei; *Fertig* schließt ihn. Wird die App
mitten im Schreiben beendet, bietet der Plan beim nächsten Öffnen
*Wiederherstellen* an.

### Technik

- **Tools** — die Tool-Verträge (`TOOL.md`) mit Status je Plattform.
  „Fehlt auf dieser Plattform" heißt: den Agenten bitten, die
  Implementierung zu schreiben; `speccify tool check <name>` verifiziert.
- **Aktionen** — benannte Projekt-Kommandos aus `.agent/actions.json`.
  *Ausführen* startet sie direkt in der App, mit Live-Ausgabe, Stop und
  Fortschritt; eine Ausgabezeile im Chart-Format wird als Diagramm
  gezeichnet. *Toolbar* legt die Aktion als Knopf in die Toolbar.
  Vorschläge des Agenten (auch abgelehnte Kommandos aus `exec-pending`)
  werden mit einem Klick bestätigt und freigegeben.
- **MCPs** — die projektbezogenen MCP-Server (`.mcp.json` für Claude,
  `.codex/config.toml` für Codex) und die Claude-Allowlist. Ohne Server
  kopiert ein Knopf einen Prompt, mit dem der Agent einen einträgt; global
  verwaltet das Dashboard die Server.
- **Agent** — `CLAUDE.md`, `AGENTS.md` und `.agent/agent.md` des
  Projekts, dazu das Agent-Kommando fürs Terminal.

### Board

Die Tickets aus `.agent/board/` in drei Spalten (Backlog, In Progress,
Done). Karten lassen sich ziehen; ein Klick zeigt das Ticket im Inspektor,
ein **Doppelklick** öffnet den Ticket-Editor. **+ Ticket** legt neue an.
Über dem Board ist der aktive Plan aufklappbar; die Kopfzeile zeigt Läufe
und Token-Verbrauch des Agenten. Im Navigator filtert die Liste nach
Plan, der Filter **braucht mich** blendet alles aus, was nicht auf Dich
wartet.

### Hilfe

Diese Anleitung und die weiteren eingebauten Dokumente; der Inspektor
nennt die Quelldatei im Repository.

## Fragen beantworten

Wenn der Agent eine Entscheidung braucht und der Lauf endet, schreibt er
die Frage ins Ticket. Die App meldet das als System-Benachrichtigung, die
Karte bekommt ein orangefarbenes **?**, und im Inspektor steht die Frage
ganz oben mit einem Antwortfeld. Antworten — der nächste Lauf des Agenten
liest sie aus der Datei.

## Einstellungen und Neustart

Das Zahnrad in der Toolbar öffnet die **Einstellungen** des
Projektfensters: Erscheinungsbild (System, Hell, Dunkel — gilt für alle
Fenster, auch im Dashboard unter *Settings*), Terminal-Position,
„Agent-Sitzung nach Neustart fortsetzen", die **Toolbar-Knöpfe** (an- und
abwählen, mit den Pfeilen sortieren) und „Layout zurücksetzen".

**Die Agent-Sitzung überlebt den Neustart:** Lief in einem Fenster ein
Agent, startet das Terminal beim nächsten Öffnen von selbst mit
`claude --continue` bzw. `codex resume --last` — der Agent liest sein
eigenes Protokoll und macht dort weiter, wo er war; nur ein gerade
laufender Werkzeugaufruf ist verloren. Abgeschaltet bietet das Terminal
*Letzte Sitzung fortsetzen* und *Neu starten*. Das Dashboard-Terminal
macht es genauso (*Settings → Agent-Sitzung*).

## Das Dashboard

- **Projekte** — Projekte in eigenen Fenstern öffnen.
- **Bibliothek** — die Skill-Bibliothek durchsehen.
- **Umgebung** — Python-Engine und Werkzeug-Checks (Doctor); hier steht,
  was fehlt und wie es installiert wird.
- **Server** — die lokalen MCP-Server starten/stoppen.
- **Agents** — die globale Konfiguration von Claude Code und Codex
  editieren (Settings-Dateien und globale Anweisungen).
- **Bibliothek** — oben die **Skill-Quellen** für alle Projekte (Git-URL
  oder Ordner; hinzufügen, aktualisieren, entfernen), darunter die
  Toolbox-Manifeste.
- **Settings** — Erscheinungsbild, Agent-Sitzung, Working Dir und
  Terminal-Autostart.

## Wenn etwas nicht geht

- **Der Banner sagt „CLAUDE.md verweist nicht auf .agent/agent.md".**
  Die Datei existiert schon und die App fasst sie nicht an — den Verweis
  (`@.agent/agent.md`) selbst ergänzen.
- **Ein Board oder Tab wirkt veraltet.** Die App liest die `.agent`-
  Bereiche alle zwei Sekunden nach, den Git-Status alle vier; wenn nicht,
  Tab wechseln und zurück — und den Fall bitte melden.
- **`speccify` fehlt im Terminal.** Im Repository `uv sync --all-packages`
  ausführen oder die Umgebung im Dashboard einrichten.
- **Eine Aktion startet nicht.** Kommandos laufen ohne Shell — `&&`,
  Pipes und `$(…)` funktionieren nicht; Verkettungen gehören in ein
  Skript, das die Aktion aufruft.
- **Git meldet „nicht startbar".** Git ist nicht installiert oder nicht im
  PATH — die App nutzt das System-`git`.
