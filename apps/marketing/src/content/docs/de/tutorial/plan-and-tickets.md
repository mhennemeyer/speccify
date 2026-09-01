---
title: Ein Plan und ein Board
description: Den Plan schreiben, den Agenten Tickets schneiden lassen und das Board arbeiten.
sidebar:
  order: 4
---

Arbeit beginnt nicht im Chat. Sie beginnt als **Plan**
(was und warum), wird zu **Tickets** (klein, geordnet, prüfbar) und
wandert über das **Board**. Dieses Kapitel zeigt den echten
4Notice-Plan und was der Agent daraus gemacht hat.

## 1. Den Plan schreiben — zuerst ein Satz

Der Plan ist eine Markdown-Datei,
`.agent/plans/basic-app-plan.md`, mit `lifecycle: active` (nur ein
Plan ist zugleich aktiv). Schreib ihn in der Sprache, in der du
denkst — 4Notices Plan ist deutsch; dem Agenten ist es egal. Sein
Kern:

> Vier Notizzettel in den vier klassischen Post-it-Farben. Eine Mac-
> und iOS-App, mit Watch-Target, Desktop-Widgets und
> Menü-Bar-Schnellzugriff. Einfacher und sehr schneller Sync über
> Ubiquitous Storage.
>
> **Der Satz, den V1.0 einlösen soll:** Vier Zettel, auf jedem Gerät
> dieselben, sofort da — tippen, fett machen, fertig. Kein Dokument,
> kein Ordner, kein Speichern.

Dieser Satz ist der Maßstab: Jede Umfangsfrage der folgenden Wochen
wird an ihm gemessen.

Der Rest des Plans ist eine **Feature-Tabelle** — eine Zeile pro
Feature, jede sagt präzise, was gemeint ist und welches Ticket es
trägt („iPhone: ein Zettel sichtbar, horizontal blättern; Start =
gepinnter Zettel … → N4"). Präzision hier ist billig; Mehrdeutigkeit
hier ist später ein falscher Build.

## 2. Entscheidungen vor den Tickets

Beim Skizzieren des Plans tauchten Fragen auf, die nur der Owner
beantworten kann — Deployment-Targets, der Sync-Store, Kaufmodell und
Preis. Sie liefen durch das
[Frageprotokoll](/de/app/questions/): im Chat gestellt, vom
Owner beantwortet, festgehalten. Erst dann ergab das Schneiden Sinn —
ein Ticket auf einer offenen Frage kodiert einen Rateversuch.

## 3. Der Agent schneidet

Eine Anweisung („schneide den Plan in Tickets") machte aus dem Plan
**dreizehn Tickets**, N1–N13, jedes eine Datei unter `.agent/board/`:
Rich-Text-Editor, KV-Store-Sync mit Größenbudget, iPhone-Pager,
Fonts, Menü-Bar, Widgets, Watch-App, Trial & Kauf, I18N, Icon,
fastlane, Release. Jedes ist für **einen Agenten-Lauf** dimensioniert,
geordnet per `order`, und startet im `Backlog`. Ein echtes:

```markdown
---
id: n2-rich-text-editor
title: Rich Text mit einfachen Edit-Tools (WYSIWYG)
station: Done
created: 2026-08-23T10:28:02Z
order: 2
plan: basic-app-plan
---
## Scope
`Note.text` wird `AttributedString`; `NoteView` editiert WYSIWYG.
Werkzeugleiste je Zettel: fett, kursiv, unterstrichen, Überschrift,
Aufzählung, Checkliste. `RichText` kodiert ⇄ `Data` für Store und
Sync.

## Acceptance criteria
- Fett/Kursiv/Unterstrichen/Überschrift/Liste/Checkliste wirken auf
  die Auswahl und bleiben nach Neustart erhalten
- `RichText`-Roundtrip-Test (Attribute überleben Encode/Decode)
- macOS und iOS benutzen denselben Editor-Code
```

Achte darauf, was die Akzeptanzkriterien sind: **beobachtbare
Ergebnisse**, eines davon ein benannter Test — nicht „Editor
funktioniert".

## 4. Das Board arbeiten

Ab hier ist die Schleife mechanisch — und genau das ist der Punkt:

1. Das **oberste Backlog-Ticket** nehmen (niedrigste `order`), auf
   `In Progress` setzen — es ist immer nur eines in `In Progress`.
2. Die Arbeit machen;
   [unterwegs committen](/de/tutorial/working-and-commits/).
3. Jedes Akzeptanzkriterium prüfen; dann `Done`.
4. Zu groß für einen Lauf? **Teilen** statt halbfertig liegenlassen.

In der Speccify-App siehst du das Board in Echtzeit wandern, und die
History des Tickets zeigt jeden Schritt, den der Agent geloggt hat:

```json
{"event_type":"station_changed","summary":"Backlog -> In Progress", …}
{"event_type":"station_changed","summary":"In Progress -> Done (Rich Text + Werkzeugleiste, 7 Tests, Sichttest)", …}
```

Sechs Tage nach dem Schneiden waren N2–N11 `Done` — Editor, Sync,
Pager, Fonts, Menü-Bar, Widgets, Watch, Trial, Lokalisierung, Icon.
Das nächste Kapitel schaut auf das, was dieses Tempo *auditierbar*
gehalten hat: [die Commits](/de/tutorial/working-and-commits/).
