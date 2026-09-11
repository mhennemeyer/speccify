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

Verfeinerte englische Landingpage: großes Board-Motiv nach dem Einstieg,
ergänzender Skill-Blick im App-Abschnitt. Englische Features-Seite mit acht
bebilderten Gruppen, nach Besonderheit sortiert; IDE/Git am Ende. Wiederholbare
Aufnahme der echten React-UI mit festen öffentlichen Demodaten im macOS-Layout.
Website-Playbook hält Auswahl/Positionierung fest; lokaler Skill die Aufnahme.
Deutsche Marketing-Lokalisierung pausiert. Kein App-Redesign, kein neuer Release,
keine Domain-Migration und kein Deployment.

## Acceptance

- Desktop zeigt die App früh und groß; Mobilansicht hat keinen horizontalen
  Überlauf und bietet Zugriff auf das Bild in voller Größe.
- Alle Motive zeigen vorhandene Funktionen, keine privaten Daten, keine
  echten Terminalsitzungen und keine erfundenen Bedienelemente.
- Democharakter und Aufnahmeverfahren sind nachvollziehbar; Bilder haben
  Alt-Texte, feste Maße und komprimierte Auslieferung.
- Ein dokumentierter Befehl reproduziert Auswahl, Layout, Theme und Daten;
  fehlende UI-Elemente oder externe Netzaufrufe führen zu einem Fehler.
- Playbook, Skill und UI-Bestand werden gemeinsam gepflegt. Nutzer nimmt die
  visuelle Variante ab; Umsetzung allein ist keine Abnahme.
- Features ist in der Navigation erreichbar, erklärt die bestehenden Fähigkeiten
  in bebilderten Gruppen und priorisiert Skills/Tools vor IDE/Git. Neue Texte
  sind Englisch; /de/ verweist zur englischen Landingpage.

## Decisions

- D5, 2026-09-11: Nutzer bestätigt den visuellen Ansatz, fordert aber Skills/Tools
  statt Git als Landingpage-Schwerpunkt und eine bebilderte Features-Seite,
  nach Besonderheit sortiert. Bestehende Bilditeration hier weiterführen.
- D6: Neue Marketing-Seiten und Demoinhalte nur Englisch. Deutsche Landingpage
  vorerst zur englischen Version weiterleiten; vorhandene DE-Dokumentation nicht
  löschen oder weiter übersetzen. Echte deutsche App-Labels bleiben unverändert.
- D7: Nur lokale Umsetzung, kein Push/Deployment. Wiederverwendbaren Aufnahme-Skill
  erweitern statt einen zweiten, nahezu identischen Skill anzulegen.

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

- [x] (added) Vorhandene Fähigkeiten priorisieren und Landingpage auf Skills ausrichten.
- [x] (added) Englische Features-Seite mit verlinkter Navigation und Screenshots umsetzen.
- [x] (added) Öffentliche Fixtures und Aufnahme-Skill um Feature-Motive erweitern.
- [x] (added) Responsive Seiten und reproduzierbare Bilder prüfen, Playbooks nachführen.

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

### 2026-09-11 · app-screenshots / skill-creator · Feature-Iteration 1 · ok

- Bestehenden lokalen Aufnahme-Skill verwendet und erweitert; kein zweiter Skill,
  kein Bibliotheksexport. Neue Feature-Gruppen gegen Projekt-Views, UI-Bestand
  und Core/MCP-Verträge geprüft; geplante Funktionen klar abgegrenzt.
- `pnpm screenshots:app` zweimal: alle acht PNGs bytegleich. SHA-256 für den
  neuen Landingpage-Schwerpunkt skills.png:
  `19668e7dd95f0238752571baa645d68a127983b4c4cdf4ef4e5cb4deddbdead8`;
  tools.png: `2ea273bdad2735c173b30e84a866a59a580f5ce36b7eba525e4646bd1f51daff`.
- Acht Originalbilder und vollständige Features-Desktopseite sowie mobiler
  Einstieg visuell geprüft. Fixture-Dokumente Englisch, echte UI-Labels unverändert.
  Diagramm/Plattformstatus ausdrücklich Demo; keine privaten Inhalte oder nativen
  Aktionen. Aufnahme prüft alle Motive auf fehlende Fixtures/JS-/Netzfehler.
- `pnpm marketing:build`: 93 Seiten, erfolgreich; bestehende Node-Deprecation
  und 404-Content-Warnung unverändert. Neue responsive WebPs ca. 10–126 KB.
- `node scripts/test_landing_screenshots.mjs`: Landingpage/Features jeweils
  1440/390/320 px grün. Reihenfolge, acht bebilderte Gruppen, Navigation,
  Dokumentationslinks, Alt-Texte, Bildbudget, Überlauf, Tastatur/volle Bildgröße,
  Sprunglinks ohne JavaScript und /de/-Weiterleitung geprüft.
- Fünf Desktop-UI-Suiten erneut grün: Spec-Navigation, UI-Farben, Aktionsausgabe,
  Workflow, Git. Desktop-Typecheck, Skill-Validierung und `git diff --check` grün.
  Vorhandene Dokumentationsbilder unter assets/app unverändert.
- Website-Playbook, Produktvision und UI-Baum nachgeführt. Native App weiterhin
  PID 18058 / Port 18768; lokale Vorschau auf 4321. Kein App-Neustart, kein Push,
  kein Deployment. Weiterhin Doing/ready zur visuellen Abnahme der neuen Variante.

## Questions

Keine blockierende Entscheidung; Platzierung/Größe nach Sichtung verfeinern.
