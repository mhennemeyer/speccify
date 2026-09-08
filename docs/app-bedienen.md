# Die Speccify-App bedienen

Diese Seite ist die Anleitung für die Desktop-App. Sie wird in der App
selbst angezeigt (Hilfe-Bereich) und lebt als normale Markdown-Datei im
Repository — wer etwas ändern will, ändert diese Datei.

## Der schnelle Weg

1. **Projekt öffnen.** Im Dashboard unter *Projekte* das Projektverzeichnis
   wählen (oder einen Eintrag aus *Zuletzt geöffnet*). Jedes Projekt bekommt
   ein eigenes Fenster.
2. **Einrichten.** Zeigt das Fenster oben einen gelben Workflow-Banner,
   einmal **Einrichten** klicken: Das legt die Workflow-Regeln in
   `.agent/agent.md`, die Skills `/ticket-next` und `/ticket-ask`, die
   Ordner `.agent/board` und `.agent/plans` sowie die Skill-Links für
   Claude Code und Codex an. Bestehendes wird nie überschrieben.
3. **Agent starten.** In der Leiste unten (oder als Tab in der rechten
   Seitenleiste — umschaltbar) das Agent-Terminal starten. `Claude`, `Codex` oder ein freies Kommando; leer = nur Shell.
4. **Plan schreiben, Board arbeiten lassen.** Einen Plan unter *Pläne*
   anlegen oder editieren und auf **active** setzen. Dann dem Agenten im
   Terminal sagen: *„Folge dem Board-Workflow"* (oder `/ticket-next`).
   Er schneidet Tickets aus dem Plan und arbeitet sie einzeln ab — das
   Board zeigt alles live.

## Der Aufbau des Projektfensters

Das Fenster folgt dem Muster von Xcode: links der **Navigator** — oben
eine Icon-Leiste mit den fünf Bereichen **Board**, **Dateien**, **Orga**
(Playbooks, Pläne, Skills), **Technik** (Tools, Aktionen, MCPs, Agent) und
**Hilfe**;
der Tooltip nennt den Namen. Hat ein Bereich mehrere Tabs, stehen sie
als zweite Zeile darunter, und die App merkt sich je Bereich den zuletzt
gewählten. Unter den Tabs die Liste des aktiven Tabs: Pläne, Playbooks,
Skills, Tools, Aktionen, Hilfe-Dokumente, im Board ein Filter nach Plan.
In der Mitte der Inhalt des Ausgewählten, rechts der **Inspektor**: Zu
allem, was links ausgewählt ist, zeigt er Metadaten und die passenden
Knöpfe — beim Ticket die Tabs *Übersicht* (Fragen und Beschreibung) und
*Historie*, beim Plan Lifecycle, Status, Aktivieren, Archivieren, beim
Skill die Herkunft, beim Tool die Plattform-Stände, bei der Aktion den
letzten Lauf und „Ausführen". Ist der Inspektor ausgeblendet, erscheint
dasselbe als Kasten über dem Inhalt. Ist eine Liste leer, sagt die
Seitenleiste, was fehlt, und bietet den nächsten Schritt an: „+ Plan",
„+ Ticket", „Quellen durchsuchen" oder einen Prompt für den Agenten.

Die **Toolbar** oben trägt links den Projektnamen, in der Mitte die
**Aktions-Knöpfe** (jede Aktion aus `.agent/actions.json` lässt sich im
Aktionen-Tab mit *Toolbar* dorthin legen; ein Klick startet sie, mit
Eingaben springt sie in den Aktionen-Tab) und die **Aktivitätsanzeige**:
Was gerade läuft — eine Aktion, das Einrichten, ein Speichern, das
Agent-Terminal, solange Ausgabe fließt — mit Laufzeit; abgeschlossene
Agent-Läufe aus der Ticket-History erscheinen mit Ticket und Tokens.
Ein Klick öffnet die Liste der letzten Aktivitäten. Tastaturkürzel wie
in Xcode: ⌘0 Navigator, ⌥⌘0 Inspektor, ⇧⌘Y Terminal unten, ⌘1 bis ⌘5
die Bereiche (Windows: Strg statt ⌘). Rechts die
Schalter für die Bereiche, Hell/Dunkel und die Einstellungen. Auf macOS
ist die Toolbar zugleich die Titelleiste (die Ampel schwebt links darüber);
das Fenster lässt sich an ihr ziehen.

Offene Projektfenster merkt sich die App über einen Neustart: Was beim
Beenden offen war, öffnet sich beim nächsten Start wieder. Ein bewusst
geschlossenes Fenster (roter Knopf, Cmd-W) bleibt zu. **Die
Agent-Sitzung überlebt den Neustart mit:** Lief in einem Fenster ein
Agent, startet das Terminal beim nächsten Öffnen von selbst mit
`claude --continue` bzw. `codex resume --last` — der Agent liest sein
eigenes Protokoll und macht dort weiter, wo er war; nur ein gerade
laufender Werkzeugaufruf ist verloren. In den Einstellungen abschaltbar;
dann bietet das Terminal *Letzte Sitzung fortsetzen* und *Neu starten*. Das **Agent-Terminal** lebt in einer Leiste unten
unter dem Inhalt; wer es lieber rechts hat, legt es mit dem Knopf *nach
rechts* im Terminal als zweiten Tab in die rechte Seitenleiste.
Alle drei Bereiche lassen sich am Rand ziehen (Doppelklick auf den Griff
setzt die Standardbreite zurück) und über die drei Schalter rechts oben
in der Toolbar ein- und ausblenden. Ist der Inspektor zu, erscheint das
Ticket-Detail wie früher unter dem Board. Breiten und Sichtbarkeiten
merkt sich die App pro Projekt, auch über einen Neustart hinaus.

Sonne/Mond rechts in der Toolbar schaltet direkt zwischen Hell und
Dunkel. Das Zahnrad daneben öffnet die **Einstellungen**: Erscheinungsbild
(System, Hell, Dunkel — gilt für alle Fenster, auch im Dashboard unter
*Settings*), Terminal-Position und „Layout zurücksetzen".

## Die Tabs im Projektfenster

- **Board** — die Tickets aus `.agent/board/` in drei Spalten (Backlog,
  In Progress, Done). Karten lassen sich ziehen; ein Klick öffnet das
  Ticket-Detail mit Beschreibung, Fragen und History im Inspektor. **+ Ticket** legt
  neue an, *Bearbeiten* öffnet das Formular. Über dem Board ist der aktive
  Plan aufklappbar; die Kopfzeile zeigt Läufe und Token-Verbrauch des
  Agenten. Der Filter **braucht mich** blendet alles aus, was nicht auf
  Dich wartet.
- **Dateien** — der Projektbaum im Navigator (`.gitignore` gilt, `.git`
  bleibt zu; Ordner laden beim Aufklappen, oben ein Namensfilter). Ein
  Klick öffnet die Datei als Tab über einem Code-Editor (CodeMirror:
  Syntaxfarben für Markdown, TypeScript, Python, Rust, JSON, YAML, HTML,
  CSS; Suche mit Cmd/Ctrl-F). **Cmd/Ctrl-S speichert**, ein Punkt am Tab
  zeigt Ungespeichertes. Der Inspektor nennt Größe, Zeilen, Änderungsdatum
  und Cursorzeile und bietet *Speichern*, *Verwerfen*, *Als Prompt
  kopieren* (mit `Pfad:Zeile`) und *Pfad kopieren*. Ändert der Agent eine
  offene, ungeänderte Datei, lädt sie nach.
- **Git** (im Bereich Dateien) — Branch mit Upstream und ↑↓-Zählern, dazu
  *fetch*, *pull*, *push* mit Live-Ausgabe (und Eintrag in der
  Aktivitätsanzeige). Darunter die geänderten Dateien in *Staged* und
  *Änderungen*; **+** und **−** an der Zeile (oder *alle +*/*alle −*)
  stagen und entstagen. Ein Klick auf eine Datei zeigt ihren Diff in der
  Mitte, der Inspektor den Zustand mit *Stagen*, *Im Editor öffnen* und
  *Diff als Prompt*. **Committen** im Inspektor (Knopf *Commit…* im
  Branch-Kopf springt hin): Nachricht schreiben und *Commit* (⌘⏎), *Alles
  committen* staged vorher alles, oder *Agent committen lassen* — der
  Auftrag landet im Agent-Terminal, dort mit Enter bestätigen, der Agent
  liest den Diff, schreibt die Nachricht und committet. Die letzten
  Commits stehen in der Mitte. Läuft alles über das installierte `git` — Zugangsdaten und
  SSH-Agent funktionieren wie im Terminal. Ohne Repository: *git init* per
  Knopf.
- **Playbooks** — stehende Anleitungen aus `.agent/playbooks/` (Release-
  Ablauf, Deploy, Onboarding …). Anders als Pläne werden sie nicht
  abgearbeitet und „fertig", sondern immer wieder benutzt. **+ Playbook**
  legt eins an, der Editor pflegt Beschreibung und Text, **Als Prompt
  kopieren** gibt den Ablauf dem Agenten ins Terminal.
- **Pläne** — Liste und Inhalt aller Pläne, mit Editor (Status-Felder und
  Text); **Doppelklick** auf den Listeneintrag oder den Inhalt öffnet ihn
  (ebenso bei Playbooks; ein Doppelklick auf eine Ticket-Karte öffnet den
  Ticket-Editor). **Der Editor speichert von selbst:** jeder Tastenanschlag landet
  sofort als Entwurf im App-Speicher, gut eine Sekunde nach dem Tippen in
  der Datei; *Fertig* schließt den Editor. Wird die App mitten im Schreiben
  beendet oder neu gestartet, bietet der Plan beim nächsten Öffnen
  *Wiederherstellen* an. Dasselbe gilt für Playbooks und den Code-Editor
  (dort bleibt ⌘S das Speichern, der Entwurf kommt beim Öffnen zurück).
  **Aktivieren** macht einen Plan zum aktiven und parkt den bisherigen
  automatisch auf `onHold`. **Archivieren** verschiebt einen
  fertigen Plan nach `.agent/plans/archive/` (lifecycle `done`); das
  Archiv ist in der Liste aufklappbar. Ein rotes Banner bedeutet: Der
  Agent hat den Plan eskaliert — lesen, handeln, **Auflösen**. **Als
  Prompt kopieren** gibt Pfad und Inhalt dem Agenten ins Terminal.
- **Skills** — die expandierten Skills des Projekts samt Herkunft. Der
  Modus **Quellen durchsuchen** zeigt Skill-Repos (Default aus den
  Dashboard-Settings, weitere pro Projekt): Ordner sind Kategorien,
  rechts die Vorschau, **Importieren (expand)** tippt das passende
  `speccify`-Kommando ins Agent-Terminal — dort mit Enter bestätigen.
- **Tools** — die Tool-Verträge (`TOOL.md`) mit Status je Plattform.
  „Fehlt auf dieser Plattform" heißt: den Agenten bitten, die
  Implementierung zu schreiben; `speccify tool check <name>` verifiziert.
- **Aktionen** — benannte Projekt-Kommandos aus `.agent/actions.json`.
  **Ausführen** startet sie direkt in der App, mit Live-Ausgabe, Stop und
  Fortschritt; eine Ausgabezeile im Chart-Format wird als Diagramm
  gezeichnet. Vorschläge des Agenten (auch abgelehnte Kommandos aus
  `exec-pending`) werden mit einem Klick bestätigt und freigegeben.
- **MCPs** — die projektbezogenen MCP-Server (`.mcp.json` für Claude,
  `.codex/config.toml` für Codex) und die Claude-Allowlist. Lesend;
  global verwaltet das Dashboard die Server.
- **Agent** — `CLAUDE.md`, `AGENTS.md` und `.agent/agent.md` des
  Projekts, dazu das Agent-Kommando fürs Terminal.

## Fragen beantworten

Wenn der Agent eine Entscheidung braucht und der Lauf endet, schreibt er
die Frage ins Ticket. Die App meldet das als System-Benachrichtigung, die
Karte bekommt ein orangefarbenes **?**, und im Ticket-Detail steht die
Frage ganz oben mit einem Antwortfeld. Antworten — der nächste Lauf des
Agenten liest sie aus der Datei.

## Das Dashboard

- **Projekte** — Projekte in eigenen Fenstern öffnen.
- **Bibliothek** — die Skill-Bibliothek durchsehen.
- **Umgebung** — Python-Engine und Werkzeug-Checks (Doctor); hier steht,
  was fehlt und wie es installiert wird.
- **Server** — die lokalen MCP-Server starten/stoppen.
- **Agents** — die globale Konfiguration von Claude Code und Codex
  editieren (Settings-Dateien und globale Anweisungen).
- **Settings** — Working Dir, Terminal-Autostart und die Default-Skill-
  Quelle.

## Wenn etwas nicht geht

- **Der Banner sagt „CLAUDE.md verweist nicht auf .agent/agent.md".**
  Die Datei existiert schon und die App fasst sie nicht an — den Verweis
  (`@.agent/agent.md`) selbst ergänzen.
- **Ein Board/Tab wirkt veraltet.** Die App liest alle zwei Sekunden nach;
  wenn nicht, Tab wechseln und zurück — und den Fall bitte melden.
- **`speccify` fehlt im Terminal.** Im Repository `uv sync --all-packages`
  ausführen oder die Umgebung im Dashboard einrichten.
- **Eine Aktion startet nicht.** Kommandos laufen ohne Shell — `&&`,
  Pipes und `$(…)` funktionieren nicht; Verkettungen gehören in ein
  Skript, das die Aktion aufruft.
