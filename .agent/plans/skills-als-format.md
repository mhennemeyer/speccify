---
lifecycle: active
status: Produktdefinition 2026-08-11 — ein Nutzer, mehrere Projekte; Skills als Format; Ablauf als Daten. Workflows durchgespielt, Bauphasen noch grob.
sessionId: skills-als-format
---
# Plan: Speccify — Skills organisieren, finden, kombinieren

> **Status**: 📋 Produktdefinition (2026-08-11). Erst definieren, dann bauen — auf
> ausdrücklichen Wunsch des BO, nachdem drei Neuausrichtungen in einer Woche
> gezeigt haben, dass Richtungswechsel billiger sind als Klarheit.
> **Ersetzt**: [`archive/neuausrichtung-workflow-playbooks.md`](./archive/neuausrichtung-workflow-playbooks.md)
> **Auslöser (BO, 2026-08-07/08)**: „Playbooks ist zwar ein netter Name, aber
> ziemlich artifiziell, wenn es ehrlicherweise einfach ein Skill mit ein paar
> Metadaten ist." — und: „Das Tool muss nicht revolutionär sein sondern vor
> Allem nützlich."

---

## Namensentscheid (BO, 2026-08-08)

**Es heißt Skill.** „Playbook" entfällt als eigener Begriff — es war ein
Kunstwort für etwas, das im Kern ein Agent Skill mit Metadaten ist. Das
Besondere an Speccify ist nicht das Format, sondern **Organisation, Lookup und
Kombination**.

Ein Skill, der andere Skills referenziert, ist weiterhin etwas Besonderes — er
heißt jetzt einfach *zusammengesetzter Skill*, nicht Playbook.

## Wer das benutzt (BO, 2026-08-11)

**Eine Person, mehrere parallele Projekte.** Kein Team, keine Rechte, kein
Review-Prozess, keine Organisation. Team-Nutzung ist ausdrücklich *später* und
darf die heutigen Entscheidungen nicht verkomplizieren.

Damit ist das Problem scharf:

> **Wissen und Setup wandern nicht zwischen den eigenen Projekten.**
> Was in Projekt A gelöst wurde, wird in Projekt B neu erarbeitet oder
> kopiert — und driftet danach auseinander.

## Rollenteilung (BO, 2026-08-11)

| Wer | Was | Wie |
|---|---|---|
| **Der Agent** | Skills finden, lesen, installieren, veröffentlichen | MCP |
| **Der Mensch** | Werkzeuge und Umgebung einrichten, Überblick behalten | Desktop-UI |

Das verschiebt den Viewer: weniger Leseoberfläche für Skills (das macht der
Agent), mehr **Aufsicht über das Setup** — was ist installiert, was kostet es,
was ist veraltet, welche MCP-Server sind konfiguriert.

## Die drei Orte

Der bisherige Entwurf ließ ein „Speccify-Arbeitsverzeichnis" drei Jobs machen
und zerbrach daran. Getrennt:

| Ort | Rolle | Eigenschaft |
|---|---|---|
| `.claude/skills/` im Projekt | wo Skills **benutzt** werden | erzeugt aus dem Manifest, wegwerfbar, gitignorierbar |
| ein Repo, das mir gehört | wo Skills **entstehen und leben** | davon gibt es mehrere |
| fremde Repos | wo Skills **herkommen** | viele, meist nicht meine |

Es gibt also **kein Arbeitsverzeichnis**. Speccify braucht pro Projekt ein
Manifest und eine Liste konfigurierter Quellen. Damit lösen sich beide Probleme
aus dem BO-Entwurf auf: mehrere Projekte mit unterschiedlichen Quellen sind der
Normalfall, und „nach Speccify exportieren" heißt „in eines meiner Repos
veröffentlichen".

## Quellen sind fremde Repos — und es gibt sie schon

Eine Quelle muss **Repos mit vielen Skills** können, nicht nur eins pro Repo.
Geprüft am 2026-08-08: `anthropics/skills` enthält 17 Skills unter `skills/`,
dazu existieren Sammlungen wie `obra/superpowers`.

Folge: **Das Kaltstart-Problem entfällt.** `speccify search` findet ab Tag eins
etwas, ohne dass jemand einen Index befüllt. Der Punkt „Index säen" von der
Launch-Liste ist damit erledigt.

## Der Ablauf ist Daten, nicht Code (BO, 2026-08-11)

> „Der Ablauf sollte nicht compiliert sein, sondern im Nachgang anpassbar."

Speccify liefert **einen** konkreten Ablauf mit, aber als Dateien in einem Repo
— nicht als Logik im Programm. Übernehmen heißt: Repo ziehen. Anpassen heißt:
forken und editieren. Damit gilt für den Ablauf dieselbe Maschinerie wie für
alles andere (Version, Pin, Frische, Diff).

Kandidat für den mitgelieferten Ablauf ist die Konvention, die im Speccify-Repo
seit Monaten läuft und sich bewährt hat: `.agent/plans/` mit Lebenszyklus und
genau einem aktiven Plan, `status.md`, `log.md`, Tags werden vorgeschlagen
statt gesetzt, Commits mit Verifikationszahlen. Erprobt statt erfunden.

Die Kette, die der BO beschreibt, schließt sich damit:
**Plan** sagt, was zu tun ist → **Skills** machen das Wiederkehrende daran
wiederholbar → **Tools** sind, was die Skills voraussetzen.

## Speccify bootet sich selbst

Wenn der Agent die Skills verwaltet, muss er von Speccify wissen. Das löst sich
im Format selbst: **Speccify liefert einen Skill mit, der Agenten beibringt,
Speccify zu benutzen.** Skills lösen über ihre Beschreibung automatisch aus —
ein Skill mit „Use when the task is something recurring and no installed skill
covers it" bringt den Agenten von selbst dazu, erst zu suchen, statt sich das
Wissen neu zu erarbeiten.

Damit fällt die größte Schwäche gegenüber nativen Skills weg: Speccify wirkt,
ohne dass man dem Agenten in jedem Projekt erklärt, dass es existiert.

---

## Workflows

Durchgespielt bis zum Ende, mit den Stellen, an denen es heute klemmt.

### W-A — Neues Projekt aufsetzen

1. `speccify init` im Projekt: Manifest, Quellen aus der persönlichen
   Voreinstellung, Ablauf-Template optional.
2. `speccify pull` materialisiert die deklarierten Skills nach
   `.claude/skills/` — samt dem Speccify-Skill, damit der Agent weiß, dass es
   Speccify gibt.
3. Die Desktop-App zeigt, welche MCP-Server der Ablauf und die Skills
   voraussetzen und was davon hier fehlt.

*Ergebnis:* Ein neues Projekt startet mit demselben Setup wie die anderen,
nicht mit Kopieren.

### W-B — Etwas gelöst, will es behalten

1. Der Agent hat gerade etwas Mühsames gelöst. Ich sage ihm, er soll daraus
   einen Skill machen.
2. Er schreibt `SKILL.md` mit Beschreibung, Schritten, Quellen samt Abrufdatum.
3. `speccify check` prüft: Beschreibung mit *was und wann*, Body-Länge, Quellen
   erreichbar, Verweise eine Ebene tief.
4. Ich sehe ihn in der App durch und veröffentliche ihn in eines meiner Repos.

*Ergebnis:* Der Moment mit dem höchsten Wert — direkt nachdem es weh tat — wird
festgehalten, statt zu verdampfen.

### W-C — In einem anderen Projekt brauchen

1. In Projekt B stößt der Agent auf dieselbe Aufgabe.
2. Der Speccify-Skill lässt ihn suchen, bevor er selbst recherchiert.
3. Fund → ins Manifest → `pull` → benutzen.

*Ergebnis:* Das, wofür das Ganze da ist.

### W-D — Ein Skill hat sich geändert

1. Upstream (meins oder fremd) ändert sich ein Skill.
2. `speccify verify` zeigt Drift gegen das Lockfile.
3. Ich sehe den Diff in der App und entscheide.

*Offen:* Bei fremden Quellen ist „ich entscheide" die richtige Stelle für einen
Review-Blick — genau das, wovor der Skills-Spec warnt (*„audit thoroughly"*).
Was die App dafür zeigen muss (gebündelte Skripte, Netzzugriffe, Diff), ist
noch nicht entworfen.

### W-E — Aufräumen

1. `speccify check` über alles: veraltete Quellen, tote Links, Lint-Verstöße.
2. Token-Bericht: was kosten die installierten Skills beim Start, welche
   Beschreibungen sind zu lang, welche Skills löst hier nie jemand aus.
3. Entfernen oder auffrischen.

*Ergebnis:* Der Grund, warum man das Werkzeug behält, nicht nur ausprobiert.

### W-F — Fremde Quelle einbinden

1. `speccify source add git+https://github.com/anthropics/skills`
2. Das Repo enthält 17 Skills; alle werden durchsuchbar.
3. Einzelne ins Projekt holen — mit Pin, damit sie sich nicht unter mir ändern.

*Ergebnis:* Speccify wird die eine Anlaufstelle, statt eine weitere Insel.

### W-G — In einem fremden Projekt arbeiten

Ich arbeite in einem Projekt, dessen Konventionen mir nicht gehoeren.

1. **Gast-Modus**: Speccify erzeugt keine Datei, die `git status` zeigt.
   Manifest und materialisierte Skills werden ueber `.git/info/exclude`
   ausgeblendet — das ist pro Klon, wird nie committet und ist genau dafuer da.
2. **Zwei Geltungsbereiche**: `~/.claude/skills/` ist, was ich mitbringe;
   `.claude/skills/` ist, was das Projekt vorschreibt. Speccify braucht also ein
   **persoenliches Manifest** neben dem pro Projekt.
3. **Meine Skills sind pro Projekt abschaltbar.** Loesen sie im fremden Projekt
   automatisch aus, bringe ich genau das Chaos hinein, das ich beklage — nur
   selbst verursacht. Definiert das Projekt einen eigenen Ablauf, gewinnt der.
4. **Vertraulichkeit**: Loese ich dort etwas und will es behalten, darf das nicht
   versehentlich in ein oeffentliches Repo wandern (interne URLs, Architektur,
   Namen). Beim Veroeffentlichen aus einem fremden Projekt heraus wird nach dem
   Ziel-Repo gefragt, Vorgabe privat.

*Ergebnis:* Ich kann mein Wissen mitbringen, ohne es jemandem aufzudraengen —
und ohne fremdes Wissen versehentlich mitzunehmen.

### W-H — Ein Skill erweist sich als schlecht

Vier Faelle, vier Antworten: **falsch** (korrigieren oder zurueckziehen),
**veraltet** (Frische-Pfad, existiert), **ueberholt** (auf Nachfolger zeigen),
**gefaehrlich** (hart zurueckziehen).

1. **Markieren, nicht loeschen.** Wie `npm deprecate`, `cargo yank`, `retract`
   in go.mod: bestehende Installationen laufen weiter, nur die Neuauswahl wird
   verhindert. In der Quelle: `metadata.speccify.deprecated` mit Grund, optional
   `speccify.superseded-by`.
   Loeschen ist schlechter — wer per Commit gepinnt hat, loest weiter auf, aber
   `verify` gegen den Tag scheitert mit einer irrefuehrenden Meldung.
2. **`check` und Viewer zeigen es deutlich**, samt Grund und Nachfolger.
3. **Pinning schuetzt vor Ueberraschungen und damit auch vor Ruecknahmen.** Ein
   Projekt mit gepinnter v1.2.0 behaelt sie. Speccify kann beim naechsten
   `check` warnen — mehr nicht. In fremde `.claude/skills/` reicht niemand
   hinein. Das ist bei jedem Paketmanager so und wird so dokumentiert, statt so
   zu tun, als ginge mehr.
4. **Wo ist er ueberall installiert?** Braucht die Projektliste (s. u.).
5. **Was hat er angerichtet?** Ein Skill sollte eine Spur hinterlassen: steht im
   Log, welchem Skill der Agent gefolgt ist, weiss man, was nachzupruefen ist.
   Bei der bestehenden `log.md`-Konvention fast geschenkt.

*Ergebnis:* Ein Fehler ist eingrenzbar statt unauffindbar.

---

## Der vierte Ort: die Projektliste

W-G und W-H brauchen beide etwas, das der bisherige Entwurf nicht hat:
**Speccify muss von meinen Projekten wissen, nicht nur vom aktuellen.**

Damit loest sich der urspruengliche BO-Entwurf („man legt das
Speccify-Work-Verzeichnis fest") richtig auf: Der Instinkt stimmte, die Form
nicht. Es braucht kein Verzeichnis, in dem Skills liegen, sondern eine
maschinenweite **Liste der Projekte und Quellen** — genau das, was die App beim
Oeffnen zeigt.

* Projekte tragen sich bei `speccify init` selbst ein; die App raeumt tote
  Eintraege weg. Kein Scannen des Dateisystems.
* Beantwortet „welche meiner Projekte haben diesen Skill?" und „wo laeuft mein
  Ablauf, wo der des Projekts?".
* Enthaelt die persoenlichen Quellen-Voreinstellungen fuer neue Projekte.

---

## Nicht-Ziele (bewusst, für jetzt)

* **Kein Team, keine Rechte, kein Review-Workflow.** Ein Nutzer.
* **Kein gehosteter Dienst, keine Registry, kein Marktplatz.** Git-Repos.
* **Kein eigenes Format.** Der Agent-Skills-Spec, plus `metadata`.
* **Kein Vorschreiben.** Ein Ablauf wird mitgeliefert, keiner erzwungen.
* **Kein Editor.** Skills schreibt der Agent; der Mensch sieht durch.

## Entscheidungsvorschläge

* **D1 — `SKILL.md` ersetzt `playbook.yaml` vollständig.** Kein Parallelbetrieb.
* **D2 — Quellen im Body**, Konvention `— retrieved <ISO>`.
* **D3 — Verzeichnis-Layout nach Spec**: `scripts/`, `references/`, `assets/`.
* **D4 — Scope in `metadata.speccify.scope`**, weil `name` nur `[a-z0-9-]` darf.
* **D5 — Quelle = Repo mit einem *oder vielen* Skills.** Auto-Erkennung über
  `SKILL.md`-Vorkommen.
* **D6 — Der mitgelieferte Speccify-Skill** ist Teil der Auslieferung, nicht
  optional.

## Offene Fragen

1. **Wie kommt der Ablauf ins Projekt?** Als Skill, als Dateien, als beides?
   Ein Skill löst über Beschreibung aus — ein Ablauf soll aber *immer* gelten.
   Das spricht für einen Abschnitt in `CLAUDE.md`/`AGENTS.md`, den Speccify
   erzeugt und aktuell hält, plus die Verzeichnisstruktur.
2. **Wie granular ist das Manifest?** Pro Projekt eine Liste von Skills — oder
   auch Gruppen („mein Rust-Setup"), die man am Stück zieht?
3. **Was passiert mit dem Entwurfs-Release v0.2.0?** Noch nicht veröffentlicht.
   Liegen lassen, bis das hier steht?

## Bauphasen (grob, erst nach der Definition schärfen)

* **S1** Format: `SKILL.md` lesen/schreiben/prüfen, die zehn Inhalte
  konvertiert. Danach funktionieren sie in Claude Code ohne Speccify.
* **S2** Quellen: fremde Repos mit vielen Skills, Suche darüber.
* **S3** Der Speccify-Skill + Manifest/Pull-Schleife (W-A, W-C).
* **S4** App als Setup-Aufsicht: installierte Skills, Token, Lint, MCP-Server.
* **S5** Ablauf-Template als Daten (W-A), Doku und Website.
