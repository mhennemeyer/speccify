# Plan: Umbenennung von „flowcation"

> **Status**: 📋 Entwurf – Namensfindung & Markenrecherche
> **Erstellt**: 2026-05-05
> **Update 2026-05-05**: Vollständige Verfügbarkeitsrecherche (Domain `.com/.dev/.io`, GitHub-Org/-User, npm-Registry, aktive Webseite) für alle Kandidaten der vorherigen Liste. Disqualifizierte Namen sind unten dokumentiert. Liste enthält jetzt nur Kandidaten, die diesen Vor-Check bestanden haben.
> **Update 2026-05-06**: Zwei Eigenvorschläge des Owners ergänzt und bewertet: **`speccify`** (Anschluss an früheres OSS-Projekt `mhennemeyer/speccify`, mit Vorbenutzungs-Argument) und **`zouop`** (Kunstwort, `.com` bereits im Besitz). Persönlicher Eindruck zur bisherigen Top-5: erste vier Namen wirken auf den Owner unprofunden, einzig `speconaut` „witzig", aber Witz nicht prioritär.
> **Update 2026-05-06 (Domain-Strategie)**: Für `speccify` ist Strategie **`.io` (international) + `.de` (DE-Markt)** als kanonisches Setup festgelegt; `.com` ist *nice to have*, aber kein Muss für Dev-Tool-Zielgruppe. Details siehe neuer Abschnitt „Domain-Strategie für `speccify`".
> **Update 2026-05-06 (weitere TLDs)**: `.ch` / `.at` / `.eu` sind frei, werden aber **nicht ins Initial-Setup** aufgenommen — kein dedizierter Marketing-Hub, kein akutes Defensiv-Risiko. Begründung + Nachzieh-Trigger im Abschnitt „Weitere TLDs".
> **Hinweis zum Dateinamen**: Der bestehende `flowcation-plan.md` enthält den **Produkt-Plan** (Spec-First Komponenten-Plattform). Dieser Plan hier behandelt die **Umbenennung** und liegt deshalb separat unter `naming-plan.md`. Sobald ein neuer Name feststeht, sollten beide Dokumente (und der GitHub-Space, Domains, Branding) konsistent umgezogen werden.

---

## Warum überhaupt umbenennen?

- Recherche ergab: In Frankfurt-Bornheim existiert bereits ein **„Flowcation"** als
  - physischer Veranstaltungsraum (Arnsburger Str. 62, 60385 Frankfurt) **und**
  - SaaS-Planungsplattform für Team-Retreats.
- Aktive geschäftliche Benutzung in DE/EU mit Website, Standort, Angebot.
- Branchenüberlapp **hoch**: SaaS / Team-Tool / Productivity – genau dort, wo unser Produkt landen kann.
- Konsequenz: sehr wahrscheinliches **Unternehmenskennzeichenrecht nach § 5 MarkenG** auf Seiten der Frankfurter Firma; reines Domain-Halten begründet kein konkurrierendes Recht.
- Risiko bei Launch unter `flowcation.com`: Abmahnung, Schadensersatz, Domain-Übertragung, erzwungenes Rebranding.
- Da der Name dem Projekt **nicht wichtig** ist (Aussage 2026-05-05), ist **proaktives Umbenennen** der pragmatische und rechtssichere Weg.

---

## Anforderungen an den neuen Namen

### Inhaltlich
- Sagt in einem Satz, **was es ist** oder zumindest **in welcher Welt es spielt** (Specs, Komposition, Forge, Agent, Codegen, Multi-Target).
- Verträgt sich mit der Vision *„npm für Spezifikationen statt Code, AI-Agent als Compiler"*.
- Nicht zu eng auf eine Komponente der Pipeline (z. B. nicht „swiftui-…", nicht „cli-…").

### Formal
- International aussprechbar (DE + EN), tippsicher beim Diktieren.
- Keine peinlichen Nebenbedeutungen in EN/DE/ES/FR.
- 6–12 Buchstaben bevorzugt, kein Bindestrich.
- `.com` frei (für saubere Markenposition; `.dev`/`.io` als Ergänzung).
- GitHub-Org frei. npm-Scope frei (relevant, da wir selbst ein Package-Manager-artiges Ökosystem bauen).
- Keine Konflikte in DPMA / EUIPO / USPTO in den relevanten Klassen.

### Relevante Nizza-Klassen für die Markenrecherche
- **9** – Software
- **42** – SaaS / Hosting / IT-Dienstleistungen
- **38** – Telekommunikation/Datenübertragung
- **41** – Aus- und Weiterbildung, Online-Content
- **35** – Werbung/Marketing-Beratung

---

## Vor-Check – Methodik (für jeden Kandidaten durchgeführt)

Pro Name geprüft (Stand 2026-05-05):

1. **Domain** `.com`, `.dev`, `.io` per `whois` + HTTP-Check (aktiv genutzte Seite?).
2. **GitHub** `https://github.com/<name>` – User/Org existiert? Was wird dort gehostet?
3. **npm** `https://registry.npmjs.org/<name>` – Paket existiert?
4. Bei Treffer: Kurz inspizieren, ob Branchen-Overlap (Dev-Tooling, Spec, Codegen, Agent, PM) besteht.

Ein Kandidat ist **nur dann „realistisch"**, wenn `.com` frei ist, GitHub-Org/-User kein Dev-Tooling-Projekt zeigt, npm-Paket nicht existiert und keine aktive Website unter dem Namen läuft.

---

## ✅ Realistische Kandidaten (Vor-Check bestanden)

Alle folgenden Namen haben:
- `.com` frei (`whois` „No match"),
- keine aktive Webseite unter `.com`,
- npm-Paket nicht existent,
- GitHub-Org `https://github.com/<name>` → 404 (frei).

### 🥇 Engerer Favoritenkreis

| Rang | Name | `.com` | GitHub-Org | npm | Cluster | Stärke |
|---|---|---|---|---|---|---|
| 1 | **forgepkg** | ✅ frei | ✅ frei (404) | ✅ frei | Forge / PM | Pragmatisch, nah an `cargo`/`npm`, sofort verständlich für Devs. |
| 2 | **mosaicspec** | ✅ frei | ✅ frei (404) | ✅ frei | Komposition | Mosaik = Komposition aus Teilen, passt zu `uses:`-Verkettungen. |
| 3 | **anvilspec** | ✅ frei | ✅ frei (404) | ✅ frei | Forge | Schmiede-Bild, schmiedet Specs in Code. |
| 4 | **canonspec** | ✅ frei | ✅ frei (404) | ✅ frei | Spec / Determinismus | „Kanonische Spezifikation" – Single Source of Truth. |
| 5 | **speconaut** | ✅ frei | ⚠️ leerer User existiert (kein Repo, keine Aktivität) | ✅ frei | Spec / Brand | Eigenständig, einprägsam, Community-Branding („Speconauts"). Risiko: Username belegt → ggf. Org-Variante (`@speconauts`) wählen. |

### 🎯 Erweiterte Auswahl (alle drei Achsen sauber)

#### Komposition / Mehrteiligkeit
- `compolith.com` – „Compositional Lithography", monumental.
- `componable.com` – „able to be composed".
- `tesseraspec.com` – „Tessera" = Mosaikstein, literarisch.
- `mosaicspec.com`

#### Forge / Werkstatt
- `anvilspec.com`
- `forgepkg.com`
- `manyforge.com` – „many targets, one forge".
- `codegenkit.com`

#### Spec-zentriert
- `specoid.com`
- `specnaut.com` / `specronaut.com` (Wildcards zu `speconaut`)
- `specthos.com`
- `unboundspec.com` – trifft USP („nicht an Framework gebunden") exakt.
- `polytargets.com` – direkt: viele Ziel-Stacks.
- `codeboundspec.com`
- `kanonspec.com` (Schreibvariante zu `canonspec`)

#### Web/Loom (Spec ↔ Code „weben")
- `weavespec.com`
- `loomspec.com`
- `fabriqspec.com` / `fabriqkit.com`

#### Schräg / Markenfähig
- `sirenspec.com`
- `kompozita.com` / `komponable.com` / `komponize.com`
- `kosherspec.com` – Augenzwinkern.

---

## ❌ Aus der Liste entfernt (Vor-Check nicht bestanden)

| Name | Grund |
|---|---|
| **specmesh** | `specmesh.io` ist seit 2022 aktives OSS-Projekt („Specification driven data mesh", Liquidlabs/OSO, AsyncAPI + Apache Kafka), GitHub-Org `specmesh` belegt. Hoher Branchen-/Vokabular-Overlap (Spec-getriebenes Dev-Tooling). Werktitel-/Unternehmenskennzeichen-Risiko (§§ 5, 15 MarkenG). |
| **specforge** | `specforge.io` ist aktives Produkt **„Spec Forge – AI Development Orchestrator"** (PRD→Code, MCP/Claude-Integration, AI-Agenten) – **direkter** Konkurrenzraum. `specforge.com` (Hardware-/Software-Firma) und GitHub-Org `specforge` ebenfalls belegt. |
| **specstack** | `specstack.com` als „HugeDomains"-Verkaufsangebot geparkt, `specstack.io` antwortet (HTTP 436), GitHub-Org `specstack` belegt. Domain-Erwerb teuer und Org weg. |
| **speclab** | `.com` vergeben (aus früherer Recherche dokumentiert). |
| **speccraft** | `.com` vergeben (aus früherer Recherche dokumentiert). |
| **agentnpm** | npm-Paket `agentnpm` existiert seit 2019 → Konflikt im wichtigsten Verzeichnis. |
| **mcppkg** | npm-Paket `mcppkg` existiert → Konflikt. |
| **forgepack** | GitHub-Org `forgepack` („Forge Pack") existiert; `.com` zudem nicht zentral geprüft, `.io` daher nur Notlösung. |
| **hexspec** | GitHub-User `hexSpec` existiert. |
| **specnpm** | Domain frei, aber „npm" als Marke im Namen ist ein langfristiges Branding-Risiko (Verwechslungsgefahr/Beschreibung). Praktisch unbrauchbar fürs öffentliche Branding. |
| **spexel** | GitHub-User `spexel` (Privatperson) existiert; nur grenzwertig problematisch, aber nicht „sauber frei". |

---

## Auswahlkriterien (Bewertungsraster)

Pro Finalist mit 1–5 bewerten:

| Kriterium | Gewicht |
|---|---|
| Konzept-Fit (Spec / Komposition / Agent / Forge) | ×3 |
| Aussprache & Internationalität | ×2 |
| Einprägsamkeit / Markenpotenzial | ×2 |
| `.com` frei | ×3 |
| GitHub-Org frei | ×2 |
| npm-Scope frei | ×2 |
| Keine offensichtlichen Markenkonflikte (DPMA/EUIPO/USPTO) | ×3 |
| Tippsicher / kurz | ×1 |

---

## 🆕 Eigenvorschläge des Owners (2026-05-06)

### A) `speccify`

**Hintergrund**: Owner (`mhennemeyer`) hatte vor langer Zeit ein gleichnamiges GitHub-Projekt (<https://github.com/mhennemeyer/speccify>) mit echten Nutzern. Dadurch existiert eine **eigene Vorbenutzung** als gewichtiges Argument gegen spätere Kollisionen.

**Verfügbarkeits-Check (2026-05-06)**:

| Achse | Status | Detail |
|---|---|---|
| `speccify.com` | ⚠️ registriert | Reg. seit 2022-12-15 (Squarespace Domains II); HTTP-Test → kein Server (Verbindung schlägt fehl). Domain wahrscheinlich nur geparkt/unbenutzt. Erwerb verhandelbar, aber **nicht garantiert frei**. |
| `speccify.dev` | ✅ frei | Auf TLD-WHOIS-Ebene kein Eintrag. |
| `speccify.io` | ✅ frei | „Domain not found." |
| GitHub-Org `speccify` | ✅ frei | 404. |
| GitHub-User `mhennemeyer/speccify` | ✅ Owner-Vorbenutzung | Bestehendes Repo des Owners → **prior use**-Argument. |
| npm `speccify` | ✅ frei | 404 in Registry. |
| Marken (DPMA/EUIPO/USPTO) | ⏳ noch zu prüfen | Lt. Owner-Aussage „kein Problem zu erwarten" — formal aber bei Finalisierung zu validieren. |

**Bewertung (Raster)**:

| Kriterium | Score (1–5) | Bemerkung |
|---|---|---|
| Konzept-Fit (Spec / Komposition / Agent / Forge) | **5** | Wortstamm „spec" + Verb-Suffix „-ify" („to specify") = exakt das Produktversprechen. |
| Aussprache & Internationalität | **4** | DE/EN beide sauber, Doppel-„c" ist beim Diktieren minimal fehleranfällig. |
| Einprägsamkeit / Markenpotenzial | **4** | Klingt wie ein echtes SaaS-Produkt (vgl. `Spotify`, `Shopify`). |
| `.com` frei | **2** | Nur registriert/geparkt, nicht frei. Erwerb möglich, aber unsicher/teuer. |
| GitHub-Org frei | **5** | Org `speccify` ist 404. |
| npm-Scope frei | **5** | Paketname und damit `@speccify`-Scope frei. |
| Keine offensichtlichen Markenkonflikte | **4** | Owner-Vorbenutzung als OSS-Projekt stärkt eigene Position; formale DPMA/EUIPO-Recherche steht aus. |
| Tippsicher / kurz | **3** | 8 Buchstaben mit Doppelkonsonant. |

**Gesamteindruck**: Inhaltlich der **stärkste Kandidat** der gesamten Liste — Suffix `-ify` macht das Produkt zum Verb. Einziger echter Schwachpunkt: `.com` ist nicht frei und müsste angekauft werden (oder man startet sauber auf `.dev`). Empfehlung: **als Top-Finalist aufnehmen**, sobald geklärt ist, ob `.com` realistisch erwerbbar ist (Anfrage über Squarespace-Marketplace oder Sedo/DAN).

---

### B) `zouop`

**Hintergrund**: Kunstwort vom Owner, phonetisch gedacht (Klang zwischen „Suppe" und „Zupp"). `zouop.com` ist bereits im Besitz des Owners — entfällt damit als Akquise-Risiko.

**Verfügbarkeits-Check (2026-05-06)**:

| Achse | Status | Detail |
|---|---|---|
| `zouop.com` | ✅ in Owner-Besitz | HTTP 200 (eigene Seite/Parkseite). |
| `zouop.dev` | ✅ frei | TLD-WHOIS ohne Eintrag. |
| `zouop.io` | ✅ frei | „Domain not found." |
| GitHub-Org `zouop` | ⚠️ Username belegt | GH-User `zOuOp` (id 147283086, 2023 angelegt) existiert — Case-Variante, aber GitHub ist case-insensitive bei Name-Reservierung. **Org-Anlage `zouop` ist damit blockiert**, ähnlich Lage wie `speconaut`. |
| npm `zouop` | ✅ frei | 404 in Registry. |
| Marken | ✅ vermutlich kollisionsfrei | Kunstwort ohne semantischen Inhalt. |

**Bewertung (Raster)**:

| Kriterium | Score (1–5) | Bemerkung |
|---|---|---|
| Konzept-Fit (Spec / Komposition / Agent / Forge) | **1** | Sagt nichts aus — null inhaltlicher Bezug zu Spec/Komposition/Codegen. |
| Aussprache & Internationalität | **2** | DE/EN-Aussprache divergiert deutlich; „zou-op" wirkt im EN-Kontext fragend, im FR/ES potenziell ungewohnt. Beim Diktieren erklärungsbedürftig. |
| Einprägsamkeit / Markenpotenzial | **3** | Kurz und einzigartig, aber bedeutungsleer → muss durch Marketing aufgeladen werden. |
| `.com` frei | **5** | Bereits im Besitz. **Größter Pluspunkt.** |
| GitHub-Org frei | **2** | User `zOuOp` blockiert Org `zouop`. Plan B: anderer Org-Name. |
| npm-Scope frei | **5** | Frei. |
| Keine offensichtlichen Markenkonflikte | **5** | Kunstwort, sauber. |
| Tippsicher / kurz | **4** | 5 Buchstaben, aber „zou" tippt sich auf QWERTZ ungewohnt. |

**Gesamteindruck**: Klassischer Kunstwort-Trade-off: rechtlich/operativ sauber, aber **erklärungsbedürftig** und ohne semantischen Anker. Für ein Dev-Tool (zielgruppenorientiert auf Devs, die das Konzept in einem Wort erfassen sollen) ist das **inhaltlich problematisch** — vergleichbar mit `Bun`, `Deno`, `Vite`, die aber alle entweder kurze Anlehnungen an reale Wörter sind oder durch starkes Marketing geladen wurden. Empfehlung: **als Outsider/Backup behalten**, vor allem für den Fall, dass alle inhaltlichen Kandidaten aus Marken-/Domain-Gründen scheitern. Die geparkte `.com` ist ein echtes Asset, sollte aber nicht über die strategische Frage entscheiden, ob das Produkt einen sprechenden Namen verdient.

---

## Domain-Strategie für `speccify` (2026-05-06)

**Ausgangslage**: Owner ist deutsche Firma mit DE-Kontakten; Vermarktung primär organisch über Dev-Community + DE-Netzwerk. `speccify.com` ist registriert (Squarespace, geparkt seit 2022, kein Server), `speccify.io` und `speccify.dev` frei, `speccify.de` voraussichtlich frei.

**Entscheidung**: **`.io` als internationale Haupt-/Produkt-Domain, `.de` als deutscher Marketing-Anker**. `.com` ist *nice to have*, aber für Dev-Tool-Zielgruppe und Go-to-Market **kein Muss**.

### Warum `.io` für Dev-Tools tragfähig ist

Eine ganze Generation erfolgreicher Dev-Tools/Infrastruktur-Produkte läuft unter `.io` — oft bewusst, weil die Marke „technisch" wirken soll:

- **Package-/Build-Tooling**: `pnpm.io`, `bun.sh`, `vitejs.dev`, `turbo.build`, `nx.dev`, `astro.build`
- **Spec-/API-Tooling**: `swagger.io`, `stoplight.io`, `buf.build`, `redocly.com`
- **Infra/Platform**: `fly.io`, `sentry.io`, `dagger.io`, `linear.app`, `posthog.com`, `supabase.com`
- **DE-Beispiele**: `n8n.io` (deutsche Firma, kein `.com`), `appwrite.io`

Pattern: Dev-Tools werden über GitHub, Hacker News, Konferenzen, Discord/Slack getragen — nicht über klassische SEO-Direktnavigation. Im Funnel zählt der **Name**, nicht die **TLD**. Bei `npm install speccify` / `npx speccify init` sieht der User die TLD ohnehin nie. Im Tweet/in der Doku steht `speccify.io/docs` — `.io` signalisiert für Devs „Tooling/Infra".

### Wo `.com` real Vorteile bringt (bewusst nicht aufgeschoben)

| Faktor | Bedeutung für `speccify` |
|---|---|
| Nicht-technisches Publikum (Investor-Decks, Enterprise-Procurement) | Aktuell nicht in Pipeline → aufschiebbar |
| E-Mail-Reputation (Cold-Outbound an Nicht-Devs) | Kleiner Effekt; SPF/DKIM/DMARC wichtiger als TLD |
| Defensive Aufstellung (Squatter mit konkurrierendem Inhalt) | Niedrig, solange `.com` geparkt bleibt |
| Typo-Traffic / Direktnavigation | Klein bei via npm/Docs gefundenen Tools |
| Marken-Anmeldung | **TLD-unabhängig**, EU-/DPMA-Wortmarke schützt das Wort |

### Konkreter Plan

1. **Sofort sichern (sobald Naming-Entscheidung steht)**:
   - `speccify.io` registrieren (kanonische Produkt-/Doku-URL)
   - `speccify.de` registrieren (DE-Marketing-Anker, Impressum, lokale Inhalte)
   - `speccify.dev` registrieren (defensiv)
   - GitHub-Org `speccify` anlegen
   - npm-Scope `@speccify` reservieren
   - Social Handles: X, BlueSky, Mastodon, LinkedIn (defensiv)
   - Geschätzte Gesamtkosten: ~50 €/Jahr — **nicht verhandelbar**, sobald Name fix ist
2. **`speccify.com` anfragen, mit Limit**: Über Squarespace Domains Marketplace oder anonyme Anfrage. Realistischer Korridor für seit 2022 geparkte Domain ohne Brand-Wert: **500–3.000 USD**. Bei > 5.000 USD: nicht kaufen — `.io` reicht.
3. **Wenn `.com` nicht erwerbbar**: tragfähig. `speccify.io` = kanonisch, `speccify.de` = DE-Hub, `.com` halbjährlich beobachten (`whois` + Wayback). Falls dort später konkurrierende Inhalte aufschlagen und Wortmarke `speccify` eingetragen ist → **UDRP-Option**.
4. **Markenanmeldung priorisieren**: Das gesparte `.com`-Akquise-Geld besser in DPMA/EUIPO-Wortmarke `speccify` (ab 290 € DPMA bzw. 850 € EUIPO/Klasse) investieren — die schützt substanziell, die TLD nicht.

### Heuristik (deine konkrete Lage)

| Frage | Antwort | Folgerung |
|---|---|---|
| Zielgruppe primär Devs? | Ja | `.io` reicht |
| Bottom-up / PLG / OSS-getrieben? | Ja | `.io` reicht |
| Enterprise-Sales an Nicht-Devs in Pipeline? | Nein | `.com` aufschiebbar |
| Wortmarke geplant? | Ja, Phase 1+ | TLD-unabhängig |
| `.com`-Halter hostet konkurrierende Inhalte? | Nein (geparkt seit 3+ Jahren) | Kein Akut-Druck |
| Reversibel, wenn `.com` später doch nötig? | Ja, jederzeit anfragbar | Geringes Risiko |

**Fazit**: Mit `.io` (international) + `.de` (DE) live gehen. `.com` jederzeit später anfragbar; einziger nicht-reversibler Schritt wäre Verlust an Konkurrenten — bei geparkter Domain unwahrscheinlich.

### Weitere TLDs: `.ch`, `.at`, `.eu` — brauchen wir die?

**Kurzantwort**: Nein, nicht zwingend. Defensiv-Registrierung ist günstig (~10–25 €/Jahr je TLD), aber für Go-to-Market irrelevant. Empfehlung: **nicht im Initial-Setup**, ggf. später nachziehen, wenn DACH-/EU-Marketing konkret wird.

| TLD | Kosten/Jahr | Strategischer Wert für `speccify` | Empfehlung |
|---|---|---|---|
| `.ch` | ~10–15 € | Schweizer Markt ist klein, Devs nutzen ohnehin `.io`/`.com`. Kein eigener Marketing-Hub geplant. | **Skip** im Initial-Setup. Nachziehen, falls CH-Kunden/Niederlassung. |
| `.at` | ~10–15 € | Wie `.ch`: österreichische Devs sind über DE-Inhalte/`.de` voll abgedeckt; eigener AT-Hub unrealistisch für Phase 1–2. | **Skip**. Defensiv nur, falls jemand AT-Squatting vermuten lässt. |
| `.eu` | ~5–10 € | Politisch/regulatorisch interessant (EU-Branding, GDPR-Signal), aber im Dev-Tooling-Funnel praktisch unsichtbar. Keiner navigiert auf `*.eu`. | **Skip**, außer du planst explizit EU-institutionelle Vermarktung (Procurement, EU-Förderprogramme). |

**Begründung in einem Satz**: TLDs zahlen nur ein, wo es einen **dedizierten Marketing-Hub oder ein Defensiv-Risiko** gibt. `.io` (Doku/Produkt) + `.de` (DE-Anker) deckt 95 % deiner Zielgruppe; `.ch/.at/.eu` würden parallel gepflegte Redirects ohne Mehrwert produzieren.

**Wann doch nachziehen**:
- `.ch`/`.at`: Sobald eine konkrete Kundenliste/Niederlassung in CH oder AT entsteht.
- `.eu`: Sobald EU-Förderanträge, EU-Procurement oder explizites „EU-souveränes Tooling"-Branding Teil der Positionierung wird.
- Allgemein: Falls ein Squatter eine dieser TLDs registriert und damit Inhalte hostet, die deinen Markenraum berühren — dann reaktiv handeln (UDRP via eingetragene Wortmarke).

**Kosten/Nutzen-Faustregel**: Für ~30 €/Jahr alle drei defensiv halten ist verteidigbar, falls du Ruhe haben willst. Aber strategisch *notwendig* ist es nicht — und du investierst die ~30 € besser in die DPMA-/EUIPO-Markenanmeldung, die alle TLDs gleichzeitig schützt.

### Bewusst nicht im Setup

- **`.ai`**: trendy, aber teuer (~70–100 €/Jahr) und semantisch zu eng auf „AI" — `speccify` ist Spec-First *unterstützt durch* AI, nicht *primär* AI. Optional zusätzlich, nicht als Ersatz.
- **`.app`**: für Web-App nett, aber `speccify` ist primär CLI-/Spec-Tool — Terminal ist Hauptoberfläche.
- **`.ch` / `.at` / `.eu`**: siehe Tabelle oben — kein zwingender Initial-Bedarf.
- **Keine Rechtsberatung**: ersetzt keine Markenanwalts-Sichtprüfung vor formaler Anmeldung.

---

## Engerer Kreis: persönlicher Kurzfavorit

> **Update 2026-05-06**: Liste neu sortiert nach Owner-Feedback. Die ursprünglichen Top-4 (`forgepkg`, `mosaicspec`, `anvilspec`, `canonspec`) bleiben formal valide, fühlen sich für den Owner aber „nicht eingänglich" an. `speconaut` wirkt am freundlichsten, ist aber bewusst „witzig" gewählt — Witz ist nicht das Ziel.

1. **speccify** — inhaltlich stärkster Kandidat (Spec→Verb), starke Owner-Vorbenutzung, npm/GH-Org frei. Achillesferse: `.com` registriert (kein Server) → Akquise-Klärung nötig.
2. **forgepkg** (`forgepkg.com`) — pragmatisch, devnah, sofort verständlich; alle drei Achsen (Domain, GitHub, npm) sauber frei.
3. **mosaicspec** (`mosaicspec.com`) — starkes Bild für Komposition aus Teilen (`uses:`-Verkettungen); sauber frei.
4. **anvilspec** (`anvilspec.com`) — Forge-Bildwelt, prägnant; sauber frei.
5. **zouop** — operativ sauber + `.com` im Eigenbesitz, aber semantisch leer → Backup-Kandidat.

`canonspec` und `speconaut` bleiben in der erweiterten Auswahl; `speconaut` mit kleinem Schönheitsfehler (leerer GitHub-User vorhanden, Org-Variante `speconauts` als Plan B).

---

## Nächste Schritte

### 1. Engere Auswahl (max. 5) festlegen
- Aus den ✅-Kandidaten 5 Finalisten auswählen.
- Bewertung anhand des Rasters oben.

### 2. Tiefer Verfügbarkeits-Check pro Finalist
- [ ] `whois` final bestätigen (`.com`, `.dev`, `.io`, `.app`, `.ai`)
- [ ] GitHub-Org-Name reservierbar
- [ ] npm-Scope frei (`npm view @<name>`) – Quick-Check oben war auf Paketname; vor Reservierung Scope-Check nachziehen
- [ ] PyPI-Name verfügbar
- [ ] Social Handles (X, LinkedIn, Mastodon, Bluesky)
- [ ] Google + App Stores nach Vorbenutzung absuchen

### 3. Markenrecherche für Finalisten
- [ ] DPMA: `register.dpma.de/DPMAregister/marke/einsteiger`
- [ ] EUIPO eSearch plus: `euipo.europa.eu/eSearch`
- [ ] USPTO: `tmsearch.uspto.gov`
- [ ] WIPO Global Brand Database: `branddb.wipo.int`
- [ ] Handelsregister
- [ ] Quick-Check, ob Begriff generisch/beschreibend wirkt (Eintragungsfähigkeit)

### 4. Entscheidung
- Finalisten gegeneinander stellen, mit Team durchsprechen.
- Einen primären Namen + einen Fallback wählen.

### 5. Sichern (Bündel)
- [ ] `.com` + `.dev` + `.io` Domains kaufen
- [ ] GitHub-Org anlegen
- [ ] npm-Scope reservieren
- [ ] Social Handles reservieren
- [ ] Optional: EU-Wortmarke beim EUIPO anmelden (ab 850 €/Klasse), idealerweise nach kurzer Anwalts-Sichtprüfung

### 6. Migration im Projekt
- [ ] `flowcation-plan.md` umbenennen + Inhalt anpassen (Vision-Satz, IDs `flow://…`, Beispielbefehle, Spec-Format)
- [ ] Repo / GitHub-Org umziehen
- [ ] `flowcation.com` weiter halten als 301-Redirect / oder verkaufen
- [ ] Schema-IDs und CLI-Name (`flowcation` → neu) im Spec-Schema v0 anpassen, **bevor** v0 öffentlich publiziert wird (Phase 0 noch nicht abgeschlossen → günstiger Zeitpunkt)
- [ ] `Vorarbeiten`-Block im Produkt-Plan aktualisieren

---

## Risiken / offene Punkte

- **Generische Begriffe** (`canonspec`, `forgepkg`, `unboundspec`) können bei DPMA/EUIPO Probleme mit Eintragungsfähigkeit haben → eher Wort-/Bildmarke als reine Wortmarke.
- **„npm" / „pkg" im Namen**: rechtlich keine direkte Verletzung, aber Verwechslungs-/Beschreibungsrisiko prüfen (`forgepkg` ist hier weniger problematisch als `specnpm`, weil `pkg` eine generische Abkürzung ist).
- **CLI-/Schema-Namen** sollten **vor** Phase-0-Veröffentlichung final sein, sonst Breaking Changes für frühe Tester.
- **Kein Anwalt = kein Freibrief**: Vor Markenanmeldung Sichtprüfung durch Fachanwalt für gewerblichen Rechtsschutz (300–800 €) – billiger als ein zweites Rebranding.
- **Lehre aus SpecMesh-/SpecForge-Check (2026-05-05)**: Vor jeder Markenrecherche zuerst `whois` aller relevanten TLDs **plus** GitHub-Org-Namen, npm-Paket und vorhandene OSS-Projekte (Google, GitHub Search) prüfen. Aktive Vorbenutzung in der Dev-Tooling-Nische schließt Kandidaten oft schneller aus als das Markenregister.

---

## Disclaimer

Strukturierte Einschätzung, keine Rechtsberatung. Domain-/GitHub-/npm-Verfügbarkeit zum Zeitpunkt der Prüfung (2026-05-05); Markenrecht muss separat geprüft werden, idealerweise vor dem Kauf der Domain bzw. der öffentlichen Nutzung.
