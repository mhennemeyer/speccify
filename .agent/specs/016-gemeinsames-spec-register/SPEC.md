---
station: Backlog
created: 2026-09-10
needs_human: true
ready: false
parent: null
---
# Gemeinsames Spec-Register unabhängig von Code-Branches erproben

## Why

> **Abgelöst 2026-09-12 durch [028](../028-spec-branch-als-register/SPEC.md):**
> Register als Branch `specs` im selben Repo statt separates Repo (Vorschlag
> D-TEAM-02 im Visionsplaybook). Diese Spec bleibt als Abwägung erhalten und
> sortiert ohne `order` als Idee.

Das Team braucht eine gemeinsame Spec-Sicht, auch bei Arbeit in Feature-Branches.
Bestätigte Entscheidung D-TEAM-01 zu V1-09 im
[Visionsplaybook](../../playbooks/weiterentwicklung.md): ein separates Spec-Repo
als Pilot; Code und codegebundene Skills/Tools bleiben in ihren Repositories.

## What

Lokaler Zwei-Checkout-Pilot mit einem separaten Git-Register und zwei Code-
Feature-Branches. Stabile Spec-/Projekt-IDs, Referenz auf Code-Repos/Revisionen,
eindeutige Datenhoheit und sichtbare lokale/gepushte/synchronisierte Zustände.
Das verknüpfte Board liest die gemeinsame Quelle; lokale `.agent/specs` bleiben
für nicht angebundene Projekte unverändert der Standard.

Die Bindung wird ausdrücklich eingerichtet. Keine zweite frei editierbare
Kopie derselben Spec, kein pauschaler Merge von `.agent` nach Code-main.
Konkurrierende Bearbeitung muss erkennbar sein; kein stilles Last-write-wins
oder Force-Push. Idempotente Historienereignisse mit eindeutiger Identität prüfen.

Nicht Teil des lokalen Piloten: Hosting buchen, externes Repo anlegen, Rechte
vergeben, bestehende Arbeit migrieren oder einen zentralen Board-Dienst bauen.
Die Einführung mit realen Teammitgliedern benötigt danach das konkrete Remote
und dessen vereinbarte Zugriffs-/Review-Regeln.

## Acceptance

- Zwei lokale Team-Checkouts sehen nach explizitem Sync dieselbe Spec und deren
  Fortschritt, ohne die jeweiligen Code-Feature-Branches zu wechseln oder zu mergen.
- Konkurrierende Änderungen derselben Ausgangsrevision werden als Konflikt
  sichtbar und erhalten beide Arbeitsstände, statt einen still zu verlieren.
- Offline-Arbeit ist als nicht synchronisiert erkennbar; erneuter Sync dupliziert
  weder Spec noch Historienereignisse.
- Branchwechsel/Branchlöschung lässt die gemeinsame Spec nicht verschwinden.
- Ready, menschliche Abnahme und erforderliche Code-Integration werden gemäß
  Spec unterschieden; ein Push oder offener PR setzt nicht automatisch Done.
- Bestehendes lokales Projekt ohne Registerbindung verhält sich unverändert.

## Decisions

- D1, 2026-09-10: D-TEAM-01 ausdrücklich bestätigt: separates gemeinsames Spec-Repo als Pilot.
- D2: Gemeinsame Projektidentitäten mit Spec 015 abstimmen; lokale Prototypen
  dürfen vor einem externen Remote mit Wegwerf-Repositories geprüft werden.
- D3: Der Pilot entscheidet nicht automatisch über Veröffentlichung privater Specs.
- D4: Vor realer Einführung Sync-/Review-Konventionen dokumentieren und zustimmen lassen.
- D5, 2026-09-12: Pilot nicht als separates Repo, sondern als Branch im Code-Repo
  (028). Grund: gleiche Rechte und Remote, ein Ordner zum Öffnen, derselbe Pfad
  für Agenten, Probelauf mit zwei Klonen erfolgreich; separates Repo bleibt
  Option, falls Specs über Repo-Grenzen hinweg geführt werden müssen.

## Tasks

- [ ] Register-/Bindungsvertrag, IDs und Konfliktregeln spezifizieren.
- [ ] Zwei-Checkout-Fixture mit Code-Branches und gemeinsamem lokalen Remote aufbauen.
- [ ] Board-Anbindung und ausdrücklich ausgelösten Sync implementieren.
- [ ] Konkurrenz, Offline, doppelte Ereignisse und Branchwechsel prüfen.
- [ ] Pilot abnehmen und Betriebsanleitung sowie Ist-Playbook aktualisieren.

## Verification

- Planungsprüfung: D-TEAM-01 ins Playbook übernommen; lokale Erprobung und
  spätere externe Einführung getrennt. Keine Repositories angelegt oder migriert.
- Bestehendes Speccify-Spec-Format verwendet; Umsetzung und Zwei-Nutzer-Abnahme offen.

## Questions

- Vor realer Einführung: Ziel-Remote, berechtigte Personen und Review-Konvention.
- Konflikt-/Abnahmedetails zunächst im lokalen Pilot demonstrieren; Abweichungen
  von den vereinbarten Projektregeln nicht still übernehmen.
