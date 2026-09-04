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
eine Icon-Leiste mit den Tabs (der Tooltip nennt den Namen), darunter
die Liste des aktiven Tabs: Pläne, Playbooks, Skills, Tools, Aktionen,
Hilfe-Dokumente, im Board ein Filter nach Plan. In der Mitte der Inhalt
des Ausgewählten, rechts der **Inspektor**, der das Detail zeigt — im
Board das angeklickte Ticket mit Beschreibung, Fragen und History. Das **Agent-Terminal** lebt in einer Leiste unten
unter dem Inhalt; wer es lieber rechts hat, legt es mit dem Knopf *nach
rechts* im Terminal als zweiten Tab in die rechte Seitenleiste.
Alle drei Bereiche lassen sich am Rand ziehen (Doppelklick auf den Griff
setzt die Standardbreite zurück) und über die drei Schalter rechts oben
in der Toolbar ein- und ausblenden. Ist der Inspektor zu, erscheint das
Ticket-Detail wie früher unter dem Board. Breiten und Sichtbarkeiten
merkt sich die App pro Projekt, auch über einen Neustart hinaus.

Das Zahnrad rechts in der Toolbar öffnet die **Einstellungen**:
Erscheinungsbild (System, Hell, Dunkel — gilt für alle Fenster, auch im
Dashboard unter *Settings*), Terminal-Position und „Layout zurücksetzen".

## Die Tabs im Projektfenster

- **Board** — die Tickets aus `.agent/board/` in drei Spalten (Backlog,
  In Progress, Done). Karten lassen sich ziehen; ein Klick öffnet das
  Ticket-Detail mit Beschreibung, Fragen und History im Inspektor. **+ Ticket** legt
  neue an, *Bearbeiten* öffnet das Formular. Über dem Board ist der aktive
  Plan aufklappbar; die Kopfzeile zeigt Läufe und Token-Verbrauch des
  Agenten. Der Filter **braucht mich** blendet alles aus, was nicht auf
  Dich wartet.
- **Playbooks** — stehende Anleitungen aus `.agent/playbooks/` (Release-
  Ablauf, Deploy, Onboarding …). Anders als Pläne werden sie nicht
  abgearbeitet und „fertig", sondern immer wieder benutzt. **+ Playbook**
  legt eins an, der Editor pflegt Beschreibung und Text, **Als Prompt
  kopieren** gibt den Ablauf dem Agenten ins Terminal.
- **Pläne** — Liste und Inhalt aller Pläne, mit Editor (Status-Felder und
  Text). **Aktivieren** macht einen Plan zum aktiven und parkt den
  bisherigen automatisch auf `onHold`. **Archivieren** verschiebt einen
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
