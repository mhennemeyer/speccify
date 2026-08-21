---
lifecycle: active
status: Bauen — T1 und T2 geliefert 2026-08-21; nächstes Ziel T3 (Evaluate — `speccify tool check`, Spur).
sessionId: skills-und-tools
---
# Plan: Speccify als Skill- und Tool-Manager

> **Status**: 📋 Definition (2026-08-20, BO-Entscheide 2026-08-21).
> **Ersetzt**: [`archive/skills-als-format.md`](./archive/skills-als-format.md)
> — die Produktdefinition dort (ein Nutzer, drei Orte, Workflows W-A bis W-H,
> Nicht-Ziele, D1–D6) **gilt weiter** und wird hier nicht wiederholt.
> **Auslöser (BO, 2026-08-20)**: Nach M1 stünde der Neubau eines alten
> Projekts an. Vorher soll Speccify um das erweitert werden, was sich beim
> Teilen von Skills als eigentliche Hürde gezeigt hat: **fertig programmierte
> Tools wandern nicht** — Python-Version, macOS/Linux gegen Windows, Pfade.
> Skills sollen deshalb Tools nicht mitliefern, sondern **spezifizieren**.

---

## Die Idee in einem Satz

Ein Skill beschreibt, *was* zu tun ist; ein **Tool-Spec** beschreibt genau,
*was ein Werkzeug können muss* — und der Agent programmiert es **vor Ort**
aus, in der Sprache, die auf dieser Maschine läuft. Geteilt wird der Vertrag,
nicht die Implementierung.

Das ist dieselbe Bewegung wie beim Pivot von Playbooks zu Skills: Speccify
liefert kein Format und keinen Code, sondern **Organisation, Lookup,
Kombination** — jetzt um eine Ebene nach unten verlängert, bis zum Werkzeug.

## Warum Specs statt Skripte

| Geteilt wird … | Bricht an … | Behebt … |
|---|---|---|
| ein `.sh`/`.py` in `scripts/` (heute) | Python-Version, Shell, Pfadtrenner, fehlende Binaries | niemand — der Empfänger patcht eine fremde Datei |
| ein **Tool-Spec** | nichts davon — es ist Text | der Agent, der es passend zur Plattform schreibt |

Nebeneffekt: Der Spec zwingt zur Präzision (Eingaben, Ausgaben, Seiteneffekte,
Beispiele), die im fertigen Skript implizit bleibt. Ein Skript sagt *wie*, ein
Spec sagt *was* — und *was* altert langsamer.

Die bestehenden `scripts/`-Dateien werden **nicht verboten**. Sie bleiben als
Referenzimplementierung für eine Plattform erlaubt; der Spec ist die Wahrheit.

---

## Zwei Welten: Quelle und Projekt

Der Kern der BO-Entscheide vom 2026-08-21. Es gibt zwei klar getrennte
Formen eines Skills:

| | **In der Quelle** (ein Skills-Repo) | **Im Projekt** (`.agent/`) |
|---|---|---|
| Form | `SKILL.md` + `metadata.speccify.*` + `tools/*/TOOL.md` | **ganz normale Skills** — Markdown, wie es auch unter `.claude/skills/` aussähe |
| Referenzen | `speccify.uses` zeigt auf andere Skills | **aufgelöst**: jeder referenzierte Skill ist ein eigener normaler Skill daneben |
| Tools | Spec | **ausprogrammiert**, pro Plattform eine Variante |
| Platzhalter | generisch | konkret für dieses Projekt |
| Git | im Quell-Repo | **committet** im Projekt-Repo |

**Expand ist der Übergang von links nach rechts.** Sonst nichts. Das Ergebnis
braucht Speccify nicht mehr, um zu funktionieren — das war schon die
Leitlinie von M1 und gilt jetzt für den expandierten Zustand erst recht.

## `.agent/` ist das Zuhause (BO, 2026-08-21)

Skills, Tools und alles Weitere leben **agentneutral unter `.agent/`**. Die
agentspezifischen Dot-Ordner (`.claude/`, später `.cursor/`, …) **verweisen
nur dorthin**. `.agent/` wird committet.

```text
.agent/
  skills/
    macos-notarize-tauri/
      SKILL.md                 ← normal; projektspezifisch ergänzt
    storekit-sandbox-testing/  ← war ein `uses`-Verweis; jetzt ein eigener Skill
      SKILL.md
  tools/
    verify-signatures/
      TOOL.md                  ← der Spec (Kopie, damit der Vertrag vor Ort liegt)
      macos.sh                 ← Implementierung für diese Plattform
      windows.ps1              ← Implementierung für die andere — beide committet
  speccify/
    expansions.yaml            ← Herkunft: Upstream-Id, Version, Hash, Datum,
                               ←   Plattformen, Tool-Status je Tool
  plans/ status.md log.md      ← gibt es schon (der Ablauf, siehe Vorplan)

.claude/skills  →  ../.agent/skills   (Symlink; Speccify legt ihn an)
```

Drei Folgen:

1. **`pull` zielt nicht mehr auf `.claude/skills/`.** Es holt den
   Upstream-Stand in einen Cache (`.agent/speccify/cache/`, gitignored);
   `expand` macht daraus die normalen Skills unter `.agent/skills/`. Die
   Unterscheidung pristin/expandiert aus dem ersten Entwurf **entfällt** —
   unter `.agent/skills/` ist alles expandiert und alles committet.
2. **Herkunft liegt nicht im Skill**, sondern in `expansions.yaml`. So bleibt
   der Skill normal (kein `speccify.*`-Ballast, der im Projekt nichts mehr
   bedeutet), und Speccify weiß trotzdem, woher er kam und ob Upstream
   weitergezogen ist.
3. **Tools sind projektweit**, nicht pro Skill — zwei expandierte Skills, die
   dasselbe Tool brauchen, teilen eine Implementierung. Daher `.agent/tools/`
   auf derselben Ebene wie `.agent/skills/`; der Skill-Body verweist relativ
   (`../../tools/verify-signatures/`).

Der Symlink ist zu prüfen (T2, erster Schritt): findet Claude Code Skills
hinter `.claude/skills → ../.agent/skills`? Falls nicht: `speccify link`
kopiert statt zu verlinken und `verify` meldet Abweichungen.

---

## Das Tool-Spec-Format

### Ort in der Quelle

Ein Tool gehört zu einem Skill und liegt **in dessen Verzeichnis**:

```text
skills/macos-notarize-tauri/
  SKILL.md
  tools/
    verify-signatures/
      TOOL.md          ← der Spec
      reference.sh     ← optional: Referenzimplementierung (eine Plattform)
  scripts/             ← bleibt erlaubt (Spec, nicht Verzeichnis, ist der Vertrag)
```

Kein neuer Top-Level-Begriff: Ein Skill, der nur Tools definiert und dessen
Body sagt „dieser Skill stellt X und Y bereit", ist ein normaler Skill. Andere
Skills erreichen seine Tools über den bestehenden Mechanismus `speccify.uses`.

### `TOOL.md`

Frontmatter analog zu `SKILL.md`, Body frei, Struktur wird **inferiert**
(dieselbe Haltung wie in `skill.py`: was nicht erkennbar ist, fehlt, es ist
kein Fehler). Inputs/Outputs als **JSON Schema** (BO-Entscheid 2, 2026-08-21):
maschinell prüfbar, und Agenten kennen es von Tool-Calls ohnehin.

```markdown
---
name: verify-signatures
description: Checks that every Mach-O in an .app bundle is signed with the
  expected identity and the hardened runtime; reports the first offender.
inputs:                 # JSON Schema, bewusst klein
  type: object
  required: [bundle]
  properties:
    bundle:   { type: string, description: "Path to the .app" }
    identity: { type: string }
outputs:
  type: object
  required: [ok]
  properties:
    ok:        { type: boolean }
    offenders: { type: array, items: { type: string } }
effects: reads filesystem; runs `codesign`; writes nothing
requires: codesign            # Binaries/Dienste, die vor Ort da sein müssen
runtime: any                  # oder: python>=3.11 | node>=22 | bash | powershell
platforms: macos              # wo das Tool überhaupt Sinn ergibt; fehlt = überall
---

## Behaviour
…Prosa: was das Tool tut, Randfälle, was es nie tun darf…

## Examples
### signed bundle
input:  {"bundle": "fixtures/Signed.app", "identity": "Developer ID Application: …"}
output: {"ok": true, "offenders": []}
### one unsigned helper
input:  {"bundle": "fixtures/Broken.app"}
output: {"ok": false, "offenders": ["Contents/MacOS/helper"]}
```

**Die Beispiele sind der wichtigste Teil.** Sie sind das, woran *Evaluate*
später prüft, ob die vor Ort geschriebene Implementierung den Vertrag erfüllt.
Ein Tool-Spec ohne Beispiele ist ein `check`-Befund, kein Fehler.

### Aufrufkonvention (D7)

Jede ausprogrammierte Implementierung ist ein **Executable, das JSON auf stdin
nimmt und JSON auf stdout gibt**, Exit-Code 0 = `ok`, ≠ 0 = Fehler mit
Meldung auf stderr. Sprache beliebig. Damit ist die Konformitätsprüfung
sprachunabhängig: `speccify tool check` füttert die Beispiele ein und
vergleicht. Der Agent ruft das Tool danach so auf, wie er jedes andere
Kommando im Terminal aufruft — es braucht keinen Vermittler.

Das ist die eine Stelle, an der Speccify *eine* Form vorschreibt — bewusst,
weil ohne sie nichts automatisch prüfbar ist.

---

## Der Dreischritt: Expand → Execute → Evaluate

Ein Skill aus dem Repo durchläuft im Projekt drei Phasen, ggf. iterativ.

### 1 — Expand: normalisieren und anpassen

Aus dem Quell-Skill werden **ein oder mehrere normale Skills** unter
`.agent/skills/`:

* **Referenzen auflösen**: jeder per `speccify.uses` verwiesene Skill wird
  selbst expandiert und liegt als eigener Skill daneben. Der Verweis im Body
  wird zu einem normalen relativen Link.
* **Metadaten abstreifen**: `speccify.*` verschwindet aus dem Frontmatter;
  die Herkunft wandert nach `expansions.yaml`.
* **Platzhalter konkret machen** (Bundle-Id, Pfade, Identitäten, Port) und
  Projektspezifisches **ergänzen** — als eigener Abschnitt (`## In this
  project`), der Upstream-Body bleibt unberührt (BO-Entscheid 3, 2026-08-21:
  erst einmal nur ergänzen; Umschreiben später, falls M2 es verlangt. Keine
  Grundsatzfrage — der Nachweis kennt den Upstream-Hash, ein späterer Wechsel
  macht aus Re-Expand einen Merge, mehr nicht).
* **Tools ausprogrammieren** nach `.agent/tools/<name>/`, für **diese**
  Plattform; weitere Plattformen kommen hinzu, wenn jemand dort expandiert,
  und werden **beide committet**. `platforms` im Spec sagt, wo ein Tool
  überhaupt erwartet wird.

Wer das tut: **der Agent.** Was Speccify tut: `speccify expand <skill>`
rechnet den Abhängigkeitsbaum aus, legt Verzeichnisse und `TOOL.md`-Kopien an,
streift Metadaten ab, schreibt den Nachweis und gibt dem Agenten die
Aufgabenliste: „2 Skills normalisiert, 3 Tools für macos zu implementieren,
2 Platzhalter zu füllen".

### 2 — Execute: ausführen

Der Agent folgt dem expandierten Skill und ruft die Tools auf. Nichts Neues in
Speccify — außer einer **Spur**: welcher Skill, welche Iteration, wann
(schließt an W-H.5 an: „Was hat er angerichtet?").

### 3 — Evaluate: eingebaute Mini-QA

Der Agent **versucht Fehler zu finden**. Zwei Schichten:

* **Mechanisch** — `speccify tool check` führt die Beispiele jedes Tool-Specs
  gegen die Implementierung dieser Plattform aus. Grün oder rot, ohne Urteil.
* **Fachlich** — der Agent prüft das *Ergebnis des Skills* gegen dessen
  `**Verify:**`-Zeilen (gibt es heute schon in jedem Schritt) und gegen die
  Akzeptanzkriterien. Er sucht aktiv nach Gegenbeweisen. Findet er keine:
  fertig. Findet er welche: **neue Iteration**, zurück zu Expand oder Execute,
  je nachdem ob Anpassung oder Ausführung schuld war.

Der Befund wandert in den Nachweis (`verified` mit Datum und Plattform) und in
die Spur. Was sich dabei als *generelle* Erkenntnis erweist, geht als
Korrektur zurück ins Quell-Repo (W-B, existiert).

### Wer den Dreischritt trägt

Nicht Code. **Der mitgelieferte Speccify-Skill** (D6 aus dem Vorplan) wird
um die drei Phasen erweitert — er löst aus, sobald der Agent einen Skill
benutzen will, und führt ihn durch Expand/Execute/Evaluate. Damit gilt
weiter: der Ablauf ist Daten, forkbar, anpassbar. Speccify liefert die
Befehle und Prüfungen, nicht die Choreografie.

---

## Was das für das Team-Problem heißt

Das Nicht-Ziel „kein Team" aus dem Vorplan **bleibt**. Tool-Specs lösen das
Teilen trotzdem — ohne Rechte, Review oder Organisation: Was geteilt wird, ist
plattformneutraler Text. Wer anders arbeitet (Windows, anderes Python),
expandiert das Tool auf seiner Maschine, committet die Variante — und ab dann
hat das Projekt beide. Das ist die billigste Form von Team-Support: die, die
keine Team-Features braucht.

## Was mit dem Exec-MCP ist (BO, 2026-08-21)

Nichts. Der Exec-MCP existiert für **gesandboxte Clients** (App-Store-App),
die selbst keine Prozesse starten dürfen. Der Normalfall hier ist ein Agent im
Terminal mit vollem Zugriff — er ruft ein expandiertes Tool direkt auf. Eine
Anbindung wäre nur dann ein Thema, wenn die Desktop-App einmal selbst Tools
ausführen soll; das ist kein Ziel dieses Plans.

---

## Meilensteine

### T1 — Tool-Spec-Format ✅ (2026-08-21)

**Geliefert:** `tool.py` (Parser, JSON-Schema-Validierung, Beispiele gegen
Schemas), `check`/`lint` mit Tool-Befunden (kein Spec → Warnung je Skript,
keine Beispiele, kein `effects`, Verzeichnis ≠ Name), drei Specs im Repo
(`verify-signatures`, `verify-stream`, `build-libgit2`; Skripte als
`reference.sh`), `show`/`skill_get` mit flacher Tool-Liste, MCP `tool_get`,
Viewer mit Tools-Abschnitt, Git-Quellen holen `tools/` mit.
**Abweichung vom Plan:** Fastlane war kein Kandidat (Konfiguration, kein
Werkzeug); stattdessen `build-libgit2`, weil der Hinweis „Skript ohne Spec"
es sonst angemeckert hätte — Dogfooding hat die Wahl getroffen.

**Fertig heißt:** `TOOL.md` lesen, schreiben, prüfen; zwei vorhandene Skripte
sind zu Specs geworden.

1. `tool.py` neben `skill.py`: Parser, Modell, `validate_tool` (Name nach
   Spec-Regel, `inputs`/`outputs` sind gültiges JSON Schema, Beispiele
   validieren gegen die Schemas, `requires`/`runtime`/`platforms` sind Listen
   wie gehabt).
2. `skill.py` kennt `tools/` als weiteres Verzeichnis; `Skill.tools`.
3. `speccify check` und `lint`: Tool-Befunde (ohne Beispiele, ohne
   `effects`, Beispiel verletzt Schema, `scripts/` ohne zugehörigen Spec als
   Hinweis).
4. Dogfooding: `verify-signatures.sh` (macos-notarize-tauri) und ein zweites
   (Kandidat: das Fastlane-Bündel oder etwas aus `mcp-client-streamable-http`)
   werden zu Specs; die Skripte bleiben als `reference.*`.
5. MCP: `skill_get` liefert Tools mit; `tool_get` einzeln. Viewer zeigt Tools
   als Abschnitt — klein, nur Lesen.

### T2 — Expand ✅ (2026-08-21)

**Geliefert:** Symlink-Probe positiv (Claude Code listet die Skills hinter
`.claude/skills → ../.agent/skills` sofort). `expansion.py` (reine
Normalisierung + `expansions.yaml`), `speccify expand` (uses-Baum, Metadaten
abgestreift, `## In this project` bleibt bei Re-Expand, Tools projektweit,
Implementierungen `<platform>.<ext>` werden nie überschrieben), `speccify link`,
`init` legt Ignore-Zeile und Link an, `pull` zielt auf den Cache, `verify`
meldet Upstream-Drift gegen die Expansion und Tool-Status je Plattform, MCP
`expand` (12 Tools). Der **Speccify-Skill** (`skills/speccify`) beschreibt
alle drei Phasen. Dogfooding: dieses Repo hat `speccify.yaml` mit elf Skills,
`.agent/skills/` (expandiert, committet), `.agent/tools/` mit drei Specs ohne
Implementierung, `.claude/skills` als Symlink im Git.
**Entscheid zur offenen Frage 2:** Implementierungsdatei = `<platform>.<ext>`
(`macos.sh`, `windows.ps1`, `linux.py`); Stamm ist die Plattform, Endung frei.
**Gelernt:** Ein Skill in `.agent/skills/` darf auf Geschwister und
`../../tools/` verweisen — `check` erkennt die Projektform am Pfad und meldet
das nicht; außerhalb bleibt es ein Fehler (der Link würde nicht reisen).
Placeholder-Heuristik: `<wort>` ohne schließendes `</wort>`, plus `YOUR_*`/`TODO`.

**Fertig heißt:** `speccify expand <skill>` erzeugt normale Skills unter
`.agent/skills/`, Tool-Gerüste unter `.agent/tools/`, den Nachweis; Claude
Code findet die Skills über `.claude/skills`; `verify` kennt Upstream-Drift.

1. **Symlink-Probe** `.claude/skills → ../.agent/skills` in Claude Code.
   Ergebnis entscheidet über Link oder Kopie in `speccify link`.
2. `pull` zielt auf den Cache `.agent/speccify/cache/` (gitignored);
   `speccify init` schreibt die `.gitignore`-Zeile und den Link.
3. Nachweis `expansions.yaml` (Schema in `core/src/speccify_core/schemas/`).
4. `speccify expand`: `uses`-Baum auflösen, Metadaten abstreifen, Verweise
   zu relativen Links machen, `## In this project` anlegen, `TOOL.md` nach
   `.agent/tools/<name>/` kopieren, Nachweis schreiben, Aufgabenliste.
5. `verify`: Upstream neuer als Expansion (Re-Expand empfohlen); Tools ohne
   Implementierung für diese Plattform; Tools `implemented`, nicht `verified`.
6. Dogfooding in **diesem** Repo: die zehn Skills liegen heute materialisiert
   unter `.claude/skills/` — sie ziehen nach `.agent/skills/` um.
7. Der Speccify-Skill bekommt die Expand-Anleitung.

### T3 — Evaluate

**Fertig heißt:** `speccify tool check` läuft die Beispiele gegen die
Implementierung dieser Plattform; der Dreischritt ist im Speccify-Skill
vollständig beschrieben; die Spur hat eine Form.

1. Konformitätsläufer nach D7 (stdin/stdout-JSON, Exit-Code, Timeout,
   Vergleich mit Toleranz für Zusatzfelder, Plattformwahl automatisch).
2. Status-Übergang `implemented → verified` je Plattform im Nachweis.
3. Spur: ein Eintragsformat für `log.md` (Skill, Version, Iteration, Befund)
   — Konvention im Speccify-Skill, kein Code.
4. Speccify-Skill: Execute- und Evaluate-Anleitung samt Iterationsregel
   („Gegenbeweise suchen; keine gefunden ⇒ fertig; gefunden ⇒ zurück zu …").

### M2 — Der Testlauf (unverändert, jetzt mit Dreischritt)

Ein altes Projekt mit Skills und Speccify neu bauen — **jeder Skill durchläuft
Expand/Execute/Evaluate.** Das ist die Evaluation von T1–T3 *und* von M1.
Erst danach: Ablauf-Frage (geparkt seit 2026-08-13), Außendarstellung (die
noch Playbooks erzählt), S2–S5 aus dem Vorplan.

**Reihenfolge-Entscheid:** T1 → T2 → T3 → M2. T1 ist klein und allein schon
nützlich (Specs sind bessere Doku als Skripte). Würde M2 ohne T2 anfangen,
gäbe es keinen Ort für expandierte Skills — `.claude/skills/` ist heute
wegwerfbar.

## Entscheidungen

* **D7 — Aufrufkonvention**: stdin-JSON → stdout-JSON, Exit-Code. Einzige
  Form, die Speccify vorschreibt; Sprache frei.
* **D8 — `.agent/` ist das Zuhause und wird committet** (BO 2026-08-21).
  `.agent/skills/` enthält nur normale, expandierte Skills; `.agent/tools/`
  die Implementierungen, je Plattform eine, alle committet. Agent-Dot-Ordner
  verweisen nur. Upstream-Cache gitignored.
* **D9 — Tools liegen in der Quelle im Skill** (`tools/<name>/TOOL.md`), kein
  eigener Top-Level-Typ; Wiederverwendung über `speccify.uses`. Im Projekt
  liegen sie projektweit unter `.agent/tools/`.
* **D10 — Beispiele sind der Vertrag.** Ohne Beispiele ist ein Spec
  unvollständig (Befund), Evaluate hat dann nur die fachliche Schicht.
  Inputs/Outputs als JSON Schema (BO 2026-08-21).
* **D11 — Der Dreischritt ist Skill, nicht Code.** Speccify liefert
  `expand`, `tool check`, den Nachweis — die Choreografie steht im
  Speccify-Skill und ist forkbar.
* **D12 — Expand ergänzt, schreibt nicht um** (BO 2026-08-21). Revidierbar
  nach M2 ohne Umbau, weil der Nachweis den Upstream-Hash führt.
* **D13 — Kein Exec-MCP** im Dreischritt (BO 2026-08-21). Der Agent ruft
  Tools direkt auf.

## Offene Fragen

Keine. Die beiden aus T2 sind beantwortet (Symlink: ja; Datei: `<platform>.<ext>`).
