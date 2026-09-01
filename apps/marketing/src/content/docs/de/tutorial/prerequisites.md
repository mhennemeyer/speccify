---
title: Voraussetzungen
description: Alles installiert und eingerichtet, bevor die erste Zeile Code entsteht — von Xcode bis zum Apple-Developer-Konto.
sidebar:
  order: 2
---

Einmal einrichten; ab hier setzt das Tutorial alles davon voraus.

## Die Plattform

- **Ein Mac** mit aktuellem macOS. Eine praktische Warnung vorweg:
  Liegen Desktop/Dokumente in der iCloud-Synchronisierung, gehören
  Build-Produkte nicht in einen gesyncten Projektordner —
  Finder-Extended-Attributes auf einem `build/`-Verzeichnis können
  später `codesign` brechen. Wir lassen Build-Produkte in Xcodes
  DerivedData (`~/Library`); die Skripte des Tutorials tun das
  explizit.
- **Xcode** (App Store oder
  [developer.apple.com](https://developer.apple.com/xcode/)), einmal
  geöffnet, damit es seine Komponenten installiert, plus die Command
  Line Tools:

  ```sh
  xcode-select --install
  ```

## Versionskontrolle

- **Git** — kommt mit den Xcode Command Line Tools; prüfen mit
  `git --version`.
- **Ein GitHub-Konto** und die **`gh`-CLI**
  ([cli.github.com](https://cli.github.com)), authentifiziert:

  ```sh
  brew install gh
  gh auth login
  ```

  GitHub trägt das App-Repo und — später — dein eigenes Skills-Repo.
  Die `gh`-Credentials geben Speccify außerdem Zugriff auf private
  Skill-Quellen.

## Der Agent: Claude Code

[Claude Code](https://code.claude.com) installieren und
sicherstellen, dass `claude` im Terminal läuft. Jeder Agent, der
Projekt-Anweisungsdateien liest, funktioniert mit diesem Workflow;
die Transkripte des Tutorials verwenden Claude Code.

## Das Cockpit: die Speccify-App

Die **Speccify-App** (macOS oder Windows) installieren. Sie rendert
Board, Pläne, Skills und Aktionen des Projekts — alles, was der Agent
als Dateien unter `.agent/` pflegt — und führt die Aktionen des
Projekts selbst aus. Kein Konto, kein Server; sie liest dein
Repository. Die lokalen MCP-Server (Exec, Discovery) für gesandboxte
Drittclients bringt sie als Binaries mit — sonst ist nichts zu
installieren.

## Der Skill-Manager: die Speccify-CLI

Die **Speccify-CLI** installieren. Sie verwaltet Skill-*Quellen*,
expandiert Skills in Projekte und prüft Tool-Implementierungen gegen
ihre Verträge. Prüfen, dass sie antwortet:

```sh
speccify --help
```

## Projekt-Generierung: xcodegen

Wir klicken keine Xcode-Projekte zusammen; die Projektdatei wird aus
einer deklarativen `project.yml` *generiert* — diffbar, und der Agent
kann sie pflegen:

```sh
brew install xcodegen
```

## Shipping-Werkzeuge (gebraucht ab den Shipping-Kapiteln)

- **fastlane**, über Bundler, damit die Version im Repo gepinnt ist:

  ```sh
  brew install ruby   # oder System-Ruby ≥ 3
  gem install bundler
  ```

  Das `Gemfile` des Projekts pinnt fastlane; `bundle install`
  erledigt den Rest, wenn wir dort ankommen.
- **Eine Apple-Developer-Program-Mitgliedschaft**
  ([developer.apple.com/programs](https://developer.apple.com/programs/),
  99 USD/Jahr) — nötig für Signierung, TestFlight und den App Store.
  Die Registrierung kann einen Tag dauern; früh starten, damit sie
  steht, wenn die Shipping-Kapitel sie brauchen.

## Checkliste

```text
✓ Xcode + Command Line Tools     ✓ git + gh (authentifiziert)
✓ Claude Code (`claude`)         ✓ Speccify-App
✓ Speccify-CLI (`speccify --help`) ✓ xcodegen
✓ ruby + bundler (für fastlane)  ✓ Apple Developer Program (pending ist ok)
```

Alles grün? [Projekt anlegen.](/de/tutorial/project-setup/)
