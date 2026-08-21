---
name: fastlane-mac-app-store
description: 'Build, upload and manage store metadata for a macOS app without ever typing
  a 2FA code: an App Store Connect API key instead of an Apple ID, lanes that stop short of
  submitting, a monotonic build number, and the two xcodebuild flags that decide whether the
  build runs at all. Use when working with fastlane or xcode on macos, or when the user mentions
  app-store, mac-app-store, ci, app-store-connect-api, testflight or xcodegen.'
license: MIT
compatibility: Requires Xcode, Ruby with bundler and App Store Connect access with App Manager
  role
---

## Prerequisites

- The app record exists in App Store Connect and the app id is registered under your team.
- A working `xcodebuild -configuration Release` before you automate anything. fastlane does not fix a broken build.

## 1 — Authenticate with an API key, not an Apple ID

Apple ID login means 2FA prompts, session expiry mid-upload and a
password in your environment. The App Store Connect API key removes all
three — fastlane lists the benefits as "no 2FA needed, better
performance, documented API, and increased reliability".

Create it in App Store Connect → Users and Access → Integrations → App
Store Connect API. The **App Manager** role is enough; do not hand out
Admin for a build machine.

You get three things, and you need all three:

* `key_id` — the key's identifier
* `issuer_id` — your team's issuer id (a UUID)
* the `.p8` file itself, **downloadable exactly once**

Know the gap before you rely on it: the key covers `pilot`, `deliver`,
`sigh`, `cert`, `match`, `download_dsyms`, `app_store_build_number` and
`precheck` — but **not** `precheck` for in-app purchases, not `pem`, and
only partly `produce`. If a lane suddenly asks for an Apple ID, that is
why, not a misconfiguration.

**Verify:** A lane that only calls `app_store_connect_api_key` succeeds without any interactive prompt.

*Source: fastlane — App Store Connect API key.*

## 2 — Keep the key out of the repository, and fail fast when it is missing

The `.p8` is a credential that cannot be re-downloaded. Store it outside
the repository, reference it by path, and put the three values in the
environment:

```ruby
def asc_api_key
  app_store_connect_api_key(
    key_id:       ENV.fetch("ASC_KEY_ID"),
    issuer_id:    ENV.fetch("ASC_ISSUER_ID"),
    key_filepath: ENV.fetch("ASC_KEY_PATH"),
    duration:     1200,        # seconds; 1200 is the documented maximum
    in_house:     false
  )
end
```

`ENV.fetch` rather than `ENV[]` — the former fails immediately with the
missing name, the latter passes `nil` down into an action that reports
something unrelated twenty seconds later.

`duration` is a session length in seconds and **1200 is the maximum**.
Setting it higher does not extend anything; it just fails.

Commit a `.env.example` listing the three names, gitignore the real
`.env`, and add a cheap sanity lane so a missing variable costs a second
instead of a ten-minute build:

```ruby
lane :check_asc do
  %w[ASC_KEY_ID ASC_ISSUER_ID ASC_KEY_PATH].each do |var|
    UI.user_error!("#{var} is not set — see fastlane/README.md") if ENV[var].to_s.empty?
  end
end
```

**Verify:** `git check-ignore fastlane/.env` matches, and `fastlane mac check_asc` fails with a named variable when one is unset.

*Source: fastlane — App Store Connect API key.*

## 3 — Regenerate the project before every build, if it is generated

If the `.xcodeproj` comes from a generator (xcodegen, Tuist) and is
gitignored, every build lane must regenerate it first. Otherwise the
lane builds whatever stale project happens to be on that machine — and
on a fresh CI checkout, nothing at all.

```ruby
def prepare_project
  sh("cd .. && xcodegen generate")
  number_of_commits(all: true)
end
```

Note the `cd ..`: fastlane runs `sh` with the `fastlane/` directory as
the working directory, which is a reliable source of "works locally,
fails in CI" if you assume the repo root.

The other half of this: **UI changes made in Xcode are lost** on the next
generation. Signing settings, capabilities and build phases belong in the
generator's manifest, not in the project file.

**Verify:** Delete the .xcodeproj, run the build lane, and it succeeds from scratch.

## 4 — Build with the two flags that decide whether it runs at all

```ruby
lane :build do
  build_number = prepare_project
  build_mac_app(
    project: "MyApp.xcodeproj",
    scheme: "MyApp",
    configuration: "Release",
    export_method: "app-store",
    output_directory: "build",
    clean: true,
    xcargs: "-skipPackagePluginValidation CURRENT_PROJECT_VERSION=#{build_number}"
  )
end
```

`build_mac_app` is `build_app` restricted to macOS. `export_method` for
the Mac App Store is **`app-store`**; `developer-id` is the other one you
might want, and it is for distribution *outside* the store — a different
signing identity and a different playbook.

**`-skipPackagePluginValidation`** is the flag that catches people out.
If any SwiftPM dependency ships a build plugin (SwiftLint, a syntax
highlighter, a code generator), `xcodebuild` refuses to run it
unattended and the lane dies with a message about validating plugins.
There is no interactive prompt to accept in CI, so the flag is not
optional — but understand that you are agreeing to run third-party code
at build time, so know which plugins you have.

Pass build settings through `xcargs`, not by editing the project.

**Verify:** The lane produces a signed artefact under `build/` on a machine that has never opened Xcode for this project.

*Source: fastlane — build_mac_app.*

## 5 — Derive the build number, never type it

App Store Connect rejects a build whose number is not higher than the
last one for that version — and the failure comes *after* the upload, so
a hand-maintained number wastes a full build and upload cycle.

`number_of_commits(all: true)` is monotonic, needs no state, and is the
same on every machine that has the full history. Feed it in via
`CURRENT_PROJECT_VERSION` so the project file stays untouched.

Two caveats worth knowing: a **shallow clone** (CI default) gives a
wrong, lower count — fetch full history in the workflow. And the count
only ever rises if you do not rewrite history on the release branch.

The alternative, `app_store_build_number` (which asks App Store Connect
for the current number), needs a network round trip and the API key;
the commit count does not.

**Verify:** Two builds from two commits produce two different, increasing build numbers with no file edited.

## 6 — Split the lanes, and stop before submitting

Three lanes, each doing one thing:

* `build` — artefact only, no network.
* `beta` — `build` + `upload_to_testflight`.
* `release` — `build` + `upload_to_app_store`, **without** submitting.

Keep `submit_for_review: false`. Automating the upload is a convenience;
automating the *submission* removes the last moment where a human looks
at what is about to reach customers. Release notes, screenshots and the
"what to test" note are usually the things that are wrong, and none of
them are caught by a build.

For the same reason `skip_metadata` and `skip_screenshots` default to
true on `release`: uploading a binary and rewriting the entire store
listing are separate decisions, and coupling them means one typo in a
description blocks a hotfix.

```ruby
lane :release do
  build
  upload_to_app_store(
    api_key: asc_api_key,
    skip_screenshots: true,
    skip_metadata: true,
    precheck_include_in_app_purchases: false,  # API key does not cover IAP precheck
    submit_for_review: false,
    force: true
  )
end
```

`force: true` suppresses the interactive confirmation — necessary
without a TTY, and the reason the "stop before submitting" rule matters.

**Verify:** `release` finishes with the build visible in App Store Connect and its status still awaiting your manual submission.

*Source: fastlane — upload_to_app_store (deliver) or fastlane — App Store Connect API key.*

## 7 — Keep store metadata in the repository, and dry-run it

`deliver` reads a directory tree: one folder per App Store locale, with
`description.txt`, `keywords.txt`, `release_notes.txt` and so on, plus
global files like `copyright.txt` and the category. Put it under version
control — store text is content that gets reviewed, and a diff is the
only way to see what changed.

Configure the paths once in a `Deliverfile` rather than repeating them:

```ruby
app_identifier   "com.example.myapp"
metadata_path    "./fastlane/metadata"
screenshots_path "./fastlane/screenshots"
automatic_release false
submit_for_review false
force true
```

Then a lane that uploads **only** metadata, so you can see the result
without touching a binary:

```ruby
lane :metadata_dry_run do
  upload_to_app_store(api_key: asc_api_key,
                      skip_binary_upload: true, skip_screenshots: true,
                      skip_metadata: false, submit_for_review: false,
                      force: true, run_precheck_before_submit: false)
end
```

Two warnings from experience: machine-translated locales need a human
pass before submission, and **placeholder URLs in metadata are a
rejection**. Grep for your own placeholder domain before every release.

**Verify:** `metadata_dry_run` completes and the changed text is visible in App Store Connect without a new build.

*Source: fastlane — upload_to_app_store (deliver).*

## 8 — Treat screenshots as an artefact with a producer

Screenshots are per-locale directories of PNGs at exact sizes. Two
things make them manageable:

* If the app's UI is one language, one screenshot set legitimately
  serves every store locale — mirror it with a small lane rather than
  maintaining seven identical folders by hand.
* Generate what you can deterministically. A snapshot test that renders
  a real view to a PNG (SwiftUI's `ImageRenderer`, for instance)
  produces a paywall or feature screenshot that never drifts from the
  actual UI, and regenerating it is a test run rather than a photo
  session.

Keep screenshot upload out of `release` (`skip_screenshots: true`) and
give it its own dry-run lane, for the same reason as metadata.

**Verify:** Regenerating screenshots is one command, and the result differs from the committed PNGs only when the UI actually changed.

## Pitfalls

- `ENV[]` instead of `ENV.fetch` for the key variables. A missing value becomes `nil` and surfaces as an unrelated error much later.
- `duration` above 1200. It is the documented maximum, not a suggestion.
- Forgetting `-skipPackagePluginValidation` when a dependency ships a build plugin. The lane dies on a prompt that cannot be answered in CI.
- A shallow CI clone with `number_of_commits`. The build number goes *down* and App Store Connect rejects the upload after it has been transferred.
- `submit_for_review: true`. The upload is the reversible part; the submission is not.
- Assuming `sh` runs at the repo root. It runs in `fastlane/`.
- Committing the `.p8` or the real `.env`. The key cannot be re-downloaded, only revoked and replaced.

## Acceptance

- Given A fresh checkout on a machine with the API key in the environment, when `bundle exec fastlane mac release` runs, then A signed build with a higher build number appears in App Store Connect, still unsubmitted, with no interactive prompt.
- Given A missing ASC_KEY_PATH, when `bundle exec fastlane mac check_asc` runs, then It fails within a second and names the missing variable.

## Sources

- [fastlane — App Store Connect API key](https://docs.fastlane.tools/app-store-connect-api/) — retrieved 2026-08-06
  key_id / issuer_id / key_filepath; duration maximum of 1200 seconds; in_house; which actions support the key — and that precheck does not support it for in-app purchases, pem not at all, produce only partly.
- [fastlane — build_mac_app](https://docs.fastlane.tools/actions/build_mac_app/) — retrieved 2026-08-06
  Alias of build_app restricted to macOS; export_method values include app-store, developer-id, mac-application and package; xcargs passes extra arguments to xcodebuild.
- [fastlane — upload_to_app_store (deliver)](https://docs.fastlane.tools/actions/upload_to_app_store/) — retrieved 2026-08-06
  Metadata/screenshot directory layout and the skip_* switches used by the dry-run lanes.

## In this project

<!-- Everything above is upstream and is replaced on re-expand; this
     section is yours and is kept. Fill in what is specific here. -->

- _Nothing project-specific yet._
