---
title: 'fastlane & App Store Connect'
description: "Screenshots, builds, and App Store Connect metadata — automated, versioned, in the repo."
sidebar:
  order: 9
  badge:
    text: in progress
    variant: caution
---

Ticket n12 sets up the release machinery: everything App Store Connect
needs — screenshots, metadata, builds — becomes a file in the repo or
a lane that produces one. The setup below exists in 4Notice as
written; the first full screenshot run and the first upload are still
ahead ([where the trail ends](#where-the-trail-ends)).

## 1. Pin fastlane with Bundler

fastlane's behavior changes between versions, so the version is a
repo fact, not a machine fact:

```ruby
# Gemfile
source "https://rubygems.org"
gem "fastlane", "~> 2.236"
```

`bundle install` once, then every invocation is `bundle exec fastlane
<lane>` — the same version for every machine and every agent run.

## 2. Credentials stay in the environment

The [board workflow's rule](/app/specs/) — never put secrets in
repo files — applies with force here, because fastlane needs an App
Store Connect API key. The Fastfile reads it exclusively from the
environment:

```ruby
def asc_api_key
  app_store_connect_api_key(
    key_id: ENV.fetch("ASC_KEY_ID"),
    issuer_id: ENV.fetch("ASC_ISSUER_ID"),
    key_filepath: ENV.fetch("ASC_KEY_PATH"),  # .p8 outside the repo
    ...
  )
end
```

A `check_asc` lane fails early with the name of the missing variable,
and `.env` is gitignored. The `Appfile` holds only the two values that
are public anyway: bundle identifier and team ID.

## 3. Screenshots are a UI test

`fastlane snapshot` drives the screenshot matrix — in 4Notice: two
devices × seven languages, declared once in the `Snapfile`:

```ruby
devices(["iPhone 17", "iPad Pro 13-inch (M5)"])
languages(["en-US", "de-DE", "fr-FR", "es-ES", "it", "ja", "zh-Hans"])
launch_arguments(["-uitest -uitest-reset -uitest-demo"])
```

Two decisions make this work:

- **Demo content is seeded in code.** The launch argument
  `-uitest-demo` fills the four notes with sample text — and the
  sample text lives in the same [string catalog](/tutorial/i18n/) as
  the UI (`demo.*` keys). One seeding function, and every language's
  screenshots show translated notes.
- **The shots are a plain XCUITest.** `ScreenshotUITests` swipes
  through the notes and calls `snapshot("01-yellow")` per motif.
  fastlane repeats it per device and language.

The run is registered as a [project action](/app/actions/) so
it can be started from the board — with its cost stated in the
description: the full matrix takes about 30 minutes.

## 4. Metadata is files, per language

The store listing is not typed into a web form. It lives in
`fastlane/metadata/<lang>/` — `name.txt`, `subtitle.txt`,
`description.txt`, `keywords.txt`, `release_notes.txt` — for all seven
languages, versioned like any other source. Fields whose real values
don't exist yet (`support_url`, `privacy_url`) are committed empty
rather than filled with placeholders. A `metadata_dry_run` lane
pushes metadata alone (`deliver` with `skip_binary_upload`), so the
listing can be iterated without building anything.

## 5. Build and upload lanes

One lane per platform, same shape: regenerate the Xcode project,
archive, upload.

```ruby
lane :beta do
  check_asc
  sh("cd .. && xcodegen generate --quiet")
  build_app(scheme: "FourNotice-iOS", export_method: "app-store", ...)
  upload_to_testflight(...)
end
```

Before any upload, the [imported release-checks
skill](/tutorial/importing-skills/) runs — plist keys, entitlements,
orphan strings — the same three contracts that gated every ticket
since.

## Where the trail ends

As of this writing, that is the practiced state: the lanes,
the test, the metadata files exist and are the ones quoted above. The
first complete screenshot matrix, the App Store Connect app record and
the first TestFlight upload have not run yet — this chapter continues,
and the [submission chapter](/tutorial/submission/) begins, once they
have.
