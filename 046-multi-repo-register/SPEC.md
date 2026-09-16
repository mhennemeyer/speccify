---
station: Doing
order: 46
needs_human: true
ready: true
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
5. 2026-09-16: Umsetzung im autorisierten Paket nach 044/047. Gemeinsamer
   Vertrag: `workspace-registers.json` mit Formatversion, Workspace-ID,
   benannten Register- und Code-Repo-IDs und optionalem Standardregister.
   Checkouts, URLs und Zugangsdaten sind lokale Bindungen, keine Manifestfelder.
   Das Manifest kann ausdrücklich in einem bestehenden Register gespeichert
   oder von einem anderen Rechner übernommen werden; kein Kundenregister
   wird dabei automatisch migriert.

## Tasks

- [x] Gemeinsamen Identitäts-/Manifestvertrag samt lokalen Bindungen und kompatibler Einführung ausarbeiten.
- [x] Root-/Kind-Aggregation und Register-Deduplizierung in Desktop/Core/Web integrieren.
- [x] Speicherortwahl und Mehrfach-Repo-Bezug einer kanonischen Spec ergänzen.
- [x] Schreibziele, Revisionen, Sync-Fehler und Erhalt ungesendeter Änderungen prüfen.
- [x] Zwei Rechnerpfade und Web-Board mit temporären Bare-Remotes durchspielen.
- [x] Workspace-/Board-Doku und Produktplaybooks nachführen; Team-Pilot zur Abnahme bereitstellen.

## Verification

Bestand: `apps/board/src/speccify_board/sources.py`, `Source.specs_dirs`,
kehrt bei vorhandenem `.agent/specs` am Root vorzeitig zurück. Die
Unterprojekt-Suche läuft nur ohne Root-Register. Mit der echten Source-Klasse
in temporären Testordnern reproduziert: `workspace/repo-a` wird nach Anlegen
eines leeren Root-Registers durch ausschließlich `workspace` ersetzt.
Dieser Ausgangsfehler ist behoben. Umsetzung am 2026-09-16:

- Core-Manifestvertrag plus nativer Adapter: portable IDs, separate lokale
  Bindungen, expliziter Export/Import in vorhandene Register.
- Rust: 123 Tests bestanden, 3 bestehende umgebungsabhängige Tests ignoriert.
  Root-/Kind-Kollisionen, explizite Deduplizierung, abweichende Checkouts,
  Revisionskonflikte und Repo-Bezüge geprüft.
- Vollständige Python-Suite grün; Core/Web-Vertragstests mit zwei unterschiedlichen
  lokalen Pfaden, temporären Bare-Remotes, gleicher Spec-ID, leerem Root,
  genauer Unterquelladressierung und ungesicherten Dateien. Ruff/Lint grün.
- Frontend-Typecheck; Browser: `test_workspace_register_binding.mjs`,
  `test_workspace_shell.mjs`, `test_workspace_root.mjs` und
  `test_workspace_register.mjs` grün. Kanonische Neuanlage bleibt am gewählten Ziel.
- Native QA im Wegwerf-Workspace: Manifestexport, drei Register mit gleicher
  Spec-ID, weiterer Checkout, Divergenzmeldung, tatsächlicher Bindungsdialog,
  SHA-256-Parität zu Python und abgelehnter veralteter Schreibauftrag. Kein
  Root-Git angelegt; ursprüngliche vier Fenster und Kundenregister erhalten.
- Lokaler signierter App-Build und Signaturprüfung erfolgreich; Website baut
  101 Seiten, Dokumentations-Sync grün. Kein Release-Tag.

Grenzen: Momentaufnahmeprüfung ist keine verteilte Dateisperre. Ältere Web/MCP-
Clients dürfen vorerst ohne `expected_revision` schreiben; neue UI-Aktionen
verwenden sie. Das Web-Board hat weiterhin den bestehenden gemeinsamen
Zugangsvertrag. Zweiter physischer Rechner und menschlicher Team-Pilot stehen
zur Abnahme aus; daher Doing/ready statt Done.

## Questions

Keine Implementierungsfrage offen. Menschliche Team-Abnahme ausstehend;
Kundenregister wurden nicht migriert.
