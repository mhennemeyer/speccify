# Plan: Umbenennung von „flowcation"

> **Status**: 📋 Entwurf – Namensfindung & Markenrecherche
> **Erstellt**: 2026-05-05
> **Update 2026-05-05**: Vollständige Verfügbarkeitsrecherche (Domain `.com/.dev/.io`, GitHub-Org/-User, npm-Registry, aktive Webseite) für alle Kandidaten der vorherigen Liste. Disqualifizierte Namen sind unten dokumentiert. Liste enthält jetzt nur Kandidaten, die diesen Vor-Check bestanden haben.
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

## Engerer Kreis: persönlicher Kurzfavorit

1. **forgepkg** (`forgepkg.com`) – pragmatisch, devnah, sofort verständlich; alle drei Achsen (Domain, GitHub, npm) sauber frei.
2. **mosaicspec** (`mosaicspec.com`) – starkes Bild für Komposition aus Teilen (`uses:`-Verkettungen); sauber frei.
3. **anvilspec** (`anvilspec.com`) – Forge-Bildwelt, prägnant; sauber frei.

`canonspec` und `speconaut` sind weiterhin starke Optionen; `speconaut` mit kleinem Schönheitsfehler (leerer GitHub-User vorhanden, Org-Variante `speconauts` als Plan B).

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
