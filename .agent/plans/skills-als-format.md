---
lifecycle: active
status: Entwurf 2026-08-07 — Playbooks werden Agent Skills (SKILL.md als Speicherformat); S0 (Refinement mit BO) offen, danach S1
sessionId: skills-als-format
---
# Plan: Skills als Format — Speccify wird die Lieferkette für Agentenwissen

> **Status**: 📋 Entwurf, wartet auf Refinement (2026-08-07)
> **Ersetzt**: [`archive/neuausrichtung-workflow-playbooks.md`](./archive/neuausrichtung-workflow-playbooks.md) (W1–W5 geliefert, veröffentlicht)
> **Auslöser (BO, 2026-08-07)**: „Warum machen wir die Playbooks nicht selbst in einem Skill-artigen Format in Markdown? […] Noch gibt es keine User und Skills sind ja wirklich sehr nützlich."

---

## In einem Satz

Ein Playbook **ist** ein Agent Skill — dieselbe Datei, dasselbe Verzeichnis, kein
Export. Was Speccify hinzufügt, ist alles, was der Skills-Spec offenlässt:
Herkunft, Version, Frische, Komposition und eine Oberfläche für Menschen.

## Die Namensfrage (BO-Entscheid, 2026-08-07)

> **Ein Playbook ist ein Skill, der andere Skills referenziert.**

Damit ist die Beziehung klar und kostenlos:

* **Skill** = die Einheit. Verzeichnis mit `SKILL.md`. Das ist das Speicherformat.
* **Playbook** = ein Skill mit `uses` — ein zusammengesetzter Workflow.

Es gibt keine zwei Formate und keinen Export zwischen ihnen. Ohne Speccify sieht
man einen Skill, der andere erwähnt; mit Speccify löst sich die Referenz auf,
wird gepinnt und geholt. Der Produktname bleibt Speccify, das Wort „Playbook"
bleibt für die zusammengesetzte Form.

## Warum das die stärkere Richtung ist

Der bisherige Bau hatte eine Schwäche, die sich nicht wegarbeiten ließ: Er war
**erst nach Installation nützlich**. Ein Playbook ohne laufenden MCP-Server ist
eine YAML-Datei, die niemand liest. Ein Skill dagegen wird von Claude Code
automatisch gefunden und ausgelöst, sobald er im Verzeichnis liegt.

Drei Funde aus der Spezifikation ([agentskills.io/specification](https://agentskills.io/specification),
gelesen 2026-08-07) machen den Wechsel billig:

1. **Herstellerneutral.** Der Spec ist aus Anthropics Doku ausgezogen, liegt
   unter `github.com/agentskills/agentskills` und hat eine Referenz-Validierung
   (`skills-ref validate`). Das ist etwas anderes als das Format eines Anbieters.
2. **`metadata` ist die offizielle Hintertür.** *„Arbitrary key-value mapping…
   Clients can use this to store additional properties not defined by the Agent
   Skills spec."* Ihr eigenes Beispiel legt dort `version: "1.0"` ab. Wir müssen
   nichts dehnen.
3. **Der Body hat keine Formatvorgaben.** *„Write whatever helps agents perform
   the task effectively."*

Dazu zwei offizielle Felder, die wir ohnehin brauchten: `license` und
`compatibility` (letzteres ist fast wörtlich unser `requires`).

## Format-Entwurf

Eine Datei. Gültiger Skill. Vollständig von uns parsebar.

```markdown
---
name: macos-notarize-tauri
description: Signs and notarizes a Tauri 2 app so it opens on a stranger's Mac
  without a Gatekeeper warning. Use when shipping a macOS app outside the App
  Store, or when the user mentions notarization, codesign, Gatekeeper, stapling.
license: MIT
compatibility: Requires Xcode command line tools and an Apple Developer Program membership
metadata:
  speccify.version: "1.0.0"
  speccify.stack: tauri
  speccify.platforms: macos
  speccify.uses: "@speccify/apple-developer-id-cert@^1.0"
---

## 1 — Turn on the hardened runtime

Notarization rejects anything without it. In `src-tauri/tauri.conf.json`: …

**Verify:** `codesign -d --entitlements -` shows the runtime flag.

## Pitfalls

- Unsigned sidecars pass the build and fail notarization.

## Sources

- [Notarizing macOS software](https://developer.apple.com/…) — retrieved 2026-08-06
```

**Abbildung der bisherigen Felder:**

| bisher (`playbook.yaml`) | jetzt |
|---|---|
| `id` | `name` + `metadata.speccify.scope` |
| `title` | H1 bzw. Verzeichnisname |
| `summary` + `applies_to.keywords` | `description` (was **und** wann) |
| `version` | `metadata.speccify.version` |
| `applies_to.platforms` / `.stack` | `metadata.speccify.platforms` / `.stack` |
| `applies_to.requires` | `compatibility` |
| `steps[]` mit `detail` | `## N — Titel` + Fließtext |
| `steps[].verify` | `**Verify:** …` im Schritt |
| `steps[].uses` | `metadata.speccify.uses` (+ Erwähnung im Text) |
| `pitfalls` | `## Pitfalls` |
| `sources[]` mit `retrieved` | `## Sources`, Konvention `— retrieved YYYY-MM-DD` |
| `assets/` | `assets/` (Spec-Konvention, unverändert) |

**Zwei bewusste Entscheidungen dabei:**

* **Quellen bleiben im Body**, nicht in einem Beiwagen. Dort nützen sie dem
  Agenten, und die Konvention `— retrieved <ISO>` ist trivial zu parsen. Der
  Skills-Spec rät zwar von „zeitabhängigen Informationen" ab — gemeint sind
  Anweisungen, die verfallen („vor August 2025 nutze X"), nicht die Herkunft
  einer Aussage.
* **`metadata` erlaubt nur String→String.** Deshalb flache Schlüssel mit
  Präfix (`speccify.stack`), wie der Spec es für Kollisionsfreiheit empfiehlt.
  Nichts Verschachteltes.

## Was Speccify draufsetzt — die eigentliche Wette

Der Spec lässt sechs Dinge offen. Alle sechs sind bei uns entweder fertig oder
billig:

| Lücke im Spec | Was wir haben |
|---|---|
| **Frische** — Empfehlung ist „vermeide zeitabhängige Infos" | `retrieved`-Daten, `check --links`, Soft-404-Erkennung. Fertig. |
| **Version/Pinning** — `metadata.version` löst niemand auf | Bundle-Hash, Commit-Pin, Lockfile, MVS-Resolver. Fertig, formatunabhängig. |
| **Komposition** — kein Abhängigkeitsmechanismus | `uses` + Resolver. Fertig. |
| **Herkunft** — nichts darüber, woher ein Skill kommt | Git-Quellen, Index-Repos, `search`. Fertig. |
| **Lint gegen die Best-Practice-Checkliste** — `skills-ref` prüft nur Frontmatter | Neu, klein: Beschreibung in dritter Person mit *was und wann*, Body < 500 Zeilen, Verweise eine Ebene tief, keine Windows-Pfade, Name = Verzeichnisname. |
| **Token-Budget** — Metadaten aller Skills liegen dauerhaft im Kontext | Neu, klein: „deine 40 Skills kosten 4k Token beim Start; diese 6 Beschreibungen sind zu lang". |

Die letzten beiden sind der Hebel: Sie sind **sofort nützlich für jemanden, der
noch nie von Playbooks gehört hat, aber zwölf Skills herumliegen hat.**

## Phasen

Jede Stufe endet mit etwas Benutzbarem — der BO prüft daran, ob er es selbst
benutzen würde, bevor die nächste beginnt.

### S1 — Format und Kern
Parser für `SKILL.md` (Frontmatter + Body-Konventionen), Validierung gegen den
Spec plus unsere Zusätze, die zehn Playbooks konvertiert. `lint` und `check`
laufen darauf. Alles, was auf Verzeichnissen arbeitet — Bundle-Hash, Lockfile,
Git-Quellen, Resolver, Index — bleibt unangetastet.
**Benutzbar danach:** Die zehn Playbooks liegen als echte Skills vor und
funktionieren in Claude Code, ohne dass irgendetwas von Speccify läuft.

### S2 — Vorhandene Skills lesen
`speccify` findet `.claude/skills/` und `~/.claude/skills/`, liest sie ohne
Konvertierung, prüft sie (`check`, Best-Practice-Lint, Token-Budget).
**Benutzbar danach:** Das Werkzeug sagt dir etwas über Skills, die du schon
hast — ohne dass du irgendetwas übernehmen musst.

### S3 — Viewer als Skills-Manager
Der Viewer zeigt, was im Projekt und global installiert ist: Beschreibung,
Alter der Quellen, Lint-Befunde, Token-Kosten, gebündelte Skripte (die
Audit-Frage aus dem Sicherheitsteil des Spec). Kompositionsbaum für Playbooks.
**Benutzbar danach:** Eine Oberfläche für etwas, das man heute nur im Editor
liest.

### S4 — In ein Repo geben und kombinieren
Aus vorhandenen Skills ein Repo machen: versionieren, taggen, pinnen. Skills zu
Playbooks zusammensetzen (`uses` schreiben, Kind auflösen).
**Benutzbar danach:** Der Weg von „ein paar Skills im Homeverzeichnis" zu
„etwas, das ich teilen und wiederfinden kann".

### S5 — Doku, Website, Ökosystem
Erzählung neu: Speccify ist die Lieferkette für Agentenwissen. Doku-Seiten,
Landing-Page, `docs/launch.md`. Index säen.

## Entscheidungsvorschläge (bitte bestätigen oder korrigieren)

* **D1 — `SKILL.md` ersetzt `playbook.yaml` vollständig**, kein Parallelbetrieb
  und keine Migrationsschicht. *Alternative*: beides lesen — kostet dauerhaft
  zwei Parser für null Nutzen bei null Nutzern. **Empfehlung: ersetzen.**
* **D2 — Quellen im Body**, Konvention `— retrieved <ISO>`, nicht in einem
  Beiwagen-File. **Empfehlung: ja** (siehe oben).
* **D3 — Verzeichnis-Layout folgt dem Spec**: `scripts/`, `references/`,
  `assets/`. Unser bisheriges `assets/` passt schon.
* **D4 — Scope im Namen.** Skill-`name` darf nur `[a-z0-9-]` — `@speccify/x`
  geht nicht. Vorschlag: `name: macos-notarize-tauri`, Scope in
  `metadata.speccify.scope`. Die Id für Lockfile und `uses` bleibt
  `@scope/name`.
* **D5 — `skills-ref` als Abhängigkeit oder nachbauen?** Es ist die
  Referenz-Validierung des Spec. **Empfehlung: erst nachsehen, was es prüft** —
  wenn es taugt, aufrufen statt nachbauen.
* **D6 — Der Viewer liest auch nicht-Speccify-Skills** (S2), ohne sie zu
  verändern. Das ist der Einstieg für neue Nutzer. **Empfehlung: ja.**

## Offene Fragen an den BO

1. **Bleibt `speccify` der CLI-Name?** Er passt weiterhin, aber wenn das Produkt
   „das Werkzeug für Skills" wird, wäre etwas Sprechenderes denkbar. Ein
   Umbenennen wird nach den ersten Nutzern teuer.
2. **Wie weit soll S2 gehen?** Nur lesen und prüfen — oder auch reparieren
   („Beschreibung ist zu lang, hier ein Vorschlag")? Letzteres ist die Brücke
   zum Vorschlags-Mechanismus, den der Viewer schon hat.
3. **Was passiert mit dem gerade veröffentlichten Release v0.2.0?** Der Entwurf
   ist noch nicht publiziert. Ihn liegen lassen, bis S1 durch ist, oder jetzt
   veröffentlichen und später ersetzen?

## Risiken

* **Dritte Neuausrichtung in einer Woche.** Vom BO ausdrücklich als
  unproblematisch eingestuft, solange es keine Nutzer gibt. Bleibt trotzdem
  wahr: Irgendwann muss man sich festlegen und liefern.
* **Abhängigkeit von einem fremden Spec.** Gemildert dadurch, dass er
  herstellerneutral ist, eine Referenz-Implementierung hat und wir nur das
  offiziell vorgesehene `metadata` benutzen. Ändert sich der Spec, ändern wir
  den Parser — nicht die Inhalte.
* **Die Website ist seit heute live** und beschreibt `playbook.yaml`. Sie wird
  ein zweites Mal umgeschrieben (S5). Kosten: ein Tag, kein Risiko.
* **Der Inhalt überlebt jeden Formatwechsel.** Die zehn Playbooks sind der
  wertvolle Teil; ihre Konvertierung ist mechanisch. Das ist das Argument
  dafür, Inhalt und Format weiterhin trennbar zu halten — auch für den
  nächsten Kurswechsel.
