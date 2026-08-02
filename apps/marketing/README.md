# speccify-marketing

Landingpage **und** Doku-Site für [Speccify](https://speccify.io), gebaut mit
[Astro](https://astro.build) + [Starlight](https://starlight.astro.build).
Teil des pnpm-Workspaces (`pnpm-workspace.yaml` im Repo-Root).

> Stand: **Phase 6, Stage 1** — Workspace-Member + Astro-Starlight-Skeleton.
> Doku-Sync, CLI-Reference-Autogen, finale Landingpage und Playground-Iframe
> folgen in den Stages 2–6.

## Entwicklung

```bash
# Vom Repo-Root:
pnpm install
pnpm --filter speccify-marketing dev      # http://localhost:4321

# oder via Root-Scripts:
pnpm run marketing:dev
pnpm run marketing:build
pnpm run marketing:preview
```

## Struktur

```
apps/marketing/
  astro.config.mjs        # Starlight + Tailwind-Vite-Plugin + Sidebar + Plausible-Env-Guard
  src/
    pages/index.astro     # Landingpage (eigener Tailwind-Look)
    pages/download.astro  # Desktop-App-Download (Fallback ohne Release)
    styles/landing.css     # Tailwind v4 Entry (nur Landing-Routen)
    content.config.ts      # Starlight-Docs-Collection
    content/docs/          # Doku (Stub-Seiten in Stage 1)
  public/logo.svg
```

## Analytics

Plausible wird **nur in Production** und **nur** bei gesetzter Env-Variable
`PUBLIC_PLAUSIBLE_DOMAIN` eingebunden (siehe `astro.config.mjs`).

## Download-Seite

`/download/` zeigt den dmg-Link nur, wenn beim Build gesetzt ist:

| Variable | Beispiel |
|---|---|
| `PUBLIC_DOWNLOAD_URL` | `https://speccify.io/releases/Speccify_0.2.0_aarch64.dmg` |
| `PUBLIC_DOWNLOAD_VERSION` | `0.2.0` |

Ohne die Variablen erscheint statt eines toten Links die Selbstbau-Anleitung
(`./scripts/dev.sh --release`) — gleiches Muster wie `PUBLIC_PLAYGROUND_URL`
auf `/try-it/`. Wie die Artefakte entstehen: [`docs/release.md`](../../docs/release.md).
