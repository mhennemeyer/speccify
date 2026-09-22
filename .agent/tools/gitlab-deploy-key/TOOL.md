---
name: gitlab-deploy-key
description: >-
  Puts one SSH public key into GitLab projects as a deploy key —
  read-only unless asked otherwise — and proves per project that it is there.
  Three modes, so the write is a separate, deliberate step: `plan` checks the
  inputs offline, `check` reads token, rights and existing keys, `apply` creates
  the key once and enables it everywhere else.
inputs:
  type: object
  required: [host, projects, title, key]
  additionalProperties: false
  properties:
    host:
      type: string
      description: GitLab host, e.g. `git.example.com` (https is assumed; a
        scheme is accepted and stripped).
    projects:
      type: array
      minItems: 1
      items: {type: string}
      description: Project paths `group/name`. The key is created in the first
        and enabled in the others.
    title:
      type: string
      description: Deploy-key title as shown in GitLab.
    key:
      type: string
      description: The OpenSSH public key line (`ssh-ed25519 AAAA… comment`).
    can_push:
      type: boolean
      default: false
      description: Grant write access. Default and recommendation is false.
    mode:
      type: string
      enum: [plan, check, apply]
      default: plan
      description: plan = validate inputs, no network; check = read only;
        apply = create/enable, then verify.
outputs:
  type: object
  required: [ok]
  description: >-
    A successful run also carries mode, fingerprint and projects; an input
    or token error carries only ok=false and error.
  properties:
    ok: {type: boolean}
    mode: {type: string}
    fingerprint: {type: string, description: SHA256 fingerprint of the key.}
    title: {type: string}
    can_push: {type: boolean}
    user: {type: string, description: Token owner (check/apply).}
    scopes: {type: array, items: {type: string}, description: Token scopes when
      the instance reports them (check/apply).}
    projects:
      type: array
      items:
        type: object
        required: [path, state]
        properties:
          path: {type: string}
          id: {type: integer}
          access_level: {type: integer, description: 40 = Maintainer, 50 = Owner.}
          state:
            type: string
            description: planned | missing | present | created | enabled |
              mismatch (present with a different can_push) | error
          key_id: {type: integer}
          detail: {type: string}
    error: {type: string}
effects: >-
  plan and check write nothing; apply creates one deploy key and
  enables it on the remaining projects, nothing else
requires: python3
runtime: any
platforms: macos, linux
---

## Behaviour

`check` and `apply` need `GITLAB_TOKEN` in the environment (scope `api`,
Maintainer or above on every project). `requires` lists only executables, so
the token is not among them; the tool checks it itself.

1. Validate the inputs before touching anything: at least one project, a
   non-empty title, a public key whose base64 blob decodes and whose type
   matches its prefix. Compute the SHA256 fingerprint the way `ssh-keygen -l`
   does. Errors here end with `ok: false`, an `error` and exit code 1.
2. `plan` stops there and lists every project as `planned`.
3. `check` and `apply` read `GITLAB_TOKEN` from the environment — never from
   the input, and it never appears in the output. Without it: error before any
   request. Then `GET /user` (who the token is), `GET /personal_access_tokens/self`
   (scopes, tolerated when the instance does not offer it) and per project
   `GET /projects/:path` (id, highest access level of project and group) and
   `GET /projects/:id/deploy_keys`. A key with the same fingerprint is
   `present`; with a different `can_push` it is `mismatch`; otherwise `missing`.
4. `apply` creates the key on the first project that misses it
   (`POST /projects/:id/deploy_keys`, `can_push` as requested) and enables the
   resulting key id on every other missing project
   (`POST /projects/:id/deploy_keys/:key_id/enable`), because GitLab keeps one
   key object per fingerprint. A `mismatch` is never changed — report it.
   Afterwards list again: `ok` only when every project has the key with the
   requested `can_push`.
5. Any HTTP error is reported per project as `error` with the status and
   GitLab's message; the run continues with the other projects so the output
   is complete.

The tool never deletes or modifies existing keys and never grants more than
asked.

## Examples

### plan: valid inputs, three projects, read-only
input: {"host": "git.example.com", "projects": ["avc/rekas", "avc/billi-legacy", "avc/billi-ci"], "title": "billi-vm-deploy-readonly", "key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIL/VDVPw/581kpNLpMU8V83lGizGEOxYE2BLQmApUxjn billi-vm-deploy-readonly", "mode": "plan"}
output: {"ok": true, "mode": "plan", "fingerprint": "SHA256:XTLqHKg7/8f+1dG7YKwhKXMtyXSsl/PziwT1eZc1IuQ", "title": "billi-vm-deploy-readonly", "can_push": false, "projects": [{"path": "avc/rekas", "state": "planned"}, {"path": "avc/billi-legacy", "state": "planned"}, {"path": "avc/billi-ci", "state": "planned"}]}

### plan: the key is not an OpenSSH public key
input: {"host": "git.example.com", "projects": ["avc/rekas"], "title": "x", "key": "-----BEGIN OPENSSH PRIVATE KEY-----", "mode": "plan"}
output: {"ok": false, "error": "key is not an OpenSSH public key line (expected `ssh-ed25519 AAAA…`)"}

### plan: no projects
input: {"host": "git.example.com", "projects": [], "title": "x", "key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIL/VDVPw/581kpNLpMU8V83lGizGEOxYE2BLQmApUxjn c", "mode": "plan"}
output: {"ok": false, "error": "projects must name at least one project (group/name)"}

`check` without `GITLAB_TOKEN` answers `{"ok": false, "error": "GITLAB_TOKEN is
not set …"}` with exit code 2 before any request; not listed as an example
because examples run with the caller's environment.
