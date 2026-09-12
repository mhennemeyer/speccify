---
station: Done
created: 2026-05-05
---
# Package-Manager-Vergleich für flowcation

> **Status**: 📋 Entscheidungsvorlage – Input für die Sektion „npm-artiger Workflow konkret" im [flowcation-plan.md](../flowcation-plan.md).
> **Erstellt**: 2026-05-04
> **Zweck**: Vor dem Festschreiben des „npm-artigen" Workflows kurz, fokussiert prüfen, welche Designentscheidungen aus existierenden Package-Managern wir übernehmen, welche wir bewusst nicht übernehmen, und wo flowcation einen Sonderfall darstellt.
> **Timebox**: ½–1 Tag. Keine vollständige Studie, sondern Vergleich entlang von 8 Designachsen.

---

## 1. Warum dieses Dokument

Die teuren Designfehler in Package-Managern sind fast alle früh getroffen worden und hinterher kaum noch korrigierbar:

- **Resolver-Semantik** (npm: nested→flat, links-pad-Drama, Caret-Hell)
- **Lockfile-Format** (npm 5/6/7-Migrationen, yarn-Splits)
- **Identitäts-/Namespace-Modell** (npm-Squatting, fehlende Scopes lange Zeit)
- **Trust-Modell** (Account-Takeover, Malicious Packages)

Sobald die ersten Specs publiziert sind, ist unser Modell de facto eingefroren. Maven hat es früh richtig gemacht (Coordinates, Immutability) – das ist seit 20 Jahren stabil. Aus diesem Reservoir wollen wir bewusst auswählen.

**Sonderfall flowcation**: Unser „Install-Artefakt" ist *generierter Code im Ziel-Stack*, kein Modul-Tree. Das verändert mehrere Annahmen klassischer PMs:

- Kein `node_modules`-Äquivalent, kein Runtime-Linking.
- Statt dessen: `--target`, generierte Dateien im Repo, Lockfile mit Modell-/Prompt-Pin, `flowcation verify` in CI.
- Conformance-Tests statt API-Kompatibilität.

---

## 2. Vergleich entlang der 8 Designachsen

### Achse 1 – Identität / Namespace

| PM | Modell | Stärken | Schwächen |
|---|---|---|---|
| npm | flat + Scopes (`@org/x`) | Kurz, schreibfreundlich | Squatting historisch (Scopes spät eingeführt) |
| Maven | `groupId:artifactId:version` (reverse-DNS) | Kollisionssicher, Namespaces inhärent | Verbose |
| Cargo | flat, reservierte Namen | Einfach | Squatting möglich |
| Go Modules | URL-basiert (`github.com/...`) | Identität = Quelle | Hoster-Abhängigkeit |
| OCI Refs | `registry/repo:tag@digest` | Inhalts-adressiert (digest) | Unbekannt im PM-Kontext |

**Krankheit**: Typosquatting, Namens-Squatting, Verwechslung.

**Entscheidung für flowcation**: Maven-artige *Coordinates* + npm-artige *Scopes* + OCI-artiger *Digest*-Pin im Lockfile.

- Public ID: `@org/login-with-otp@1.4.0` (ergibt `flow://@org/login-with-otp@1.4.0`).
- Reservierte/verifizierte Scopes (à la npm-`@types`, Crates-reserved).
- Lockfile referenziert zusätzlich `sha256:…` des Spec-Bundles (OCI-artig).

---

### Achse 2 – Versionierung

| PM | Modell | Eigenheiten |
|---|---|---|
| npm/Cargo | SemVer + Caret/Tilde | Caret-Default → „silent breaking" |
| Maven | Soft-/Hard-Ranges | Selten genutzt, in Praxis fixe Versionen |
| Go MVS | Minimum Version Selection | Deterministisch, keine Range-Magie |
| pip/PEP 440 | Reicher (pre, post, dev) | Komplex, viele Edge Cases |

**Krankheit**: Caret-Hell, inkompatible Minor-Bumps, Range-Resolver-Explosion.

**Entscheidung**: SemVer pflicht, **kein Caret-Default**. Manifest schreibt exakte oder `>=`-Untergrenze; tatsächliche Auflösung nach **MVS-Prinzip** (siehe Achse 3). Pre-Releases als `1.4.0-rc.1`. Breaking Change in Spec → Major-Bump pflicht (durch Lint erzwingbar).

---

### Achse 3 – Resolver-Strategie

| PM | Strategie | Eigenschaften |
|---|---|---|
| npm | nested (alt) / flat (neu) + Backtracking | Diamond-Konflikte, langsam, nicht-deterministisch ohne Lock |
| pip | Backtracking (resolvelib) | Kann sekundenlang rechnen, instabil bei Konflikten |
| Cargo | SAT-Solver, *eine* Version pro Build | Klar, gelegentlich „kann nicht aufgelöst werden" |
| Go MVS | Minimale Version, die alle Constraints erfüllt | Deterministisch, langweilig, reproduzierbar |

**Krankheit**: Dependency-Hell durch Diamond-Konflikte, nicht-deterministische Resolves zwischen Maschinen.

**Entscheidung**: **Go-MVS-artiger Resolver**. Bei flowcation ist das fast geschenkt:

- Wir haben *Komposition über IDs*, kein Runtime-Linking → keine ABI-Inkompatibilität.
- Mehrere Versionen derselben Spec dürfen koexistieren (anders als Cargo „eine Version pro Build"), weil Output generierter Code in unterschiedliche Dateien sein kann.
- Default: pro `uses`-Eintrag wird die *kleinste* Version genommen, die alle Lower Bounds erfüllt. Vorhersagbar, ohne Magie.

---

### Achse 4 – Lockfile

| PM | Lockfile | Hashes | Reproduzierbarkeit |
|---|---|---|---|
| npm | `package-lock.json` | ja (sha512) | gut, aber häufige Schema-Wechsel |
| Cargo | `Cargo.lock` | ja | sehr gut |
| Poetry | `poetry.lock` | ja | sehr gut |
| Go | `go.sum` | ja, **separat** vom `go.mod` | exzellent, immutable verifiziert |
| Bundler | `Gemfile.lock` | nein historisch | mittelmäßig |

**Krankheit**: Drift zwischen Maschinen, Supply-Chain-Tampering ohne Hash-Pinning.

**Entscheidung – `flowcation.lock`** (USP): pro aufgelöster Spec mindestens

```yaml
- id: "@org/login-with-otp"
  version: 1.4.0
  sha256: "…spec-bundle-digest…"
  resolved_via: "registry.flowcation.com"
  # flowcation-spezifisch:
  target: swiftui
  generator:
    model: claude-sonnet-4.5-2026-03
    prompt_version: 7
    seed: 1234
  generated_files_sha256:
    - path: Sources/Login/LoginView.swift
      sha256: "…"
```

Damit ist die Generierung reproduzierbar, nicht nur die Auflösung. `flowcation verify` in CI prüft beide Hashes.

---

### Achse 5 – Immutability / Yank

| PM | Politik |
|---|---|
| Maven Central | komplett unveränderlich, kein Delete |
| Cargo | `cargo yank` (zukünftige Resolves überspringen, alte Builds funktionieren weiter) |
| npm | historisch `unpublish` < 72h → Left-Pad-Disaster; heute eingeschränkt |
| Go Proxy | unveränderlich gecached |

**Krankheit**: Builds, die Monate später anders/gar nicht mehr bauen.

**Entscheidung**: **Maven-/Cargo-artig**. Einmal publiziert, **nie löschen**. Nur `flowcation yank` mit Pflicht-Begründung; geyankte Versionen werden in der Auflösung neuer Resolves übersprungen, aber bleiben für existierende Lockfiles erreichbar.

---

### Achse 6 – Trust / Supply Chain

| PM | Mechanismus |
|---|---|
| npm/PyPI (2024+) | sigstore-Signaturen, Provenance |
| Maven | GPG-Signaturen pflicht für Central |
| Go | öffentlicher Checksum-DB (transparent log) |
| Cargo | crates.io Index in Git, signiert (in Ausbau) |

**Krankheit**: Malicious Packages, Account-Takeover (event-stream, ua-parser-js).

**Entscheidung**: **sigstore-artige Signaturen** von Anfang an im Schema vorgesehen, auch wenn die Umsetzung Phase 2+ ist. Zusätzlich:

- Public Transparency Log à la Go Checksum-DB für alle veröffentlichten Spec-Hashes.
- Pflicht-2FA für Publish (npm-Lehre).
- Optional: Spec-Inhalts-Diff bei Major-Bump muss menschlich reviewed sein (Web-UI).

---

### Achse 7 – Distribution / Mirroring

| PM | Modell |
|---|---|
| Maven | Central + Nexus/Artifactory-Mirrors |
| PyPI | Public + private Indexe (mit Vorrang-Risiko: confused deputy) |
| npm | Public + Verdaccio |
| Go Proxy | Globaler Caching-Proxy by default |

**Krankheit**: Single Point of Failure, „dependency confusion" zwischen Public/Private.

**Entscheidung**: 

- **Federation** vorgesehen: jedes Team kann eigenes Registry hosten; flowcation.com ist Index + Default-Proxy.
- **Scopes sind Registry-gebunden**: `@org/x` darf nur aus dem für `@org` registrierten Registry kommen. Verhindert dependency-confusion-Angriffe (PyPI-Lehre).
- Air-gapped-Builds möglich via Lockfile + Hashes ohne Netz.

---

### Achse 8 – Monorepo / Workspaces

| PM | Workspace-Modell |
|---|---|
| Cargo | Workspaces nativ |
| pnpm/Yarn | Workspaces nativ |
| Nx/Turborepo | Layer obendrauf |
| Maven | Multi-Module-POMs |

**Krankheit**: Schmerzen bei Multi-Spec-Repos (jede Spec einzeln publishen, Versionen synchron halten).

**Entscheidung**: **Cargo-/pnpm-artige Workspaces** ab Phase 2. `flowcation.workspace.yaml` listet mehrere Specs, gemeinsame Version optional, gemeinsamer Lockfile, `flowcation publish --workspace`.

---

## 3. Was wir bewusst NICHT übernehmen

| Aus | Was | Warum nicht |
|---|---|---|
| npm | Caret-Default (`^1.2.3`) | Silent-Breaking, schwer reproduzierbar |
| npm | `unpublish` < 72h | Left-Pad-Lehre |
| npm | flat namespace ohne Scope | Squatting, Verwechslung |
| pip/npm | Backtracking-Resolver mit Solver-Magie | Nicht-deterministisch, langsam |
| Cargo | „eine Version pro Build" | Bei generiertem Code nicht nötig |
| Maven | Range-Syntax `[1.0,2.0)` | Selten verstanden, fehleranfällig |
| Bundler | Lockfile ohne Hashes | Supply-Chain-blind |

---

## 4. flowcation-spezifische Erweiterungen (kein anderer PM hat das)

1. **`--target`** als first-class-Bürger jeder Operation (`pull`, `verify`, `lock`).
2. **Generator-Pin im Lockfile** (`model`, `prompt_version`, `seed`) → Reproduzierbarkeit *des Outputs*, nicht nur *der Auflösung*.
3. **Conformance-Tests pro Target** als Teil der Spec → ersetzen API-Kompatibilität als Vertrag.
4. **MCP-Resolver** als gleichberechtigte Schnittstelle zur CLI: jede Resolver-/Codegen-Operation ist via MCP für Agents aufrufbar.
5. **Doppelter Hash im Lockfile**: Spec-Bundle UND generierte Dateien.

---

## 5. Konkrete Entscheidungen (zusammengefasst)

| Designachse | Entscheidung | Vorbild |
|---|---|---|
| Identität | `@scope/name@version` + `sha256` | npm-Scopes + OCI-Digest |
| Namensschutz | reservierte/verifizierte Scopes, registry-gebundene Scopes | npm + PyPI-Lehre |
| Versionierung | SemVer pflicht, kein Caret-Default | (negativ) npm |
| Resolver | MVS – Minimum Version Selection | Go |
| Lockfile | Hashes pflicht, Generator-Pin, Output-Hashes | Go + neu |
| Immutability | unveränderlich, `yank` mit Begründung | Maven + Cargo |
| Trust | sigstore-artige Signaturen, Transparency Log, 2FA pflicht | npm/PyPI 2024+ + Go |
| Distribution | Federation, registry-gebundene Scopes | Maven + PyPI-Lehre |
| Workspaces | nativ ab Phase 2 | Cargo + pnpm |

---

## 6. Offene Punkte (vor Phase 2 zu klären)

- **Yank-Politik im Detail**: Grace-Period, automatisches Yank bei CVE?
- **Pre-Release-Workflow**: Wie laufen `1.4.0-rc.1` und stabile `1.4.0` parallel?
- **Modell-Drift**: Wenn das in `generator.model` gepinnte Modell EOL geht – Migrations-Tool?
- **Diamond-Specs in MVS**: Wenn Spec A v2 verlangt und Spec B v1 verlangt, wird Output für beide separat generiert oder erzwungen v2? (Default: separat, da Output ≠ Modul.)
- **Confused-Deputy-Schutz**: Konkrete Mechanik der registry-gebundenen Scopes.

---

## 7. Nächste Schritte

1. Diese Entscheidungen in den `flowcation-plan.md` als neue Sektion **„npm-artiger Workflow konkret"** übernehmen.
2. Phase 4 (Desktop) im Plan als „geparkt" markieren, MCP-Server in den frühen Kern ziehen.
3. Artikel `topics/flowcation/01-spec-first-komponenten/article_de.md` entsprechend anpassen (CLI + MCP + Playground vorne, Desktop optional/später, neue Sektion „So fühlt sich der Workflow an" mit konkretem CLI-/MCP-Beispiel und Verweis auf dieses Dokument).

---

## Quellen / Lesestoff

- Russ Cox: *Minimal Version Selection* — research.swtch.com/vgo-mvs
- npm Blog: *left-pad incident postmortem* (2016) und *unpublish policy* (2016/2024)
- PyPI: *Dependency Confusion* (Alex Birsan, 2021)
- Go: *Module Authentication with go.sum* — go.dev/ref/mod
- sigstore: *Keyless Signing for OSS* — sigstore.dev
- Maven Central: *Requirements for Publishing* (GPG, Coordinates, Immutability)
- Cargo Book: *Resolver* und *Yanking versions*
