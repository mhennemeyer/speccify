---
station: Backlog
order: 9
created: 2026-09-12
needs_human: true
ready: false
open_question: null
parent: null
---
# Übernahme sichtbar: Besitzer und Branch je Spec auf dem Board

## Why

Im Team muss auf einen Blick klar sein, wer an welcher Spec arbeitet und in
welchem Branch der Code dazu liegt. Heute sagt das Board nur die Station; die
Person steht bestenfalls in der History, der Branch nirgends. Baut auf dem
gemeinsamen Register aus [028](../028-spec-branch-als-register/SPEC.md) auf,
damit Besitzer und Branch bei allen ankommen (V1-09, D-TEAM-02).

## What

Zwei Front-Matter-Felder je Spec: `owner` (Anzeigename und E-Mail aus der
Git-Identität des Checkouts, z. B. `Matthias Hennemeyer <mh@…>`) und `branch`
(Konvention `spec/<NNN>-<slug>`; in Workspaces `branches:` je Repo-Slug).
„Übernehmen“ (Backlog → Doing per Drag oder Knopf) setzt beide Felder, loggt
`station_changed` mit Person, und bietet an, den Branch anzulegen und zu
wechseln (bestehende Branch-Befehle aus 021) oder einen Worktree dafür zu
öffnen; nichts davon passiert ohne Klick. Abgeben/Parken setzt `owner` zurück,
`branch` bleibt als Spur.

Karten zeigen Besitzer (Initialen, Tooltip mit Name) und Branch; Filter
„meine“ und eine Ansicht „Doing nach Person“ (Spec, Person, Branch, letzte
Bewegung). Beobachtete Wahrheit ergänzt die erklärte: für jede Doing-Spec
prüft die App `origin/<branch>` (existiert? letzter Commit von wem, wann?) und
den lokalen Checkout. Abweichungen werden angezeigt, nie korrigiert: „Du
stehst auf `x`, Spec 12 gehört zu `spec/012-…`“, „Branch hat seit 5 Tagen
keine Bewegung“, „Zuletzt hat eine andere Person auf diesen Branch gepusht“,
„Branch existiert nicht auf origin“. Zwei gleichzeitige Übernahmen kollidieren
auf der `owner`-Zeile und werden beim Sync als Konflikt sichtbar (028).

Policy-Ergänzung: der Agent liest `owner`/`branch`, nennt beides im Commit-
Body, wechselt den Branch nicht still, meldet Abweichung und übernimmt keine
Spec, die einer anderen Person gehört, ohne ausdrücklichen Auftrag.

Nicht enthalten: Rechte oder Sperren (Git-Konflikt reicht), automatische
Merges, PR-Erstellung, Benachrichtigungen (030), Zeiterfassung.

## Acceptance

- Wenn eine Spec übernommen wird, dann stehen `owner` und `branch` in der
  Front Matter, die History nennt die Person, und die Karte zeigt beides.
- Wenn zwei Personen dieselbe Spec übernehmen und synchronisieren, dann sieht
  die zweite einen Konflikt mit beiden Besitzern statt einer stillen
  Ersetzung.
- Wenn der lokale Checkout nicht auf dem Branch der ausgewählten Doing-Spec
  steht, dann zeigt das Fenster das an; ein Klick wechselt (bestehender
  Branch-Wechsel mit Bestätigung), sonst passiert nichts.
- Wenn `origin/<branch>` fehlt oder eine andere Person zuletzt gepusht hat,
  dann ist das an der Karte sichtbar, ohne dass Felder geändert werden.
- Wenn der Filter „meine“ aktiv ist, dann erscheinen nur Specs mit dem
  eigenen `owner`; „Doing nach Person“ listet alle Doing-Specs gruppiert.
- Wenn eine Spec ohne die neuen Felder gelesen wird, dann bleibt alles wie
  heute; die Felder sind optional und werden nie von der App erfunden.

## Decisions

- D1, 2026-09-12: Identität = Git-Identität des Checkouts; keine eigene
  Nutzerverwaltung. Anzeige über Name, Gleichheit über E-Mail.
- D2, 2026-09-12: Branch-Konvention `spec/<NNN>-<slug>` als Vorschlag beim
  Übernehmen, frei änderbar; keine Erzwingung.
- D3, 2026-09-12: Abweichungen anzeigen, nicht korrigieren (wie 015/026).

## Tasks

- [ ] Vertrag: Felder `owner`/`branch`/`branches`, Übernehmen/Abgeben,
      Abweichungsregeln; Policy-Ergänzung.
- [ ] Native Befehle: Übernehmen/Abgeben (Front Matter + History), Branch-
      Beobachtung (`origin/<branch>`, letzter Autor/Datum, lokaler Branch).
- [ ] Board: Karte mit Besitzer/Branch, Filter „meine“, Ansicht „Doing nach
      Person“, Abweichungshinweise; Workspace-Board (024) übernimmt die Anzeige
      lesend.
- [ ] Tests: Rust (Felder, Beobachtung mit Fixture-Remote), Mock/Browser-Suite
      (Übernehmen, Konfliktanzeige, Filter, Hinweise).
- [ ] Hilfe, Website-Doku, Stand-Playbook.

## Verification

Noch nichts geprüft; Entwurf. Abhängig von 028 (Sync) für die Teamwirkung.

## Questions

Keine blockierende Frage für den Entwurf.
