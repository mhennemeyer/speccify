---
station: Doing
order: 41
needs_human: false
---

# Release 0.7.0 und aktuelle Website

## Why

Die neue Erkennungstiefe wurde angenommen. Der Nutzer beauftragt Commit/Push,
ein neues Release sowie aktuelle Screenshots und Dokumentation auf der Website.
0.6.0 ist das letzte veröffentlichte Release; 0.7.0 ist im Code vorbereitet.

## What

0.7.0 mit dem aktuellen geprüften Stand veröffentlichen. Öffentliche Demo-Bilder
erneuern, Erkennungstiefe illustrieren, Website-/Doku-Aussagen nachziehen,
Release-Notizen mit Referenz auf den Spec-Register-Commit erstellen.

## Acceptance

- Website erklärt Standardtiefe 1 und die Konfiguration 1–16; Bilder zeigen
  aktuelle UI mit öffentlichen Demo-Daten, lesbar auf Desktop und Mobilgeräten.
- Release 0.7.0 besitzt die vorgesehenen macOS-, Windows- und Linux-Artefakte;
  Build-/Deploy-Läufe und öffentliche Downloadziele sind geprüft.
- Commits und Tag verwenden die Nutzeridentität ohne Attributionstrailer.
- Lokale App bleibt für Nutzung geöffnet; Prüfgrenzen werden dokumentiert.

## Decisions

1. 2026-09-15: Expliziter Nutzerauftrag erlaubt Tag, Release-Veröffentlichung
   und Website-Deploy. Keine erneute Freigabe für bereits beauftragte Schritte.
2. 2026-09-15: Version 0.7.0 verwenden; dieser vorbereitete Versionsstand wurde
   noch nicht veröffentlicht. Historische Phase-Tags sind keine App-Releases.

## Tasks

- [x] Release-Differenz und Website-Dokumentation prüfen und aktualisieren.
- [x] Demo-Aufnahmen aktualisieren, zweimal erfassen und visuell prüfen.
- [x] Website bauen, Desktop/Mobil/Links prüfen; Release-Notizen vorbereiten.
- [ ] Mit Nutzeridentität committen/pushen, Tag setzen, Plattform-Builds prüfen.
- [ ] Release veröffentlichen, Website/Downloads prüfen, Register abschließen.

## Verification

- CI zum App-Code `5c30726` vollständig grün: Rust, Python, Frontend sowie
  Desktop-Tests/Build auf Windows und Linux (Lauf 34950294982).
- Zehn öffentliche Demo-Aufnahmen visuell geprüft; nach Korrektur der normalen
  Workspace-Panelgrößen passen alle drei Spalten samt Überschriften ins Bild.
  Zwei finale Durchläufe bytegleich (SHA-256 für alle zehn Bilder).
- Marketing-Build: 101 Seiten; Doku-Sync und `git diff --check` grün.
- Website-Prüfung deckte zunächst einen nach unten gerückten Mobil-Einstieg und
  die normalisierte Starlight-URL auf. Release-Link unter das Leitbild gesetzt,
  Doku-URL auf `/releases/0-7-0/` korrigiert. Linux-Startoptionen auf der
  Downloadseite umbrechen jetzt auch bei 320 px. Finale Prüfung vollständig grün:
  Landing/Features 1440/390/320 px, Bildlinks ohne JS, DE-Weiterleitung,
  Doku-/Release-Seiten und sechs getrennte Linux-Downloadlinks (x86_64/arm64).

## Questions

Keine.
