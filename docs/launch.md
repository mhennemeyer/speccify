# Launch checklist

What is left before this repository is public, and what to say when it is.
Everything here is a decision or an account action — none of it can be done
from inside the repository.

## Before the repository goes public

- [ ] **Create the remote and push.** There is no git remote today. The default
      branch should be `main`; `feat/oss-pivot` carries the current work.
- [ ] **Check `LICENSE` and the author line.** MIT, one copyright holder.
- [ ] **Decide what the archive branches say.** `archive/pre-oss-pivot-registry`
      and `archive/pre-playbook-pivot` hold the two abandoned directions. They
      are honest history and cost nothing to keep — but they are public once
      pushed. Either push them with that framing or leave them local.
- [ ] **Seed the index repository.** Discovery needs at least one index with a
      handful of entries, otherwise `speccify search` is an empty room. Format
      and the pull-request flow are in [`../index/README.md`](../index/README.md).
- [ ] **Deploy the docs site.** `pnpm --filter speccify-marketing build`
      produces a static site; [`deploy.md`](./deploy.md) has the target.

## Optional, and clearly marked as pending

Neither blocks a launch, and both are visible on the site as "not yet":

- [ ] **Signed Mac app.** Needs an Apple Developer ID and an app-specific
      password, then `./scripts/release_macos.sh`. Until `PUBLIC_DOWNLOAD_URL`
      is set, the download page shows the self-build route instead of a dead
      link.
- [ ] **Updater key.** `pnpm --filter speccify-desktop tauri signer generate`.
      The public key in `tauri.conf.json` is empty today, which keeps the
      updater deliberately inert rather than half-wired.

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
