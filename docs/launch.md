# Launch checklist

What is left before this repository is public, and what to say when it is.
Everything here is a decision or an account action — none of it can be done
from inside the repository.

## Before the repository goes public

- [x] **Remote and workflows.** `main` is the default branch;
      `master` holds an unrelated 2009 project of the same name and is left
      untouched, so old links keep working.
- [x] **Site deploys itself.** `pages.yml` publishes `apps/marketing/` to
      GitHub Pages on every push to `main`, after re-checking that the docs on
      the site still match the repository.
- [x] **Releases build themselves.** `release.yml` builds the app on a `v*`
      tag and opens a draft release.
- [x] **speccify.io points at GitHub Pages.** Four `A` records on the apex, a
      `CNAME` for `www`, custom domain set, Let's Encrypt certificate issued and
      HTTPS enforced. The wildcard `*.example.com` record was removed: it served
      a stranger's 404 page under the domain and would have masked a typo in any
      future subdomain record with a page instead of `NXDOMAIN`.
- [ ] **Check `LICENSE` and the author line.** MIT, one copyright holder.
- [ ] **Seed the index repository.** Discovery needs at least one index with a
      handful of entries, otherwise `speccify search` is an empty room. Format
      and the pull-request flow are in [`../index/README.md`](../index/README.md).

### DNS for speccify.io

```text
A      @      185.199.108.153
A      @      185.199.109.153
A      @      185.199.110.153
A      @      185.199.111.153
CNAME  www    mhennemeyer.github.io.
```

Then enable *Enforce HTTPS* in the repository's Pages settings — it only
becomes available once the certificate has been issued, which takes a few
minutes after DNS propagates.

## Optional, and clearly marked as pending

Neither blocks a launch, and the first is visible on the site as "not yet":

- [ ] **Signed Mac app.** Needs an Apple Developer ID certificate and an
      app-specific password as repository secrets — the workflow header lists
      the exact names. Until then the release is unsigned, and the download
      page says so plainly instead of letting people meet "Speccify is damaged"
      with no explanation. Set the repository variable
      `PUBLIC_RELEASE_SIGNED=true` once signing is live to drop that notice.
- [ ] **Updater key.**
      `pnpm --filter speccify-desktop tauri signer generate -w ~/.speccify/updater.key`,
      then the private key as the secret `TAURI_SIGNING_PRIVATE_KEY` and the
      public key as the repository *variable* `TAURI_UPDATER_PUBKEY`. The
      updater stays deliberately inert until both exist — a half-wired updater
      is worse than none.
- [ ] **Intel Macs.** The release builds for Apple Silicon only, because
      `build_sidecars.sh` builds sidecars for the host triple and a universal
      bundle needs both. It is a change to that script, not a flag in the
      workflow.

## What to say

The honest version of the story, because it is the interesting part:

> Speccify started as fine-grained component specs you would compose into
> larger things. Coding agents got good enough that describing a button stopped
> being worth doing. What they still lack is the knowledge *around* a task — the
> order, the fine print, the dead ends. So a spec became a **playbook**: a
> complex, recurring workflow with its steps, the sources each one came from,
> the assets it needs, and the pitfalls you only find out about once.

Three things that hold up in a discussion, because each is implemented:

1. **Rot is a first-class concern.** Every source carries the date it was
   retrieved; `speccify check` reports age and, with `--links`, whether the URL
   still resolves. A stale playbook is worse than none, so the tool says so.
2. **No registry, no account.** The repository URL is the identity, tags are
   the versions — Go modules, not npm. Discovery is index repositories you
   extend by pull request.
3. **No edit mode.** Reading and asking is what a human does now; the writing
   is done by the agent next to the viewer, and every change arrives as a diff
   with an Apply button.

The thing to be upfront about: the four reference playbooks in `playbooks/`
come from two real projects, but this has not been used by anyone else yet. It
is a working tool with a sample size of one.

## Where to post

Order matters — the first one sets the framing that gets quoted afterwards.

1. **GitHub repository** with the README as the landing text.
2. **Hacker News**, "Show HN". The pivot story is the hook, not the feature
   list.
3. **Mastodon / X**, one thread of the same story with a link.
4. **Reddit** — r/MacApps for the trial-purchase playbook specifically, since
   that is the one with a concrete audience.

Do not post to all four at once. If the first conversation surfaces a
misunderstanding, it is cheaper to fix the README before the rest goes out.
