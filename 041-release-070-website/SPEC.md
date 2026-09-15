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

- [ ] Release-Differenz und Website-Dokumentation prüfen und aktualisieren.
- [ ] Demo-Aufnahmen aktualisieren, zweimal erfassen und visuell prüfen.
- [ ] Website bauen, Desktop/Mobil/Links prüfen; Release-Notizen vorbereiten.
- [ ] Mit Nutzeridentität committen/pushen, Tag setzen, Plattform-Builds prüfen.
- [ ] Release veröffentlichen, Website/Downloads prüfen, Register abschließen.

## Verification

Ausstehend.

## Questions

Keine.
