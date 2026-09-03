---
title: Pläne & Playbooks
description: Ein Plan ist das, was der Agent in Tickets schneidet — genau einer aktiv. Ein Playbook ist eine stehende Anleitung, die du immer wieder benutzt.
sidebar:
  order: 3
---

Neben dem Board leben zwei Sorten längerer Texte, und die App hält sie
mit Absicht auseinander:

- Ein **Plan** beschreibt ein Stück Arbeit. Er wird in Tickets
  geschnitten, abgearbeitet und ist dann *fertig*.
  `.agent/plans/<name>.md`.
- Ein **Playbook** beschreibt einen Ablauf — Release, Deploy, einen
  neuen Rechner einrichten. Es wird nie fertig; du benutzt es, wann
  immer der Anlass kommt. `.agent/playbooks/<name>.md`.

Beides sind einfache Markdown-Dateien, committet mit dem Code, und
beides kommt auf demselben Weg ins Terminal des Agenten: **Als Prompt
kopieren**.

## Pläne

Ein Plan hat ein kleines Frontmatter und einen Body. Der Body ist
freies Markdown — die App rendert ihn, der Agent liest ihn. Der Titel
ist die erste Überschrift; der Dateiname ist die Referenz, die Tickets
benutzen (`plan: <stem>` im Ticket-Frontmatter).

```markdown
---
lifecycle: active
status: Bauen — P1 geliefert, P2 läuft
---
# Projektfenster

## Ziel
…

## Meilensteine
…
```

### Lifecycle: genau ein Plan ist aktiv

`lifecycle` ist eins von `draft`, `active`, `onHold`, `done`,
`research`. Die Invariante, die die App durchsetzt: **höchstens ein
Plan ist `active`**. Das ist der Plan, aus dem der Agent Tickets
schneidet, und der, der aufklappbar über dem Board steht.

- **Aktivieren** setzt einen Plan auf `active` und parkt den bisher
  aktiven im selben Schritt auf `onHold`. Die App sagt dir, welche
  Datei sie geparkt hat.
- **Archivieren** verschiebt einen Plan nach `.agent/plans/archive/`
  und setzt `lifecycle: done`. Fertige Pläne bleiben im Repository —
  der Pläne-Tab listet das Archiv getrennt, damit die Arbeitsliste
  kurz bleibt.
- Was die App im Frontmatter nicht kennt (Session-IDs, eigene
  Felder), bleibt Byte für Byte erhalten. Die App schreibt nur die
  Zeilen um, die sie ändert.

### Der Editor

Öffne einen Plan und wechsle auf **Bearbeiten**: Die strukturierten
Felder `lifecycle` und `status` stehen über einem Textfeld mit dem
Body. Speichern schreibt die Datei; der nächste Lauf des Agenten liest
sie. Mit demselben Editor trägst du einen neuen Meilenstein nach oder
hältst eine Entscheidung direkt im Plan fest — so bleibt der Plan die
eine Quelle dessen, was entschieden wurde.

### Eskalation: der Agent braucht dich

Ein Agent, der auf etwas stößt, das er nicht allein entscheiden darf —
ein Widerspruch im Plan, eine Migration, die Daten löschen würde, ein
fehlender Account — schreibt eine `escalation:` ins Frontmatter des
Plans, einzeilig oder als Block:

```yaml
escalation:
  reason: Migration würde die users-Tabelle löschen — bestätigen oder Plan ändern
  raisedBy: agent
  at: 2026-09-03T09:12:00Z
```

Der Pläne-Tab zeigt an diesem Plan einen **roten Banner** mit dem
Grund. Lesen, handeln (Plan bearbeiten, im Terminal antworten), dann
**Auflösen** klicken — das entfernt genau diese Zeilen und sonst
nichts. Eskalationen sind für die Plan-Ebene; eine Frage zu einem
einzelnen Ticket läuft stattdessen über [Fragen](/de/app/questions/).

### Als Prompt kopieren

**Als Prompt kopieren** legt den Plan als Markdown-Block in die
Zwischenablage, mit dem Pfad als erster Zeile:

````markdown
`.agent/plans/projektfenster.md`

```md
# Projektfenster
…
```
````

Füge ihn ins Agent-Terminal ein und schreibe dazu, was passieren soll
— „schneide Meilenstein P3 in Tickets", „prüf, ob das noch zum Board
passt". Über die Pfad-Referenz kann der Agent die Datei selbst öffnen,
wenn er mehr als den Ausschnitt braucht. Denselben Knopf gibt es an
Tickets und Playbooks; die Zaunlänge wird gegen Backticks im Inhalt
berechnet, Code-Blöcke im Plan überstehen den Weg also.

## Playbooks

Playbooks sind die Abläufe, die sonst im Wiki oder im Kopf liegen:
*wie wir ein Release schneiden*, *wie ein neuer Rechner eingerichtet
wird*, *wie wir ein Deploy zurückrollen*. Eine Playbook-Datei ist ein
Markdown-Body mit optionaler `description` im Frontmatter; der Titel
ist die erste Überschrift.

```markdown
---
description: Vom Tag zum veröffentlichten Release, macOS und Windows
---
# Release

1. Version anheben, committen.
2. `vX.Y.Z` taggen und den Tag pushen — der Release-Workflow baut
   beide Plattformen in ein Entwurfs-Release.
3. Entwurf prüfen: signiertes dmg, Notarisierungs-Ticket gestapelt.
4. Veröffentlichen; Download-Seite nachziehen.
```

Der Tab **Playbooks** sitzt zwischen Board und Plänen. **+ Playbook**
legt aus einem Namen eine Datei an (Umlaute und Leerzeichen werden zum
Slug), der Editor pflegt Beschreibung und Body, und **Als Prompt
kopieren** gibt den Ablauf dem Agenten genau wie einen Plan. Löschen
fragt vorher nach — Playbooks sind die Sorte Datei, deren Verlust man
bereut.

Was Playbooks mit Absicht **nicht** haben: einen Lifecycle, eine
Station, ein Aktiv-Flag. Ein Plan ist fertig, wenn seine Tickets
fertig sind; ein Playbook ist nie fertig. Wenn du in einem Playbook
Schritte abhaken willst, ist der Anlass ein Plan — leg einen an und
verweise darin auf das Playbook.

## Pläne, Playbooks, Skills — was ist was?

- Ein **Skill** bringt dem Agenten bei, *wie* eine Sorte Aufgabe geht,
  in jedem Projekt; er kommt aus einer
  [Speccify-Quelle](/de/speccify/overview/) und löst von selbst aus.
- Ein **Playbook** sagt, wie *dieses Projekt* einen wiederkehrenden
  Ablauf fährt; du gibst es dem Agenten, wenn der Anlass da ist.
- Ein **Plan** sagt, was *dieses Projekt* als Nächstes baut; der Agent
  schneidet ihn in Tickets auf dem [Board](/de/app/board/).
