# Deploy — Marketing-Site (`apps/marketing/`)

Die Landingpage + Doku-Site (`apps/marketing/`, Astro Starlight) wird auf
**Vercel** unter der Domain `speccify.io` gehostet. Die Code-Seite ist
hosting-agnostisch — der Build (`pnpm --filter speccify-marketing build`) läuft
auch lokal und in CI (`.github/workflows/docs.yml`).

## Vercel-Setup (einmalig, Maintainer-Schritte)

1. Neues Vercel-Projekt anlegen, Repo verbinden.
2. **Root Directory**: `apps/marketing`.
3. **Framework Preset**: Astro (Build `pnpm build`, Output `dist`).
4. **Install Command**: `pnpm install --frozen-lockfile` (vom Repo-Root, pnpm-Workspace).
5. Custom-Domain `speccify.io` zuweisen.
6. PR-Previews sind Vercel-Default — pro PR entsteht eine Preview-URL.

## Environment-Variablen

| Variable | Zweck | Wirkung wenn leer |
| --- | --- | --- |
| `PUBLIC_PLAYGROUND_URL` | Iframe-Quelle auf `/try-it` | Fallback-Block mit Cross-Link |
| `PUBLIC_PLAUSIBLE_DOMAIN` | Plausible-Analytics-Domain | Kein Analytics-Snippet |

`PUBLIC_PLAUSIBLE_DOMAIN` greift nur in Production-Builds (`NODE_ENV=production`),
sodass Dev-Builds nie tracken.

## Lokaler Build / Preview

```bash
cd apps/marketing
pnpm install
pnpm dev        # http://localhost:4321
pnpm build      # erzeugt dist/
pnpm preview    # serviert dist/
```

## Content-Sync

Die Doku-Inhalte sind aus dem Repo-`docs/` gespiegelt und die CLI-Reference aus
der Binary generiert. Vor dem Commit neu generieren:

```bash
uv run python scripts/sync_docs_to_site.py   # docs/ → Site-MDX
uv run python scripts/gen_cli_docs.py        # speccify --help → CLI-Reference
```

CI (`docs.yml`) bricht bei Drift via `--check`.
