# Phase 6 — Landingpage + Doku-Site (`speccify.io`)

> **Status:** Entwurf (2026-06-02). Nachfolger von Phase 5c (`v0.10.0-phase-5c`).
> **Ziel-Tag:** `v0.11.0-phase-6` (Vorschlag, User setzt selbst).
> **Vorgänger-Plan:** `.agent/plans/archive/phase-5c-visual-regression-skeleton.md`.
> **Strategische Begründung:** Nach Phase 5c ist der technische Kern (CLI + MCP + Registry + Multi-Target-Codegen + Conformance + Visual-Regression-Skeleton) belastbar. Der größte ungebaute Hebel ist jetzt **Außenwirkung** — eine öffentliche Landingpage + durchsuchbare Doku-Site. Vertiefungen im Visual-Regression-Bereich werden in **Phase 7 (optional)** geparkt, damit nichts verloren geht.

## Vision (Phase-spezifisch)

> Ein Erstbesucher auf `speccify.io` versteht in **< 60 Sekunden**, was Speccify ist, sieht ein laufendes Beispiel (Playground-Embed oder GIF), kann in die Doku springen und findet eine **vollständige Quickstart-Anleitung** für CLI, MCP und Browser-Playground.

## Scope

### In-Scope

1. **Landingpage** (`apps/web/marketing/` oder neuer Workspace-Member `apps/marketing/`):
   - Hero („npm für Spezifikationen statt für Code")
   - Problem/Lösung-Block (3–5 Stichpunkte)
   - Demo-Block: Code-Snippet `speccify pull spec://button@1.0.0 --target react` + Output-Preview
   - Targets-Block (React, SwiftUI, Angular — mit Logos)
   - „How it works" (3 Schritte: Spec → Resolver → Codegen)
   - CTA: GitHub-Link + Quickstart-Link + Playground-Link
   - Footer: Lizenz (MIT), Imprint, Datenschutz-Platzhalter

2. **Doku-Site** (`apps/web/docs/` als Static-Site, Kandidat: **Astro Starlight** oder **Nextra**):
   - `Getting Started` (Install, erste Spec, erstes `pull`)
   - `Concepts` (Spec-Format, Lockfile, Resolver, Workspaces)
   - `CLI Reference` (alle Befehle, autogeneriert aus `--help`)
   - `MCP Reference` (Tool-Liste mit Schemas)
   - `Targets` (React/SwiftUI/Angular — Pinning, Idiom, Limitations)
   - `Conformance` (Build-Smoke + Visual-Regression — Cross-Link zu `docs/conformance.md` + `docs/visual-regression.md`)
   - `Registry` (Publish/Yank/Auth/Device-Code)
   - `Workspaces` (Cross-Link zu `docs/workspaces.md`)
   - Suche (Starlight/Pagefind eingebaut)

3. **Stack-Entscheidung Doku-Site**:
   - **Empfehlung: Astro Starlight** — minimaler JS-Footprint, MDX, Pagefind-Suche eingebaut, niedriger Maintenance-Overhead, separater Build vom Next.js-Playground.
   - Alternative: Nextra (Next.js-basiert, würde sich mit dem Playground-Stack decken).
   - Stage 0 klärt das mit dem User.

4. **Hosting/Deploy**:
   - Statisches Hosting auf **Vercel** (Empfehlung, gleicher Account wie Playground denkbar) oder **Cloudflare Pages**.
   - Domain `speccify.io` — User-Beschaffung, Plan trackt nur DNS-Konfiguration.
   - PR-Previews für Doku-Änderungen (Vercel-Default).

5. **Auto-Generierung CLI-Reference**:
   - Skript `scripts/gen_cli_docs.py` ruft `speccify <cmd> --help` für alle Top-Level-Commands ab und schreibt MDX nach `apps/web/docs/src/content/docs/cli/`.
   - Pre-Commit-Hook **optional** (Stage 0 klären).

6. **Playground-Embed**:
   - Doku-Seite „Try it" embedded den existierenden Playground (`apps/web/frontend/`) per `<iframe>` oder Cross-Link.
   - Kein neuer Renderer.

7. **CI**:
   - Neuer Workflow `.github/workflows/docs.yml` — `npm run build` für Doku-Site, Link-Check (lychee), Lint (markdownlint).
   - Pfad-Filter: `apps/web/docs/**`, `docs/**`.

### Out-of-Scope (explizit)

- **Marketplace** (kommerzielle Specs, Billing, Entitlements) — bleibt im Master-Plan „on hold".
- **Community-Features** (Discussions, Comments, Profile-Seiten auf der Landingpage) — separater späterer Plan.
- **i18n** (`speccify.io/de` aus dem Master-Plan) — Phase-6 baut nur EN. DE-Variante = Folge-Substage oder Phase 8.
- **SEO-Optimierung über Default-Meta hinaus** — separater späterer Plan.
- **Analytics** (Plausible/PostHog) — Stage 0 klärt, ob minimal mit rein.
- **Visuelle Vertiefungen** (echter Component-Mount-Renderer, volle Visual-Regression-Coverage, SwiftUI-Visual-Regression) → **Phase 7 (optional)**.

## Stages

### Stage 0 — Open Questions (User-Klärung, blockierend)

Vor Implementierungsstart als Block dem User vorlegen:

1. Doku-Stack: **Astro Starlight** vs. **Nextra** vs. **Docusaurus**?
2. Landingpage als neuer Workspace-Member (`apps/marketing/`) oder Sub-Route in `apps/web/`?
3. Hosting: Vercel (Default) vs. Cloudflare Pages vs. self-hosted?
4. Domain `speccify.io` schon registriert? Falls nein, Phase-6 trotzdem starten und auf Preview-Domain hosten?
5. Analytics: Plausible Cloud / PostHog / keine?
6. i18n in Phase 6 oder erst Phase 8? (Empfehlung: Phase 8, EN-only in Phase 6.)
7. CLI-Docs-Generierung: Pre-Commit-Hook + CI-Check, oder nur manuell?
8. Playground-Embed: `<iframe>` der live deployten Playground-Instanz, oder Static Screenshot/GIF?
9. Design: eigener Tailwind-Look oder Starlight-Default-Theme zunächst?
10. Lizenz/Imprint/Datenschutz — wer liefert Texte (User vs. Platzhalter)?

### Stage 1 — Workspace-Setup + Doku-Skeleton
- Neuer Workspace-Member nach Stage-0-Entscheidung (`apps/web/docs/` oder `apps/marketing/`).
- Doku-Tool initialisieren (Astro Starlight: `npm create astro@latest -- --template starlight`).
- Navigation aus Scope-Liste oben anlegen, leere Seiten als Stubs.
- `pnpm-workspace.yaml` / `package.json` anpassen.
- CI: Build-Job in neuem `.github/workflows/docs.yml`.

### Stage 2 — Content Migration aus `docs/`
- Bestehende `docs/*.md` (`conformance.md`, `visual-regression.md`, `workspaces.md`) als MDX in die neue Site übernehmen — entweder kopieren oder per Symlink/Re-Export.
- Querverlinkung von der Repo-`docs/` auf die Doku-Site (eine Quelle der Wahrheit zukünftig: Doku-Site; Repo-`docs/` wird Light-Mirror oder verweist).
- README-Update mit Doku-Site-Link.

### Stage 3 — CLI-Reference Autogen
- `scripts/gen_cli_docs.py` (Python, nutzt `speccify --help` + Subcommands).
- Output nach `apps/web/docs/src/content/docs/cli/`.
- Snapshot-Test: nach Regenerierung darf Diff nur erwartete CLI-Änderungen enthalten.
- Optional Pre-Commit-Hook gemäß Stage-0-Antwort.

### Stage 4 — Landingpage
- Hero + Sections gemäß Scope.
- Code-Highlighting via Shiki (Starlight built-in).
- Demo-Snippet: echter Output aus `speccify pull` als statischer Codeblock.
- Lighthouse-Budget: Performance ≥ 90, A11y ≥ 95.

### Stage 5 — Playground-Embed + Cross-Links
- „Try it"-Seite mit Embed.
- Footer-Cross-Links: GitHub, Playground, Doku.

### Stage 6 — CI + Link-Check + Deploy
- `lychee` Link-Check über die ganze Site.
- `markdownlint` für MDX.
- Vercel-Projekt (oder Cloudflare-Pages) verdrahten — User macht den Account-Setup, Plan dokumentiert nur die Config.
- Preview-Deploy pro PR.

### Stage 7 — Verifikation + Doku + Archivierung
- Manueller Smoke-Test:
  - `pnpm build` für Doku-Site grün
  - Alle internen Links auflösbar
  - CLI-Reference matcht aktuelle Binary
  - Playground-Embed lädt
- AGENTS.md aktualisieren („Aktuelle Phase").
- Plan archivieren nach `.agent/plans/archive/phase-6-landing-and-docs.md`.
- Tag-Vorschlag an User: **`v0.11.0-phase-6`** (nicht selbst setzen, vgl. `rules.md`).

## Risiken / Mitigation

| Risiko | Mitigation |
|---|---|
| Doku-Stack-Lock-In | Starlight ist Standard-MDX → Migrations-Pfad bleibt offen |
| Doppelte Quelle (Repo `docs/` vs. Site) | Stage 2 etabliert Single Source of Truth in der Doku-Site, Repo-`docs/` linkt nur |
| Vercel-Account / Domain blockt Stage 6 | Stages 1–5 sind hosting-agnostisch und liefern lokal nutzbare Site |
| Scope-Creep Marketplace/Auth/Community | Out-of-Scope explizit dokumentiert, Phase 7 + spätere Phasen sammeln Folge-Wünsche |

## Done-Kriterien

- [ ] Landingpage öffentlich erreichbar (Preview-Domain ok)
- [ ] Doku-Site mit Suche und allen Scope-Sektionen
- [ ] CLI-Reference autogeneriert + im CI verifiziert
- [ ] Quickstart-Path: Neuer Nutzer kann allein per Doku-Site `speccify lint` + `speccify pull` ausführen
- [ ] CI-Workflow `docs.yml` grün
- [ ] AGENTS.md + README aktualisiert
- [ ] Plan archiviert

## Cross-Referenzen

- Master-Plan: `.agent/plans/speccify-plan.md`
- Optionaler Folge-Plan für visuelle Vertiefung: `.agent/plans/phase-7-visual-regression-deepening.md`
- Archiv Phase 5c: `.agent/plans/archive/phase-5c-visual-regression-skeleton.md`
