---
station: Backlog
order: 46
needs_human: true
ready: false
---

# Multi-Repo-Register mit gemeinsamem Desktop- und Web-Board

## Why

Ein fachliches Projekt umfasst mehrere Repos und eventuell einen Root ohne
Git. Das Team braucht ein gemeinsames Board über alle kanonischen Specs, auch
im Browser. Gleiche Spec-Nummern, mehrere Checkouts und verschiedene lokale
Pfade dürfen weder Karten verlieren noch doppelte Wahrheiten erzeugen.

## What

Bestehende Register (028/042) und Multi-Repo-Web-Board (032/033) durch eine
gemeinsame, versionierbare Quellbindung ergänzen. Desktop und Web verwenden
dieselben logischen Register-IDs; lokale Pfade sind gesonderte Bindungen.
Root- und Unterprojekt-Register aggregieren, nicht gegeneinander ausschließen.

Ein Root ohne Git kann ein vorhandenes Register ausdrücklich als Speicherort
für neue übergreifende Specs wählen. Jede Spec hat genau ein kanonisches
Register und kann mehrere betroffene Code-Repos/Branches referenzieren.
Vorhandene per-Repo-Register bleiben erhalten; keine automatische Migration in
ein Zentralrepo. Der genaue Manifest-/Metadatenvertrag gehört zur Umsetzung.

Nicht enthalten: vollständige Web-IDE, Anbieter-Login, neue zentrale
Spec-Datenbank oder ein komplettes persönliches Web-Identitätssystem. Die
bestehende Web-Board-Berechtigung bleibt sichtbar; sie darf nicht als
persönlich geprüfter Repo-Zugriff dargestellt werden.

## Acceptance

- Desktop und Web-Board zeigen bei identischer Quellbindung dieselben Specs:
  Root-Register plus zwei Repo-Register, jeweils mit Herkunft und Sync-Zustand.
  Auch ein leeres Root-Register verdeckt keine Unterprojekt-Specs.
- Zwei Register mit `001-example` erzeugen zwei Karten. Zwei lokale Checkouts
  desselben logischen Registers erzeugen eine Karte mit wählbarer lokaler
  Bindung. Abweichende ungesyncte Stände werden sichtbar, nicht willkürlich
  zusammengelegt; unabhängige lokale Register werden nicht nach Namen dedupliziert.
- Ein zweiter Rechner oder Web-Server kann dieselbe Quellbindung mit anderen
  lokalen Pfaden verwenden. Getrackte Konfiguration enthält keine Tokens,
  persönlichen absoluten Pfade oder pauschale Benutzerrechte.
- Eine übergreifende Spec wird im gewählten kanonischen Register angelegt,
  verweist auf die betroffenen Repos und erscheint genau einmal. Ist beim
  Anlegen das Register nicht eindeutig, wird es ausdrücklich gewählt.
- Root ohne Git funktioniert lokal; ohne Remote-Bindung ist der Zustand klar
  lokal. Die explizite Wahl eines Team-Registers benötigt keine Git-Initialisierung
  des Parent-Ordners und kopiert keine bestehenden Specs automatisch.
- Web- und Desktop-Änderung an derselben Spec erkennt die erwartete Revision.
  Paralleländerung, Push-Ablehnung und fehlende Rechte bleiben sichtbar und
  erhalten ungesendete Änderungen. Kein Force-Push oder Überschreiben lokaler
  Änderungen beim nächsten Refresh; Fehler einer Quelle verdecken keine andere.
- Jede Schreibaktion adressiert Register-ID und Spec-ID; Anzeigenamen und
  Client-Pfade sind keine Berechtigung. Der Dienst begrenzt den Zugriff auf
  konfigurierte Quellen und verwendet den bestehenden Auth-Vertrag.
- Code-Branchwechsel ändert nicht die Registerwahrheit. Bestehende Register,
  History, Besitzer/Branch-Felder und MCP-Clients funktionieren weiter oder
  erhalten einen dokumentierten kompatiblen Übergang.

## Decisions

1. 2026-09-16: D-TEAM-02 (`specs`-Branch je Repo) bleibt gültig. Aggregation
   und Bindung erweitern, keine zweite veränderliche Kopie pro Board erzeugen.
2. 2026-09-16: Fachliche Identität ist Register-ID + Spec-ID, nicht Nummer,
   Projektname, Arbeitsbaum-Pfad oder bloß normalisierte Remote-URL.
   Der Vertrag muss dieselbe Quelle explizit wiedererkennen können.
3. 2026-09-16: Quellbindung und Speicherort für Root-Specs müssen teilbar sein.
   Ein Root ohne eigenes Repo kann die Bindung im ausdrücklich gewählten
   bestehenden Register versionieren; lokale Checkout-Zuordnung bleibt lokal.
4. 2026-09-16: Web-Board existiert bereits. Persönliche Benutzeranmeldung und
   individuelle Git-Autorisierung einer vollständigen Web-App werden nur im
   [Draft](../../playbooks/speccify-web-app.md) untersucht.

## Tasks

- [ ] Gemeinsamen Identitäts-/Manifestvertrag samt lokalen Bindungen und kompatibler Einführung ausarbeiten.
- [ ] Root-/Kind-Aggregation und Register-Deduplizierung in Desktop/Core/Web integrieren.
- [ ] Speicherortwahl und Mehrfach-Repo-Bezug einer kanonischen Spec ergänzen.
- [ ] Schreibziele, Revisionen, Sync-Fehler und Erhalt ungesendeter Änderungen prüfen.
- [ ] Zwei Rechnerpfade und Web-Board mit temporären Bare-Remotes durchspielen.
- [ ] Workspace-/Board-Doku und Produktplaybooks nachführen; Team-Pilot abnehmen lassen.

## Verification

Bestand: `apps/board/src/speccify_board/sources.py`, `Source.specs_dirs`,
kehrt bei vorhandenem `.agent/specs` am Root vorzeitig zurück. Die
Unterprojekt-Suche läuft nur ohne Root-Register. Konfiguration benennt
Quellen aktuell über `RepoConfig.name`; das ist noch kein gemeinsamer
Desktop-/Web-Identitätsvertrag. Noch keine Umsetzung dieser Spec.

## Questions

Das konkrete serialisierte Format und die Einführung stabiler IDs werden vor
der Implementierung anhand der Kompatibilitätsfälle festgelegt. Keine
Kundenregister ohne explizit gewählten Zielvertrag migrieren.
