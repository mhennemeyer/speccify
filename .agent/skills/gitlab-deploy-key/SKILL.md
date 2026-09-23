---
name: gitlab-deploy-key
description: Put a machine's SSH public key into GitLab projects as a read-only deploy key — check token and rights first, let the human approve the write, then prove per project that the key is there and that the machine can pull. Use when a VM, container or CI runner needs to clone or pull from GitLab without a personal account, when a spec asks the human to "hinterlege den Key in GitLab", or when the user mentions deploy key, GitLab, git pull auf der VM, Remotes auf SSH.
---

# GitLab deploy key

A deploy key gives one machine read access to a repository without a person's
credentials. The machine makes the key pair; only the public half travels. The
step that needs a human is the write into GitLab — it grants access — so this
skill separates reading from writing and asks before the write.

Tool: `.agent/tools/gitlab-deploy-key/` (`TOOL.md` is the contract; run
`python3 .agent/tools/gitlab-deploy-key/macos.py` or `linux.py` with one JSON
object on stdin).

## 1 — Get the public key

The key is made **on the machine that will pull**, never on the developer's
laptop and never by the agent on the human's behalf (on a Windows VM:
`ssh-keygen -t ed25519 -N "" -C <machine>-deploy-readonly -f C:\Users\<user>\.ssh\id_ed25519_deploy`;
the agent's auto mode blocks `ssh-keygen` as persistence — the human runs it).
Take only the `.pub` line. A line starting with `-----BEGIN` is the private
key: refuse it and say so.

**Verify:** `mode: plan` returns `ok: true` with the fingerprint, and
`ssh-keygen -lf <pubfile>` on the machine shows the same fingerprint.

## 2 — Check before you write

```sh
printf '%s' '{"host":"git.example.com","projects":["group/a","group/b"],"title":"vm-deploy-readonly","key":"ssh-ed25519 AAAA… comment","mode":"check"}' \
  | python3 .agent/tools/gitlab-deploy-key/macos.py
```

Reads only. It tells you whose token this is, its scopes, the access level per
project (40 Maintainer, 50 Owner — below 40 the write will fail) and whether
the key is already `present`, `missing` or `mismatch` (present with a different
`can_push`).

**Verify:** every project is listed with an id and access level ≥ 40, `scopes`
contains `api` (when reported), no project is `error`.

## 3 — Ask, then apply

Adding a key grants access. Show the human the check result and ask for the
go — in the chat, or with `ask_bo` when the app runs. An agent in auto mode
will see the write blocked as a permission grant: then hand the exact command
to the human to run with the `!` prefix in the session, do not work around it.

```sh
printf '%s' '{…same input…, "mode":"apply"}' | python3 .agent/tools/gitlab-deploy-key/macos.py
```

`apply` creates the key on the first project that lacks it and enables the
same key id on the others (GitLab keeps one key object per fingerprint). It
never changes a `mismatch`; report it and let the human decide.

**Verify:** the output has `ok: true` and every project is `created`,
`enabled` or `present` — the tool re-reads after writing, but look yourself:
Project → Settings → Repository → Deploy keys shows the title, and the other
projects list it under "Privately accessible deploy keys" as enabled.

## 4 — Prove it from the machine

On the machine that owns the private key, with the remote on SSH
(`git remote set-url origin git@<host>:<group>/<name>.git`):

```sh
ssh -T git@<host>            # "Welcome to GitLab, @<project>+deploy-key-…"
git ls-remote origin HEAD    # one line, no prompt
git pull                     # works
git push --dry-run           # refused: the key is read-only
```

**Verify:** `git pull` succeeds and `git push --dry-run` is rejected with a
permission error. A push that succeeds means `can_push` is true — remove or
fix the key.

## Evaluate — try to prove it went wrong

- Run `mode: check` again: is the key `present` with `can_push: false` on
  every project, and not on any project you did not name?
- Is the same fingerprint listed anywhere with write access (an older key with
  the same blob)? `mismatch` in the check output says so.
- Did the token or the key line land in a spec, a history line, a terminal
  transcript or a commit? `git log -p -S'PRIVATE-TOKEN'`, and grep the spec.
- Does `git push` from the machine really fail, not just "nothing to push"?

## Pitfalls

- **`api` scope, Maintainer or above.** `read_api` lists keys but cannot add
  them; Developer cannot either. The check step shows both before you try.
- **One key object per fingerprint.** Posting the same key to a second project
  answers 400 "has already been taken"; use enable with the existing id (the
  tool does). Deleting the key on the first project removes it everywhere.
- **`ssh -T` without a shell.** Deploy keys have no account; `ssh -T` greets
  with the deploy-key identity, an interactive login is not expected.
- **Wrong host key on first contact.** `git ls-remote` on a fresh machine
  prompts to accept the host key; do it once, interactively, not by disabling
  checking.
- **`fingerprint_sha256` comes without the `SHA256:` prefix** (GitLab 19.x),
  while `ssh-keygen -l` prints it with. Compare the bare digest, or the key
  blob. The first `apply` on 2026-09-22 wrote the key correctly and then
  reported it "missing" for exactly this reason.
- **The key line is public, the token is not.** Keys may be pasted into a
  chat or a spec; `GITLAB_TOKEN` stays in the environment. The tool refuses
  to read it from the input for that reason.

## In this project

- Host: `git.itsd-consulting.de` (self-hosted GitLab, API v4).
- Token: `GITLAB_TOKEN` in the shell environment of the developer's Mac
  (scope `api`, expires 2027-04-01; owner `matthias.hennemeyer`, Owner on
  the `avc` projects).
- First use (2026-09-22, AVC/rekas spec 008, Q1): key `billi-vm-deploy-readonly`
  from the Windows VM `billi-vm` for `avc/rekas`, `avc/billi-legacy`,
  `avc/billi-ci`; fingerprint `SHA256:XTLqHKg7/8f+1dG7YKwhKXMtyXSsl/PziwT1eZc1IuQ`.
  The write needs the human: run `apply` with the `!` prefix or click in
  GitLab (Settings → Repository → Deploy keys → Add new key, write permission
  unchecked; then Enable in the other two projects).
