---
station: Doing
order: 50
needs_human: true
ready: true
---

# Signierte automatische Updates für Desktop-Plattformen

## Why

Nach 0.8.0 sollen Windows, macOS und Linux neue Versionen in der App erhalten.
Der Nutzer priorisiert dies vor der Fortsetzung der itsdcloud-Integration.

## What

Eine appweite automatische Update-Suche mit abschaltbarem Intervall, sichtbarer
Version/Release-Notizen, geprüftem Download, Fortschritt, Abbruch und expliziter
Installation. Signierte Artefakte und vollständiges Manifest für macOS arm64,
Windows x64 und Linux AppImage x64/arm64. Linux deb/rpm verweisen auf den
Paketmanager. Sichere Installation berücksichtigt alle geöffneten Fenster,
Editoren und laufenden Terminals/Aktionen. Schlüssel nur im Rechnerspeicher und
GitHub Secrets; öffentlicher Prüfkey im App-Vertrag.

## Acceptance

- Suche erfolgt beim Start und im gewählten Intervall genau einmal appweit;
  abschaltbar, manuell weiterhin verfügbar. Kein ungefragter App-Neustart.
- Offline-/Signaturfehler sind sichtbar und wiederholbar, ein Abbruch installiert
  nichts; eine ältere oder gleiche Version wird nicht angeboten.
- Ein Update kann heruntergeladen und später ausdrücklich installiert werden.
  Offene Editoransichten, aktive Prozesse und nicht antwortende Fenster verhindern
  die Installation. Während der abschließenden Prüfung ist die UI gesperrt.
- Der Release-Workflow erzeugt auf allen unterstützten Plattformen Signaturen;
  ein abschließender Job prüft und veröffentlicht ein vollständiges `latest.json`.
- Bestehende 0.8.0-Installationen brauchen einmalig einen neuen Installer, weil
  ihnen der öffentliche Prüfkey fehlt; diese Grenze ist dokumentiert.
- Plattformtests und tatsächliche Installationsnachweise werden getrennt benannt.

## Decisions

1. 2026-09-16: Expliziter Nutzerauftrag; nächste Arbeit danach ist 034.
2. 2026-09-16: Automatische Suche, bewusste Installation; kein erzwungener
   Neustart laufender Arbeit. Linux-internes Update nur für AppImage gemäß Tauri.
3. 2026-09-16: Ein nativer Koordinator hält Update, Download und Installationssperre
   für sämtliche Fenster. Frontend besitzt keine direkte Installationsberechtigung.

## Tasks

- [x] Nativen Update-Koordinator und Schutz laufender Arbeit implementieren.
- [x] Appweite Anzeige, Einstellungen, Download/Abbruch/Installation ergänzen.
- [x] Signierung, Schlüsselablage und Release-Manifest für alle Plattformen einrichten.
- [x] Zustands-, Signatur-, Fehler- und UI-Regressionen prüfen; lokale App aktualisieren.
- [x] Dokumentation/Playbooks nachführen, committen/pushen; zu 034 weitergehen.
  Commit `379ea42` auf main gepusht; plattformübergreifende CI läuft.

## Verification

Ausgangsstand 0.8.0: Plugin und manueller Knopf vorhanden, Public Key leer,
keine Update-Schlüssel in GitHub, Windows ohne Update-Artefakte. Offizielle
Referenz: https://v2.tauri.app/plugin/updater/ (2026-09-16).

2026-09-16: `cargo test -p speccify-desktop`: 126 passed, 3 ignored;
`uv run pytest`: 282 passed, 1 deselected. Ruff lint/format, Cargo format,
TypeScript-Prüfung grün. `test_updates.mjs` prüft Einstellungen, Offline/Retry,
Fortschritt/Abbruch, Signaturfehler und Editor-/Prozessschutz. Echter Tauri-Client
prüft signierte und manipulierte Daten gegen lokalen HTTP-Server; Manifesttests
prüfen echte minisign-Signaturen. Mermaid-Regression grün.

Lokaler App-Build mit Developer-ID signiert, `codesign --verify --deep --strict`
grün; nach Neustart vier Fenster wiederhergestellt (PID 61854), überall derselbe
native Update-Zustand. Öffentlicher Endpoint liefert noch kein Manifest, daher
erwarteter sichtbarer Suchfehler. Bootstrap-Release und tatsächliche N→N+1-
Installation auf macOS/Windows/Linux noch ausstehend. Implementierung zur
menschlichen Abnahme geparkt; danach Arbeit an 034.

## Questions

Keine für die Implementierung.
