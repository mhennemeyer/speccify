---
name: website-publish
description: Change and publish speccify.io — edit marketing pages or docs, build, check the landing pages at three widths, push to main and confirm the live result. Use when the user asks to update the website, docs, download page or release notes, or to check whether a website change is live.
---

# Website publish

`apps/marketing/` (Astro + Starlight) is the public site; product texts are
English. Design rules, motifs and approval state live in the living playbook
`.agent/playbooks/website.md` — read its checklist before changing images or
claims. A push to `main` touching `apps/marketing/**`, `docs/**` or the docs sync
scripts deploys through `pages.yml`. There is no staging: what is pushed is public.

Hosting (Spec 071, since 2026-09-26): the site is deployed to **Netlify**
(site `speccify`, account `mhennemeyer`, `https://speccify.netlify.app`) with
`netlify deploy --prod --no-build --dir=<absolute path to apps/marketing/dist>`;
the CLI resolves a relative `--dir` against the repository root, so pass the
absolute path. Redirects and headers ship inside `dist/` from
`apps/marketing/public/_redirects` and `_headers`; `/download/latest.json` and
`/download/<asset>` are the stable download addresses that forward to the
current asset host. GitHub Pages keeps receiving deploys until the DNS of
`speccify.io` points at Netlify; then the Pages job in `pages.yml` goes. The
workflow needs the secrets `NETLIFY_SITE_ID` (set) and `NETLIFY_AUTH_TOKEN`
(personal access token from app.netlify.com → User settings → Applications);
without the token the Netlify job skips itself and only Pages deploys. A manual
deploy from a machine with `netlify login` works the same way.

## Steps

1. Edit. Release notes: `src/content/docs/releases/<x-y-z>.md`; landing:
   `src/pages/index.astro`; app help: `src/content/docs/app/`. Claims describe
   shipped behaviour only; goals and proposals are not features. Signing claims
   per platform follow `PUBLIC_MACOS_RELEASE_SIGNED` /
   `PUBLIC_WINDOWS_RELEASE_SIGNED` (GitHub variables), independent of each other.
2. Build: `pnpm marketing:build` — must end with `Complete!`; check the new route
   under `apps/marketing/dist/`.
3. Landing or Features changed: `pnpm marketing:preview`, then
   `node scripts/test_landing_screenshots.mjs` (local preview only; checks `/`
   and `/features/` at 1440, 390 and 320 px, keyboard and no-JavaScript).
4. Images changed: `app-screenshots` skill, open every image, capture twice.
5. Update `website.md` (and `stand-und-ui.md` when product claims changed) in
   the same commit. Commit, push `main`.
6. Wait for **Deploy site** and **Docs & Marketing Site**
   (`gh run list --limit 6`, `gh run watch <id> --exit-status`).
   Two pushes in short succession make the second deploy fail with
   "Deployment request failed … due to in progress deployment". Wait a minute,
   then `gh run rerun <id> --failed`; no new commit needed.
7. Confirm live: `curl -s https://speccify.io/<route>/ | grep "<new text>"`.
   A green deploy is not the proof; the fetched page is.

Release-related website work is part of the `release` skill; do not publish
release notes for a version whose tag is not authorized.
