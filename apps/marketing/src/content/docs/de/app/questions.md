---
title: Fragen & Antworten
description: Das Protokoll, das einen Agenten am Raten hindert — und jede Entscheidung die Konversation überleben lässt.
sidebar:
  order: 3
---

Manche Entscheidungen gehören dir allein: Umfang, Geld, Geschmack,
alles Unumkehrbare. Die Regel des Workflows für den Agenten:

> Wenn du eine Entscheidung brauchst, die nur der Owner treffen kann,
> **frag im Chat, sofort**. Warte auf die Antwort; **rate nicht**
> weiter. Eine falsche Annahme kostet mehr als eine kurze Pause.

Der Chat ist der Ort, an dem die Frage *gestellt* wird — aber Chat
scrollt davon. Deshalb wird jede beantwortete Frage **im Ticket
festgehalten**, wo die Entscheidung hingehört:

```markdown
## Questions

### Q1 · answered · 2026-08-06T10:00:00Z
Should the run history be persisted, or is session scope enough?

### A1 · bo · 2026-08-06T10:02:00Z
Session scope is enough.
```

Fragen werden fortlaufend nummeriert, Nummern nie wiederverwendet.
Das Ticket ist das Protokoll, kein Briefkasten: Im Normalfall wird
der Q/A-Block vollständig geschrieben, nach deiner Antwort.

## Wenn du nicht da bist

Endet ein Lauf ohne Antwort — du bist unterwegs, oder der Agent
wurde unbeaufsichtigt gestartet — wird die Frage als *offen*
geschrieben:

```markdown
### Q2 · open · 2026-08-07T18:30:00Z
Which of the two paywall layouts should ship?
```

Das Frontmatter des Tickets bekommt `open_question: Q2`, das Ticket
bleibt in `In Progress`, und das Board zeigt es als **wartend** — die
App schickt zusätzlich eine System-Notification, damit eine neue
Frage nicht darauf wartet, dass du hinsiehst. Du antwortest, wann
immer du zurück bist — im Antwortfeld ganz oben im Ticket-Detail, mit
einem `### A2 · bo · …`-Block direkt in der Ticket-Datei oder einfach
im nächsten Chat; der nächste Lauf des Agenten trägt es nach, löscht
das Flag und macht weiter. Erledigte Fragen klappen unter
**Answered (n)** zusammen.

:::note[Screenshot]
*Platzhalter: ein wartendes Ticket mit offener Frage auf dem Board.*
:::

Der Effekt, Monate später: Jedes „warum ist das so?" hat eine
auffindbare Antwort mit Zeitstempel — im Ticket, das die Entscheidung
hervorgebracht hat, nicht in einem Chat-Log, das niemand durchsuchen
kann.
