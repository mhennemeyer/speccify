---
title: fastlane & App Store Connect
description: "Screenshots, Builds und App-Store-Connect-Metadaten — automatisiert, versioniert, im Repo."
sidebar:
  order: 9
  badge:
    text: in Arbeit
    variant: caution
---

Ticket n12 baut die Release-Maschinerie auf: Alles, was App Store
Connect braucht — Screenshots, Metadaten, Builds — wird eine Datei im
Repo oder eine Lane, die eine erzeugt. Das folgende Setup existiert in
4Notice wie beschrieben; der erste vollständige Screenshot-Lauf und
der erste Upload stehen noch aus ([wo die Spur
endet](#wo-die-spur-endet)).

## 1. fastlane mit Bundler pinnen

fastlanes Verhalten ändert sich zwischen Versionen, also ist die
Version ein Repo-Fakt, kein Maschinen-Fakt:

```ruby
# Gemfile
source "https://rubygems.org"
gem "fastlane", "~> 2.236"
```

Einmal `bundle install`, danach läuft jeder Aufruf als `bundle exec
fastlane <lane>` — dieselbe Version auf jeder Maschine und in jedem
Agent-Lauf.

## 2. Zugangsdaten bleiben in der Umgebung

Die Regel des [Board-Workflows](/de/app/board/) — niemals
Secrets in Repo-Dateien — greift hier mit voller Härte, denn fastlane
braucht einen App-Store-Connect-API-Key. Das Fastfile liest ihn
ausschließlich aus der Umgebung:

```ruby
def asc_api_key
  app_store_connect_api_key(
    key_id: ENV.fetch("ASC_KEY_ID"),
    issuer_id: ENV.fetch("ASC_ISSUER_ID"),
    key_filepath: ENV.fetch("ASC_KEY_PATH"),  # .p8 außerhalb des Repos
    ...
  )
end
```

Eine `check_asc`-Lane schlägt früh fehl und nennt die fehlende
Variable; `.env` ist gitignored. Das `Appfile` enthält nur die zwei
ohnehin öffentlichen Werte: Bundle-Identifier und Team-ID.

## 3. Screenshots sind ein UI-Test

`fastlane snapshot` fährt die Screenshot-Matrix — in 4Notice: zwei
Geräte × sieben Sprachen, einmal deklariert im `Snapfile`:

```ruby
devices(["iPhone 17", "iPad Pro 13-inch (M5)"])
languages(["en-US", "de-DE", "fr-FR", "es-ES", "it", "ja", "zh-Hans"])
launch_arguments(["-uitest -uitest-reset -uitest-demo"])
```

Zwei Entscheidungen machen das tragfähig:

- **Demo-Inhalte werden im Code gesät.** Das Startargument
  `-uitest-demo` füllt die vier Zettel mit Beispieltext — und der
  Beispieltext liegt im selben [String-Katalog](/de/tutorial/i18n/)
  wie die UI (`demo.*`-Keys). Eine Seeding-Funktion, und die
  Screenshots jeder Sprache zeigen übersetzte Zettel.
- **Die Aufnahmen sind ein gewöhnlicher XCUITest.**
  `ScreenshotUITests` wischt durch die Zettel und ruft je Motiv
  `snapshot("01-yellow")`. fastlane wiederholt das pro Gerät und
  Sprache.

Der Lauf ist als [Projekt-Action](/de/app/actions/)
registriert und damit vom Board aus startbar — mit den Kosten in der
Beschreibung: Die volle Matrix dauert rund 30 Minuten.

## 4. Metadaten sind Dateien, je Sprache

Der Store-Eintrag wird nicht in ein Webformular getippt. Er liegt in
`fastlane/metadata/<lang>/` — `name.txt`, `subtitle.txt`,
`description.txt`, `keywords.txt`, `release_notes.txt` — für alle
sieben Sprachen, versioniert wie jede andere Quelle. Felder, deren
echte Werte noch fehlen (`support_url`, `privacy_url`), werden leer
committet statt mit Platzhaltern gefüllt. Eine
`metadata_dry_run`-Lane lädt nur die Metadaten hoch (`deliver` mit
`skip_binary_upload`) — so lässt sich der Eintrag iterieren, ohne
etwas zu bauen.

## 5. Build- und Upload-Lanes

Eine Lane pro Plattform, gleiche Form: Xcode-Projekt neu erzeugen,
archivieren, hochladen.

```ruby
lane :beta do
  check_asc
  sh("cd .. && xcodegen generate --quiet")
  build_app(scheme: "FourNotice-iOS", export_method: "app-store", ...)
  upload_to_testflight(...)
end
```

Vor jedem Upload läuft der [importierte
release-checks-Skill](/de/tutorial/importing-skills/) — Plist-Keys,
Entitlements, verwaiste Strings — dieselben drei Verträge, die seit
dem Import jedes Ticket absichern.

## Wo die Spur endet

Das ist zum Zeitpunkt dieses Textes der praktizierte Stand: Die
Lanes, der Test und die Metadaten-Dateien existieren und sind die
oben zitierten. Die erste vollständige Screenshot-Matrix, der
App-Store-Connect-Eintrag und der erste TestFlight-Upload sind noch
nicht gelaufen — dieses Kapitel geht weiter, und das
[Submission-Kapitel](/de/tutorial/submission/) beginnt, sobald sie es
sind.
