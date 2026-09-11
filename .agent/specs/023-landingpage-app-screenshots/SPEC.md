---
station: Doing
created: 2026-09-11
needs_human: true
ready: true
parent: null
---
# App-Screenshots auf der Landingpage

## Why

Die Landingpage erklärt Speccify bisher fast ausschließlich mit Text. Der erste
Eindruck soll die tatsächliche App zeigen und sich gemeinsam visuell verfeinern lassen.

## What

Erste Variante für EN/DE: großes Board-Motiv nach dem Einstieg, ergänzender
Git-Detailblick im App-Abschnitt. Wiederholbare Aufnahme der echten React-UI
mit festen, unverfänglichen Demodaten im macOS-Layout. Website-Playbook hält
Bildauswahl/Platzierung fest; projektspezifischer Skill hält die Aufnahme fest.
Kein App-Redesign, kein neuer Release, keine Domain-Migration.

## Acceptance

- Desktop zeigt die App früh und groß; Mobilansicht hat keinen horizontalen
  Überlauf und bietet Zugriff auf das Bild in voller Größe.
- Beide Motive zeigen vorhandene Funktionen, keine privaten Daten, keine
  echten Terminalsitzungen und keine erfundenen Bedienelemente.
- Democharakter und Aufnahmeverfahren sind nachvollziehbar; Bilder haben
  Alt-Texte, feste Maße und komprimierte Auslieferung.
- Ein dokumentierter Befehl reproduziert Auswahl, Layout, Theme und Daten;
  fehlende UI-Elemente oder externe Netzaufrufe führen zu einem Fehler.
- Playbook, Skill und UI-Bestand werden gemeinsam gepflegt. Nutzer nimmt die
  visuelle Variante ab; Umsetzung allein ist keine Abnahme.

## Decisions

- D1, 2026-09-11: Zunächst zwei Motive statt Karussell. Board erklärt Planung
  und Abnahme; Git-Detail erklärt die direkte Umsetzung. Kein Autoplay.
- D2: Browseraufnahme der echten Desktop-Komponenten mit macOS-Plattform und
  kontrollierter Bridge, kein nachgezeichnetes UI und keine native OS-Aufnahme.
  Bildunterschriften nennen Demodaten. Persönliche laufende App bleibt unberührt.
- D3: Suche nach `screenshot` und `website` in der konfigurierten Skill-Bibliothek
  ohne Treffer. Neuer lokaler Skill; kein automatischer Export in andere Repos.
- D4: Veraltete Plan/Ticket-Texte auf der deutschen Landingpage und unbelegte
  nahtlose Sitzungsfortsetzung auf der englischen Seite im betroffenen Text korrigieren.

## Tasks

- [x] Landingpage, Demo-Bridge und bestehende Aufnahmewege prüfen.
- [x] Kuratierte Demodaten und reproduzierbare Aufnahme implementieren.
- [x] Motive einbinden und Desktop/Mobilansicht visuell prüfen.
- [x] Website-Playbook, Aufnahme-Skill und Bestandsdokumentation aktualisieren.

## Verification

### 2026-09-11 · speccify / skill-creator / app-screenshots · Iteration 3 · ok

- Bibliothekssuche `speccify search screenshot` / `website`: keine Treffer.
  Globaler CLI-Einstieg funktioniert; lokaler `.venv/bin/speccify` derzeit ohne
  importierbares `speccify_cli` (keine Umgebungsreparatur in diesem Schnitt).
- Iteration 1: Aktivitätslabel bleibt nach Abschluss sichtbar; Aufnahme wartet
  nun auf fehlenden Spinner statt auf verschwundenes Label. Feste Demo-Uhr verhindert
  wechselnde Laufzeiten, Render-Wartepunkt verhindert unstabile Eingabefeld-Pixel.
- Iteration 2: Eigener `assets/landing/`-Namensraum eingeführt; vorhandene
  Dokumentationsbilder bleiben exakt unverändert. Keine nachträgliche Bitmap-Bearbeitung.
- Iteration 3: Wiederholte `pnpm screenshots:app`-Läufe liefern identische SHA-256:
  Board `6ed10b5f85f3c33e2e66a995a3e1a0b4371953d9c79fb1cbe5513aa24691d22a`,
  Git `d14a3a6f6a506e8f033a57eff5e112c2605dad6bd39d973c442d152d5b3075a5`.
- `pnpm marketing:build`: 92 Seiten; responsive WebP-Bilder. Board-Varianten
  ca. 19–130 KB. Bestehende Node-Deprecation-/404-Content-Warnung, kein Buildfehler.
- `node scripts/test_landing_screenshots.mjs`: EN/DE × 1440/390/320 px bestanden;
  Bilder geladen, Alt-Texte/Maße/srcset, unter 200 KB, kein Überlauf, frühe
  Platzierung, Tastaturfokus, volle Bildgröße auch ohne JavaScript.
- Fünf bestehende Desktop-UI-Suiten grün: Spec-Navigation, Farbkontrast,
  Aktionsausgabe, Workflow, Git. Desktop-Typecheck und `git diff --check` grün.
- Neuer Skill: `speccify lint` und `skill-creator/scripts/quick_validate.py` grün.
- Originalbilder, gesamte DE-Desktopseite und DE-Mobileinstieg visuell geprüft.
  Browser-Captures belegen keine native Betriebssystemintegration oder Produkt-Abnahme.
- Lokale Vorschau auf 127.0.0.1:4321 offen; native App PID 18058 / Port 18768
  unverändert offen. Designvariante noch nicht veröffentlicht; menschliche Abnahme offen.

## Questions

Keine blockierende Entscheidung; Platzierung/Größe nach Sichtung verfeinern.
