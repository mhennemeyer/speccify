# Plan: Umbenennung von „flowcation"

> **Status**: 📋 Entwurf – Namensfindung & Markenrecherche
> **Erstellt**: 2026-05-05
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

## Auswahlkriterien (Bewertungsraster)

Pro Kandidat in `Top-Auswahl` mit 1–5 bewerten:

| Kriterium | Gewicht |
|---|---|
| Konzept-Fit (Spec / Komposition / Agent / Forge) | ×3 |
| Aussprache & Internationalität | ×2 |
| Einprägsamkeit / Markenpotenzial | ×2 |
| `.com` frei | ×3 |
| GitHub-Org frei | ×2 |
| npm-Scope frei | ×2 |
| Keine offensichtlichen Markenkonflikte (Quick-Check DPMA/EUIPO/USPTO) | ×3 |
| Tippsicher / kurz | ×1 |

---

## Kandidatenliste (Domain `.com` frei, `whois` 2026-05-05)

### 🥇 Top-Empfehlungen

| Name | `.com` | Cluster | Stärke |
|---|---|---|---|
| **forgepkg** | `forgepkg.com` ✅ | Forge / PM | Pragmatisch, nah an `cargo`/`npm`, sofort verständlich für Devs. |
| **specmesh** | `specmesh.dev` ✅ / `specmesh.io` ✅ (`.com` vergeben prüfen) | Spec / Federation | Federation-/Registry-Vibe, modern (Service-Mesh-Anklang). |
| **speconaut** | `speconaut.com` ✅ | Spec / Brand | Eigenständig, einprägsam, Community („Speconauts"). |
| **mosaicspec** | `mosaicspec.com` ✅ | Komposition | Mosaik = Komposition aus Teilen, passt zu `uses:`-Verkettungen. |
| **anvilspec** | `anvilspec.com` ✅ | Forge | Schmiede-Bild, schmiedet Specs in Code. |
| **canonspec** | `canonspec.com` ✅ | Spec / Determinismus | „Kanonische Spezifikation" – Single Source of Truth. |
| **specforge** | `specforge.dev` ✅ (`.com` vergeben) | Forge | Starkes Authoring-Bild, `.dev` etabliert (Deno, Bun, Astro). |
| **specstack** | `specstack.io` ✅ (`.com` prüfen) | Spec / Workspaces | „Stack of Specs", passt zu Workspaces + Multi-Target. |

### 🎯 Erweiterte Auswahl (alle `.com` frei)

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
- `forgepack.io`

#### Spec-zentriert
- `specnpm.com` (Risiko: „npm" ist Marke – nur Domain, nicht Branding)
- `canonspec.com` / `kanonspec.com`
- `specoid.com`
- `speconaut.com` / `specnaut.com` / `specronaut.com`
- `specthos.com`
- `unboundspec.com` – trifft USP („nicht an Framework gebunden") exakt.
- `polytargets.com` – direkt: viele Ziel-Stacks.
- `codeboundspec.com`

#### Agent / MCP
- `agentnpm.com`
- `mcppkg.com` – sehr nischig, aber sprechend.

#### Web/Loom (Spec ↔ Code „weben")
- `weavespec.com`
- `loomspec.com`
- `fabriqspec.com` / `fabriqkit.com`

#### Schräg / Markenfähig
- `sirenspec.com`
- `kompozita.com` / `komponable.com` / `komponize.com`
- `spexel.com` – wie „pixel" für Specs.
- `kosherspec.com` – Augenzwinkern.
- `hexspec.com`
- `tesseraspec.com`

---

## Engerer Kreis: persönlicher Kurzfavorit

1. **forgepkg** (`forgepkg.com`) – pragmatisch, devnah, sofort verständlich.
2. **specmesh** (`specmesh.dev`) – modern, trifft Federation/Registry/Komposition.
3. **speconaut** (`speconaut.com`) – Wildcard mit klarem Markenpotenzial und Community-Branding.

---

## Nächste Schritte

### 1. Engere Auswahl (max. 5) festlegen
- Aus Top-Empfehlungen + erweiterter Liste 5 Finalisten wählen.
- Bewertung anhand des Rasters oben.

### 2. Vollständige Verfügbarkeitsprüfung pro Finalist
- [ ] `whois` final bestätigen (`.com`, `.dev`, `.io`)
- [ ] GitHub-Org-Name verfügbar
- [ ] npm-Scope verfügbar (`npm view @<name>`)
- [ ] PyPI-Namen verfügbar
- [ ] Social Handles (X, LinkedIn, Mastodon, Bluesky)

### 3. Markenrecherche für Finalisten
- [ ] DPMA: `register.dpma.de/DPMAregister/marke/einsteiger`
- [ ] EUIPO eSearch plus: `euipo.europa.eu/eSearch`
- [ ] USPTO TESS: `tmsearch.uspto.gov`
- [ ] WIPO Global Brand Database: `branddb.wipo.int`
- [ ] Google + App Stores + Handelsregister
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

- **Generische Begriffe** (`canonspec`, `specstack`, `forgepkg`) können Markenrecht-Probleme bei Eintragungsfähigkeit haben → eher Wort-/Bildmarke als reine Wortmarke.
- **„npm" / „pkg" im Namen**: rechtlich keine direkte Verletzung, aber Verwechslungs-/Beschreibungsrisiko prüfen.
- **CLI-/Schema-Namen** sollten **vor** Phase-0-Veröffentlichung final sein, sonst Breaking Changes für frühe Tester.
- **Kein Anwalt = kein Freibrief**: Vor Markenanmeldung Sichtprüfung durch Fachanwalt für gewerblichen Rechtsschutz (300–800 €) – billiger als ein zweites Rebranding.

---

## Disclaimer

Strukturierte Einschätzung, keine Rechtsberatung. Domain-Verfügbarkeit zum Zeitpunkt der Prüfung (2026-05-05); Markenrecht muss separat geprüft werden, idealerweise vor dem Kauf der Domain bzw. der öffentlichen Nutzung.
