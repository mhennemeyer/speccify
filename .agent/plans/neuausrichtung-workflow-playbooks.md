---
lifecycle: active
status: Entwurf 2026-08-06 — Neuausrichtung von Komponenten-Specs auf Workflow-Playbooks; Stage 0 (Refinement mit BO) offen, danach W1
sessionId: neuausrichtung-workflow-playbooks
---
# Plan: Neuausrichtung — Specs als Workflow-Playbooks für Agents

> **Status**: 📋 Entwurf, wartet auf Refinement (2026-08-06)
> **Ersetzt**: [`archive/pivot-open-source-git-composer.md`](./archive/pivot-open-source-git-composer.md) (P1–P6.1 geliefert)
> **Auslöser (BO, 2026-08-06)**: Der ursprüngliche Zweck ist vom technischen Fortschritt bei Agents überholt. Feingranulare Komponenten-Specs, aus denen man größere Komponenten und Anwendungen zusammensetzt, bringen kaum noch Mehrwert — moderne Agents sind auf diesem Level bereits gut genug.

---

## Neue Vision in einem Satz

> *„Eine Spec ist ein **Playbook für einen komplexen, wiederkehrenden Workflow** — mit Quellen, Assets und Schritten. Sie enthält genau das Wissen, das ein Agent sich sonst jedes Mal neu erarbeiten müsste."*

**Das Beispiel, an dem der Plan sich messen lassen muss** (BO): *„In-App-Purchase mit 7 Tage Testzeitraum in eine macOS/iOS-App integrieren."* Zweimal gemacht, jedes Mal Stunden gekostet — Recherche in App Store Connect, StoreKit-2-Details, Sandbox-Eigenheiten, Fallstricke bei Einführungsangeboten. Genau dieses Wissen soll einmal geschrieben, versioniert, geteilt und von jedem Agent direkt konsumiert werden.

### Warum das trägt, wo Komponenten-Specs es nicht mehr tun

| | Komponenten-Spec (alt) | Workflow-Playbook (neu) |
|---|---|---|
| Was steht drin | Props, Events, Slots einer Komponente | Schritte, Quellen, Assets, Fallstricke eines Vorhabens |
| Was der Agent spart | wenig — er kann eine Button-Komponente aus dem Stand | **Recherche + Irrwege**: verstreute Doku, versteckte Bedingungen, Reihenfolge-Abhängigkeiten |
| Wert pro Spec | sinkt mit besseren Modellen | **steigt** mit Domänen-Tiefe und Aktualität |
| Halbwertszeit | kurz (Framework-Moden) | mittel bis lang, aber **prüfbar** (Quellen altern sichtbar) |

Der Hebel verschiebt sich von *Codegen* zu **kuratiertem, überprüfbarem Kontext**. Das passt zum Determinismus-Gedanken, der Speccify von Anfang an ausmacht: nicht „der Agent macht schon", sondern *pinnbar, prüfbar, teilbar*.

---

## Was bleibt, was geht

### Bleibt (und wird ausgebaut)

- **Git als Distribution + Discovery-Indizes** (P5). Für Playbooks ist das noch passender als für Komponenten: Wissen lebt in Repos, Versionen sind Tags, `speccify search` findet Playbooks.
- **Determinismus-Stack**: Resolver/MVS, Lockfile mit Bundle-Hash und Commit-Pin, `verify`. Ein Playbook, das man vor drei Monaten benutzt hat, muss reproduzierbar dasselbe sagen.
- **MCP-Server + HTTP-API + CLI als gleichwertige Wege** (Cross-Consistency-Vertrag). Der MCP-Server wird sogar zum *Hauptweg*: dort holt sich der Agent das Playbook.
- **Desktop-App + Toolkit** (Exec/Discovery/Parallels/desktop-ui-MCP, Agent-Terminal, Server-Tab). Genau die Bausteine, die der kontextsensitive Chat braucht.
- **Composer-Shell** (Vite-React-SPA, Tauri-2-fähig, agent-bedienbar über HTTP) — wird vom Editor zum Viewer umgebaut, nicht weggeworfen.
- **Wiederverwendung/Komposition**: Playbooks referenzieren Playbooks (Child-Nodes). Das Konzept bleibt, nur die Knoten sind jetzt Workflows statt UI-Komponenten.

### Geht (Rückbau, D1)

Der gesamte Codegen-Zweig trägt in der neuen Welt nichts mehr:

- Mock-Codegen (`codegen/mock_react.py`), App-Builds (`codegen/app_react.py`, `speccify build`), LLM-Targets React/SwiftUI/Angular (`react_llm`, `swiftui_llm`, `angular_llm`, `stub`), Replay-Cache, Conformance-Build-Smoke, Visual-Regression.
- Zugehörig: `speccify mock`/`build`/`pull`/`verify`(Output-Teil)/`conformance`, MCP-Tools `mock`/`build`/`render`, Web-Routen `/api/v1/mock*`, `/api/v1/build`, `/api/v1/render`, die `app:`-Blöcke, `registry-fixtures/org/demo-app`, `apps/composer`-Editorteile (Inspector, Wiring-Formular, Undo/Redo auf Modell-Edits, Drag & Drop).
- Grob: **~2.700 Zeilen Codegen + ~10 Testdateien + 3 CI-Jobs**.

**Empfehlung**: konsequent zurückbauen, exakt nach dem bewährten Muster des Registry-Rückbaus (P1): Archiv-Branch `archive/pre-playbook-pivot` + Löschung im Arbeitszweig. Begründung: Der Zweig kostet Wartung bei jedem Schema-Schritt, prägt Doku und Website, und *ohne* Rückbau bleibt unklar, was das Produkt eigentlich ist. Der BO hat dieselbe Linie schon einmal bestätigt („kein Kompatibilitäts-Ballast, Start bei Null ist ok, solange nichts Echtes darauf aufbaut") — und es baut nichts Echtes darauf auf.

*Nicht* betroffen: `assets` als Konzept. Ein Playbook darf Code-Templates mitbringen (StoreKit-Boilerplate, Config-Dateien) — das sind statische Dateien im Bundle, kein Codegen.

---

## Architektur-Skizze

### 1. Die Playbook-Spec (Schema v2, harter Cut)

`kind: playbook` wird die tragende Spec-Art. Entwurf am IAP-Beispiel:

```yaml
schema_version: 2
id: "@org/iap-trial-apple"
version: 1.0.0
kind: playbook
title: In-App-Purchase mit 7-Tage-Testzeitraum (macOS/iOS)
summary: >
  StoreKit-2-Abo mit Einführungsangebot „7 Tage kostenlos" — von der
  Konfiguration in App Store Connect bis zum Sandbox-Test.

applies_to:                       # wann ist dieses Playbook das richtige?
  platforms: [macos, ios]
  requires: ["Xcode >= 16", "Apple Developer Program"]
  keywords: [storekit, iap, subscription, trial]

prerequisites:
  - Apple-Developer-Account mit aktiver Vereinbarung für bezahlte Apps
  - App-Eintrag in App Store Connect existiert

steps:
  - id: asc_product
    title: Abo-Produkt mit Einführungsangebot anlegen
    detail: |
      Markdown — was zu tun ist, in welcher Reihenfolge, worauf zu achten.
    sources: [asc_subscriptions]          # Verweise in `sources`
    assets: [assets/asc-subscription.png]
    verify: Produkt steht in App Store Connect auf „Bereit zur Übermittlung".

  - id: storekit_file
    title: StoreKit-Konfigurationsdatei einbinden
    uses: "@org/xcode-add-resource@^1"    # Wiederverwendung: Child-Playbook
    assets: [assets/Trial.storekit]

sources:                            # das teure Rechercheergebnis
  - id: asc_subscriptions
    title: Configure auto-renewable subscriptions
    url: https://developer.apple.com/help/app-store-connect/...
    retrieved: 2026-08-06
    note: Abschnitt „Introductory Offers"

pitfalls:
  - Sandbox rafft Zeit: ein Jahresabo läuft in ~1 Stunde ab, 7 Tage in Minuten.
  - Ein Einführungsangebot gilt pro Familienfreigabe-Gruppe, nicht pro Account.

acceptance:
  - given: frisch installierte App, frischer Sandbox-Account
    when: Trial gestartet
    then: Ablaufdatum 7 Tage in der Zukunft, keine Belastung
```

**Tragende Konzepte**: `steps` (geordnet, mit `uses` für Child-Playbooks), `sources` (Links **mit Abrufdatum** — dadurch ist Alterung messbar), `assets` (Dateien im Bundle), `pitfalls` (das, was man beim zweiten Mal wieder vergessen hätte), `applies_to` (Auswahlkriterien für Agent und Suche), `acceptance` (bleibt aus v1: Given/When/Then).

Bewusst **nicht** drin: eine Ausführungs-Engine. Der Agent ist der Executor; das Playbook ist Kontext, keine Skriptsprache.

### 2. Specs werden Bundles (Verzeichnisse statt Einzeldatei)

Assets erzwingen die strukturelle Änderung: eine Spec ist künftig

```
<spec-wurzel>/
  spec.speccify.yaml
  assets/…            (Bilder, Templates, Konfigurationen)
```

Konsequenzen: `LocalRegistry`/`GitRegistry` lesen ein Verzeichnis statt einer Datei (Git: `ls-tree` + `cat-file` über den Teilbaum, weiterhin ohne Working Tree); das Lockfile pinnt einen **Bundle-Hash** (deterministisch über sortierte Pfade + Inhalte) statt des YAML-Hashes; `speccify verify` prüft ihn.

### 3. Composer: Viewer + kontextsensitiver Chat

- **Viewer** (kein manueller Edit-Modus, D3): Schritte als Diagramm/Sequenz, Quellen-Liste mit Alter, Asset-Vorschau, Child-Playbooks als aufklappbarer Baum. Alles read-only.
- **Auswahl ist Kontext**: Klick auf Schritt/Quelle/Asset/Child setzt eine Selection. Diese Selection ist über MCP abfragbar — der Agent im Chat daneben *weiß*, worüber gesprochen wird, ohne dass man es hinschreibt.
- **Chat**: Änderungen schlägt der Agent vor, der Nutzer übernimmt sie (Diff → speichern). Kein Formular-Editieren mehr.

**Anbindung (D2)**: primär über den **vorhandenen Agent-Weg** — Agent-Terminal (PTY) in der Desktop-App plus MCP-Server. Neues Tool `composer_selection` (Muster: das bestehende `ask_bo` im desktop-ui-MCP) liefert die aktuelle Auswahl; `playbook_get` liefert die Spec. Kein eigener LLM-Client, kein API-Key im Produkt, keine zweite Agent-Implementierung. Ein direkter LLM-Endpoint im Web-Backend bleibt als spätere Option für den Browser-only-Fall.

### 4. Was an die Stelle von Conformance tritt

Playbooks haben eine andere Qualitätsfrage als Code: nicht „kompiliert es", sondern **„stimmt es noch"**. Deshalb `speccify check`:

- Sind alle `sources[].url` erreichbar (HTTP-Status, optional Content-Hash)?
- Wie alt ist `retrieved` — Warnung ab Schwellwert (z. B. 180 Tage)?
- Existieren alle referenzierten `assets`, sind alle `steps[].uses` auflösbar, zeigen `steps[].sources` auf deklarierte Quellen?

Der Netz-Teil läuft wie Conformance hinter einem Marker/eigenem CI-Job; die strukturellen Prüfungen laufen offline in der Standard-Suite.

---

## Phasen

Jede Phase ist einzeln shippable; nach jeder Phase Go/No-Go wie bisher.

### W0 — Refinement (jetzt)
Offene Punkte mit dem BO klären (unten), Entscheidungen hier festschreiben.

### W1 — Schnitt & Fundament ✅ (2026-08-06)

> Geliefert: Archiv-Branch `archive/pre-playbook-pivot`, Rückbau des kompletten Codegen-Zweigs (inkl. Workspaces und der alten Schemata), neues Playbook-Schema (Neustart bei `schema_version: 1`), `core/playbook.py` mit Validierung, Bundles in Local-/GitLibrary, Bundle-Hash im Lockfile v1, CLI/MCP/Web auf Playbooks, Viewer statt Editor, zwei echte Referenz-Playbooks, `docs/playbooks.md` + `docs/viewer.md`, CI-Smoke neu. **115 Pytest, 1/1 Playwright, MCP-Smoke, Viewer-Build, Doku-Site grün.**
>
> Vorgezogen aus W3: der Composer ist bereits ein lesender Viewer (Bibliothek, Schritte, Quellen mit Alter, Assets inline, Sprung ins Child-Playbook, Selection-State) — sonst wäre das Repo nach dem Rückbau kaputt gewesen.
- Archiv-Branch `archive/pre-playbook-pivot`, dann Rückbau des Codegen-Zweigs (D1).
- Spec-Schema **v2** mit `kind: playbook` (harter Cut, kein Migrationspfad); Validator + Lint.
- Specs als **Bundles**: Local-/GitRegistry lesen Verzeichnisse, Bundle-Hash im Lockfile, `verify` darauf.
- Referenz-Playbook `@org/iap-trial-apple` aus dem BO-Beispiel + ein kleines Child-Playbook (beweist Wiederverwendung).
- **Definition of Done**: `speccify lint` + `verify` grün auf dem Referenz-Playbook; Suite grün ohne Codegen-Tests.

### W2 — Agent-Vertrag (MCP + HTTP + CLI) ✅ (2026-08-06)

> Geliefert: `speccify check` (Struktur + Quellen-Alter offline, Link-Erreichbarkeit hinter `--links`), MCP-Tools `playbook_asset` und `playbook_check` (damit 9 Tools), Doku in `docs/playbooks.md`/`docs/viewer.md`. Der Agent-Vertrag ist per Test gepinnt: list → get → dem delegierten Schritt ins Child folgen → Schritt lesen → Asset lesen, nur über Tools. **130 Pytest, `-m links` grün.**
>
> Bewusste Feinheit: Strukturfehler verdecken Alters-Warnungen — bei einem kaputten Playbook ist die Liste alter Quellen nur Rauschen.
- MCP-Tools: `playbook_search` (über Discovery-Index), `playbook_get` (Spec + Quellen + Asset-Liste), `playbook_step` (ein Schritt inkl. aufgelöster Quellen), `playbook_asset` (Datei-Inhalt).
- HTTP-Pendants + CLI (`speccify show`, `speccify steps`), Cross-Consistency-Test wie gehabt.
- `speccify check` (Struktur offline, Link-Rot hinter Marker).
- **Definition of Done**: ein Agent löst das IAP-Vorhaben allein über MCP — Suche → Playbook → Schritte → Assets, ohne die Doku-Site zu öffnen. Als headless-E2E gepinnt.

### W3 — Viewer (Rest)
- Grundgerüst steht seit W1. Offen: Schritt-**Diagramm** (Sequenz/Abhängigkeiten), Markdown-Rendering im `detail` statt `<pre>`, Alters-Warnung an Quellen (> 180 Tage), Suche/Filter über die Bibliothek, Index-Treffer im Viewer öffnen.
- **Definition of Done**: Referenz-Playbook ist im Viewer vollständig erfassbar; Playwright-Smoke auf Navigation + Selection.

### W4 — Kontextsensitiver Chat
- MCP-Tool `composer_selection` + Selection-Push aus dem Viewer.
- Chat-Panel neben dem Viewer (Agent-Terminal-Anbindung), Änderungsvorschläge als Diff mit „übernehmen".
- **Definition of Done**: Schritt anklicken, „warum ist das nötig?" fragen, Antwort bezieht sich nachweislich auf den ausgewählten Schritt; ein vorgeschlagener Zusatz landet nach Bestätigung in der Spec.

### W5 — Doku, Website, Ökosystem
- `docs/` neu schneiden: Playbook-Format, Agent-Vertrag, Viewer/Chat, Git-Quellen (bleibt), `check`. Alte Seiten (Mocks, App-Builds, Composer-Editor) entfernen.
- Website: Hero, „How it works", Doku-Sidebar, Index-Format (Keywords/Plattformen für Playbooks), `docs/launch.md` neu texten.
- Saatgut: die ersten echten Playbooks (BO-Wissen) als Index-Einträge.

---

## Entscheidungsvorschläge (bitte bestätigen oder korrigieren)

- **D1 — Rückbau des Codegen-Zweigs**: Archiv-Branch + Löschung (Mocks, App-Builds, LLM-Targets, Replay-Cache, Conformance, Visual-Regression, Composer-Editor). *Alternative*: einfrieren statt löschen — kostet dauerhaft Wartung und verwässert das Produktbild. **Empfehlung: löschen.**
- **D2 — Chat-Anbindung**: über Agent-Terminal + MCP (`composer_selection`), kein eigener LLM-Client im Produkt. *Alternative*: Chat-Endpoint im Web-Backend mit API-Key — nötig, wenn der Composer auch ohne Desktop-App/Agent nutzbar sein soll. **Empfehlung: MCP-Weg zuerst.**
- **D3 — Kein Edit-Modus**: Der Viewer ist read-only; Änderungen kommen als Agent-Vorschlag mit Diff. Ein YAML-Textfeld bleibt als Notausgang. (BO-Vorgabe, hier nur festgehalten.)
- **D4 — Schema v2 als harter Cut**: keine Migration von v1-Komponenten-Specs; die sieben Referenz-Specs entfallen mit dem Codegen. **Empfehlung: ja** — es baut nichts Echtes darauf auf.
- **D5 — Bundles statt Einzeldatei**: Spec = Verzeichnis mit `spec.speccify.yaml` + `assets/`; Lockfile pinnt Bundle-Hash. Ohne das gibt es keine Assets. **Empfehlung: ja.**

## Offene Fragen an den BO

1. **Sprache der Playbooks**: Doku und Repo sind deutsch, ein OSS-Ökosystem für Playbooks wäre auf Englisch reichweitenstärker. Für Schema-Felder und Referenz-Playbooks brauche ich eine Festlegung.
2. **Referenz-Playbook**: Ich kann das IAP-Playbook als Entwurf aus öffentlichen Quellen schreiben — aber das eigentliche Wissen (die Fallstricke aus deinen zwei Durchläufen) steckt bei dir. Entwurf schreiben und du korrigierst? Oder du diktierst grob und ich forme?
3. **Granularität**: Wie klein darf ein Child-Playbook sein („Datei in Xcode-Target aufnehmen")? Das entscheidet, ob Wiederverwendung real wird oder Deko bleibt.
4. **Name/Vokabular**: bleibt es bei „Spec" (dann mit `kind: playbook`), oder soll das Produkt-Vokabular auf „Playbook" wechseln (CLI-Kommandos, Doku)? Betrifft W5 und die Website.

---

## Risiken

- **Wert steht und fällt mit Inhalt**: Zehn gute Playbooks sind mehr wert als jede Schema-Feinheit. Deshalb ist das Referenz-Playbook Teil von W1 und nicht erst von W5 — wenn sich das IAP-Beispiel nicht sauber schreiben lässt, stimmt das Format nicht.
- **Alterung**: Ein Playbook mit toten Links ist schlimmer als keins. `speccify check` (W2) ist deshalb kein Nice-to-have.
- **Abgrenzung zu „Prompt-Sammlung"**: Was Speccify unterscheidet, ist der Determinismus-Stack — Versionen, Hashes, Commit-Pins, prüfbare Quellen. Das muss in Doku und Launch-Text vorn stehen, sonst wirkt es beliebig.
- **Rückbau-Umfang**: ~2.700 Zeilen plus Tests und CI-Jobs. Der Archiv-Branch macht ihn umkehrbar; trotzdem sollte W1 in einem Rutsch laufen, damit die Suite nie länger rot ist.
- **Zu viel Struktur**: `steps`/`sources`/`assets` sind genug für den Anfang. Alles weitere (Fortschritts-Journal, Varianten, Conditionals) erst, wenn ein zweites echtes Playbook es erzwingt.
