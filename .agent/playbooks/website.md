---
description: Landingpage, Produktbilder und wiederholbare visuelle Abnahme
---
# Website: Produkt sichtbar machen

Lebendes Playbook für `apps/marketing/`. Produktvision: [Weiterentwicklung](weiterentwicklung.md).
Aktuelle Bilditeration: [Spec 023](../specs/023-landingpage-app-screenshots/SPEC.md).

## Erste Bildvariante · 2026-09-11

Zwei Motive, kein Karussell. Erst das Produkt zeigen, dann Details erklären.
Die Bildauswahl ist implementiert, aber noch nicht menschlich abgenommen.

| Ort | Motiv | Darstellung / Zweck |
| --- | --- | --- |
| Direkt unter Hero und CTAs, vor Problem/Idee | Projektfenster: Board, ausgewählte Tasks, Terminal | bis 1104 CSS-px breit; drei Stationen und menschliche Abnahme sichtbar |
| Unterer App-Abschnitt „Von der Spec zum Commit“ | Ausschnitt des tatsächlichen Git-Composers | ca. 675 CSS-px neben kurzem Text; mobil untereinander |

Hero-Kopie bewusst kürzer, damit die App früher sichtbar ist. Beide Sprachfassungen
verwenden dieselben deutschen App-Motive; die App selbst ist noch nicht durchgängig
lokalisiert. Captions/Alt-Texte sind sprachbezogen. Kein Versprechen nahtloser
Terminal-Wiederaufnahme, solange das nicht abgenommen ist.

## Kanonische Quellen

- Landingpages: `apps/marketing/src/pages/index.astro` und `de/index.astro`.
- Gemeinsame Bildkomponente: `apps/marketing/src/components/AppScreenshot.astro`.
  Feste Bildmaße, responsive WebP-Varianten, erstes Bild eager/high, Detailbild lazy.
  Vergrößern über einen normalen Bildlink: Tastatur und ohne JavaScript nutzbar.
- Originale: `apps/marketing/src/assets/landing/board.png` und `git.png`.
  Alte Dokumentationsbilder in `assets/app/` separat halten; sie haben andere
  Motive und Bildunterschriften. Keine beiläufige Ersetzung durch Detailausschnitte.
- Aufnahme-Skill: [app-screenshots](../skills/app-screenshots/SKILL.md).
- Fiktives Projekt `OrbitNotes`: `apps/desktop/dev/marketing-fixture.js`.
  Sechs Specs, ausgewählt `005-suche`, zwei von drei Tasks erledigt; eine weitere
  Spec wartet auf menschliche Abnahme. Terminalausgabe ausdrücklich als Demo-Lauf.

Die Bilder stammen aus den echten React-Komponenten mit einer kontrollierten
Tauri-Bridge im Browser auf macOS. Es sind **keine Aufnahmen nativer Fenster**.
Die dekorativen macOS-Ampelpunkte entstehen ausschließlich im Website-Rahmen;
Produktinhalte/Bedienelemente werden nicht nachgezeichnet oder nachträglich verändert.
Weder echte Nutzerprojekte noch private Sessions noch reale Tests/Commits verwenden.

## Aufnahme und Prüfung

Am Repo-Root, macOS mit installiertem Chrome:

```sh
pnpm install --frozen-lockfile
pnpm screenshots:app
pnpm marketing:build
pnpm marketing:preview --host 127.0.0.1 --port 4321
node scripts/test_landing_screenshots.mjs
```

Playwright ist als Entwicklungsabhängigkeit gepinnt. Der Skill beschreibt die
Alternative mit gebündeltem Chromium. Das Aufnahmeskript startet und beendet seinen
eigenen Vite-Server auf einem freien Loopback-Port; die persönliche App bleibt offen.
Viewport 1344 × 840, Pixeldichte 2, Dark Theme, deutsche Locale, feste Demo-Uhr.
Die Git-Aufnahme erfasst das echte `Git-Arbeitsbereich`-Element statt eines
nachträglich ausgerechneten Pixel-Ausschnitts.

Vor Freigabe:

- Bilder selbst öffnen: richtige Auswahl, lesbare Texte, keine Lade-/Fehlerzustände,
  privaten Pfade oder echten Sitzungsinhalte. Demodaten sind ausdrücklich gekennzeichnet.
- Nach Änderungen am Aufnahmeverfahren zweimal aufnehmen und Hashes vergleichen;
  Layout/Fonts/Browserupdates können eine bewusste Neufreigabe erfordern.
- `/` und `/de/` bei 1440, 390 und 320 px prüfen: kein Überlauf, Bild früh sichtbar,
  Vergrößerungslink und Tastaturfokus funktionieren. Pro ausgeliefertem Screenshot
  unter 200 KB anstreben; Original-PNG wird nur beim Vergrößern geladen.
- Ändert sich die gemeinsame Demo-Bridge, auch die fünf bestehenden Desktop-
  Browser-Suiten ausführen. Keine Screenshot-spezifischen CSS-Hacks in der Produkt-UI.
- Festgestellte Fehler im aktiven Spec-Protokoll halten und die Aufnahme erneut prüfen.

## Laufende Pflege und Veröffentlichung

Bei sichtbaren Änderungen an Board, Inspektor, Terminal oder Git zuerst die Motive
gegen den neuen Produktstand prüfen. Nicht bei jedem Backend-Commit neu aufnehmen.
Bild, Fixture, Aufnahme-Skill und betroffene Texte im selben Änderungssatz pflegen.

Diese erste Designvariante zunächst lokal vergleichen/refinen; noch nicht deployen.
Die allgemeine Commit-/Push-Erlaubnis bleibt bestehen. Ein Push auf `main` löst
Website-Workflows aus und ist daher eine bewusste Veröffentlichung, keine Vorschau.
Domain-/Sprachmigration aus 003 sowie Rechtstexte/DNS sind nicht Teil dieses Playbooks.

Nächste visuelle Fragen: Reicht das Board als einziges Motiv? Ist der Git-Ausschnitt
hilfreich oder zu prominent? Braucht der Einstieg nach Rückmeldung mehr Bildfläche?
