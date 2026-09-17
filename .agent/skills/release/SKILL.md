---
name: release
description: Publish a new Speccify desktop version end to end — spec, version bump, release notes, checks, tag, four signed platform builds, update manifest, publication, public feed and the local update proof. Use when the user says "release", "veröffentlichen", "als 0.x.y rausgeben", asks to tag a version, or when a release workflow failed and must be repaired without moving the tag.
---

# Release

One tag builds macOS (Apple Silicon), Windows x64, Linux x64 and Linux arm64,
verifies every update package and attaches `latest.json` to a **draft**. A human
decision publishes; here that decision is the user's explicit release request.

Setup, secrets and background live in `docs/release.md`. This skill is the run
sheet plus the pitfalls learned in specs 049–058. Related skills:
`project-checks`, `local-app`, `app-screenshots`, `macos-notarize-tauri`.

## Authorization

- A tag needs an explicit user request for **this** version ("publish as 0.8.3").
  Standing commit/push permission does not cover tags. No request → prepare, ask.
- Never move or delete a pushed release tag. Never regenerate the updater key:
  installed apps trust the existing one.
- Release approval is not human acceptance of the shipped specs; leave their
  `ready`/`needs_human` state alone.

## 1. Spec and scope

Create `.agent/specs/<NNN>-release-<xyz>/SPEC.md` in `Doing` (next free number,
two history lines). State what ships and what is explicitly out. Check
`./scripts/dev.sh --status --ui-port=18768` and note the running local app.

## 2. Version — four places, one value

- `apps/desktop/package.json`
- `apps/desktop/src-tauri/tauri.conf.json`
- `apps/desktop/src-tauri/Cargo.toml`
- `Cargo.lock` → the `speccify-desktop` package entry only

`grep -rn "<old version>"` also hits unrelated crates (`toml 0.8.2`,
`schemars 0.8.22`). Edit exact lines; never replace globally.

## 3. Texts

- `apps/marketing/src/content/docs/releases/<x-y-z>.md` (English): what changed,
  "Update or install" (in-app from 0.8.1+, fresh installer for 0.8.0 and older —
  those lack the verification key; deb/rpm via package manager), verification
  and honest limits. Copy the structure of the previous release file.
- `apps/marketing/src/pages/index.astro`: the "What's new" link.
- Docs pages that say "Available in Speccify x.y.z" only when the feature is new.
- Playbooks in the same change set: `stand-und-ui.md`, `website.md`,
  `weiterentwicklung.md` when scope or workflow changed.
- UI changed visibly on a demo motif → run the `app-screenshots` skill and
  inspect every image. Otherwise say why no capture was needed.

## 4. Checks

Run the full set from the `project-checks` skill, including the marketing build
and the browser regressions that touch the changed area. Record counts.

## 5. Commit, push, wait

Conventional commit `chore(release): prepare Speccify x.y.z` with `Spec:`,
`Branch:` and `Validation:` lines. Push `main` (deploys the website). Wait until
**CI**, **Docs & Marketing Site** and **Deploy site** are green for that commit:

```sh
gh run list --limit 6 --json databaseId,name,status,conclusion,headSha
gh run watch <id> --exit-status --interval 30
```

`gh run list --commit` needs the full SHA; a short one returns nothing.
"Deploy site" failing with "in progress deployment" is a collision with the
previous push: wait a minute, `gh run rerun <id> --failed`.

## 6. Tag

```sh
git tag vX.Y.Z && git push origin vX.Y.Z
```

Only `v<major>.<minor>.<patch>` triggers the workflow. Never `git push --tags`:
the repo carries old phase tags.

## 7. Release text before the manifest job

`scripts/build_update_manifest.py` copies the **draft's body** into `latest.json`
as the notes users see in the update dialog. The workflow's default body is
generic. As soon as the draft exists (first platform job, a few minutes in) and
before the builds finish (~20–40 min), set the final text:

```sh
gh release view vX.Y.Z --json isDraft,databaseId
gh release edit vX.Y.Z --notes-file <notes.md>
```

Body: short change list, update/install paths per platform, verification and
limits, links to the release guide and downloads, and the spec-register snapshot
(`git -C .agent/specs rev-parse HEAD`). If the text changes after the manifest
was built, re-run with `verify_only` (step 9) so notes and manifest match.

## 8. Watch the workflow

```sh
gh run list --workflow release.yml --limit 1
gh run watch <id> --exit-status --interval 60
```

Jobs: four platform builds → `verify-macos-dmg` (notarizes and staples the DMG)
→ `update-manifest`. All must be green.

## 9. Repairing a failed run

- Transient failure (GitHub HTTP 5xx, notarization timeout): re-run **only the
  failed job**: `gh run rerun <id> --failed`.
- Re-verify existing packages without rebuilding installers:
  `gh workflow run release.yml --ref main -f tag=vX.Y.Z -f verify_only=true`.
- Real defect: fix on `main`, release the next patch version. Do not move the tag.
- Draft releases answer 404 on the REST tag endpoint; resolve the numeric id with
  `gh release view <tag> --json databaseId` and use `/releases/<id>`.

## 10. Verify the draft independently

Download into the scratchpad, not the repo:

- 20 assets expected (compare with the previous release's asset list).
- The four update packages (`Speccify_aarch64.app.tar.gz`, `*_x64-setup.exe`,
  `*_amd64.AppImage`, `*_aarch64.AppImage`) plus their `.sig`: rebuild the
  manifest locally with the same script CI uses. It checks upload state, size,
  SHA-256 and the real minisign signature (needs `minisign`; Tauri's `.sig` and
  public key are base64-wrapped, plain `minisign -V` on them fails):

  ```sh
  id=$(gh release view vX.Y.Z --json databaseId -q .databaseId)
  gh api repos/mhennemeyer/speccify/releases/$id > $S/release.json
  gh release download vX.Y.Z --dir $S/pkgs --pattern '*.sig' --pattern '*.app.tar.gz' \
    --pattern '*-setup.exe' --pattern '*.AppImage' --pattern latest.json
  python3 scripts/build_update_manifest.py $S/release.json $S/pkgs --output $S/latest.local.json
  ```

  The script reads the public key from the working tree's `tauri.conf.json`;
  make sure it equals the tag's (`git diff vX.Y.Z -- apps/desktop/src-tauri/tauri.conf.json`).
- Compare `latest.local.json` with the attached `latest.json` (ignore
  `pub_date`): version without `v`, four platforms, URLs on the tag path, notes
  equal to the final body.
- macOS: `codesign --verify --deep --strict` on the app and each binary under
  `Contents/MacOS`; `xcrun stapler validate` on app **and** DMG;
  `spctl -a -vvv -t exec` on the app, `spctl -a -t open --context
  context:primary-signature` on the DMG → `Notarized Developer ID`.

## 11. Publish — CLI only

```sh
gh release edit vX.Y.Z --draft=false
```

The web button fails with "author does not have push access" because the draft
belongs to the Actions bot.

## 12. Public proof

- `https://github.com/mhennemeyer/speccify/releases/latest/download/latest.json`
  equals the verified manifest; all four target URLs answer 200 unauthenticated
  (`curl -sIL -o /dev/null -w '%{http_code}'`).
- `https://speccify.io/releases/<x-y-z>/` and the landing link are live.

## 13. Update the local app through the real updater

Use the `local-app` skill. Announce the restart, make sure no drafts, editors or
terminals are open, then in the running app: Environment → Updates → search →
download → install. Confirm the new version, state `current`, restored windows
and a valid signature of the installed bundle. This is the macOS acceptance;
Windows and Linux installation stay named open points unless actually tested.

## 14. Close

Second commit `docs(release): record verified x.y.z publication` — release notes
verification paragraph, `docs/release.md` updater section, playbooks. Fill
`## Verification` in the spec with run ids, counts and what was **not** proven,
append `agent_run`, set `station: Done`, log `station_changed`.

## Evaluate — try to prove it went wrong

- Does an installed previous version really offer and install the new one?
- Does the manifest's note text match what was published?
- Is any claim in the notes backed only by CI where it says "verified"?
- Did anything land in the repo that belongs in the scratchpad (downloads, keys)?
