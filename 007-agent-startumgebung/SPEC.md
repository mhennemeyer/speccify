---
station: Doing
order: 1
created: 2026-09-10
needs_human: true
ready: true
open_question: null
parent: null
---
# Agent mit einer nachvollziehbaren Startumgebung öffnen

## Why

Eine frische Installation darf nicht von zufälligen globalen CLI-Versionen
oder vom Start der App aus einem bereits eingerichteten Terminal abhängen.
Im überprüften Repo kennt die globale Speccify-CLI wesentliche Befehle nicht.
Die pnpm-Abfrage beim Kollegen zeigt zusätzlich eine Lücke beim ersten Setup.

## What

Ein gemeinsamer Diagnosevertrag für den Agent-Start: Projektwurzel, gewählter
Host, aufgelöstes Binary, Version/Fähigkeiten und nutzbare Speccify-Runtime.
Aufbauen auf vorhandenem Umgebungs-Doctor, Engine und Terminal. Für Entwickler
Repo-Runtime, für installierte Apps vorhandene Engine-/MCP-Wege ausdrücklich
unterscheiden. Fehlende Voraussetzungen erhalten einen konkreten nächsten Schritt.

`scripts/dev.sh` soll unterstützte Werkzeugversionen und pnpm-Buildfreigaben
reproduzierbar behandeln. Keine eigene Anmeldung, kein Modellwechsel und keine
automatische Änderung globaler Shell- oder Agent-Konfigurationen.

## Acceptance

- Wenn eine alte globale Speccify-CLI vor einer aktuellen Workspace-CLI liegt,
  zeigt die Diagnose den Unterschied und der dokumentierte Startweg bietet
  die für den Auftrag benötigten Befehle oder einen überprüften MCP-Ersatz.
- Wenn Codex fehlt oder nicht gestartet werden kann, erscheint der konkrete
  Fehler; die UI meldet keine erfolgreich gestartete Agent-Sitzung.
- Wenn die App aus Finder oder Terminal geöffnet wird, liefern Diagnose und
  tatsächlich gestartete Shell übereinstimmende Angaben zur Runtime.
- Wenn ein frischer Mac-Checkout eingerichtet wird, sind unterstützte Node-,
  pnpm-, Python- und Rust-Voraussetzungen nachvollziehbar; Buildskripte von
  Abhängigkeiten werden anhand einer ausdrücklichen Projektkonfiguration
  behandelt. Unbekannte Abhängigkeiten erhalten keine pauschale Freigabe.
- Wenn nur eine Shell gewünscht ist, bleibt dieser Modus nutzbar.

## Decisions

- D1 (2026-09-10): Diagnose und konkrete Fehlerbehandlung zuerst; bestehende
  Engine-/Host-Konfiguration weiterverwenden.
- D2 (2026-09-10): Das Terminal verwendet eine Login-Shell. Eine Diagnose nur
  gegen den Rust-Prozess-PATH reicht deshalb nicht als Nachweis.
- D3 (2026-09-10): Versionen bei Umsetzung an den tatsächlich unterstützten
  Werkzeugen prüfen und an einer Stelle festhalten.
- D4 (2026-09-10): Umsetzung freigegeben. Auswahl: Projekt-venv mit Speccify,
  installierte App-Engine, Shell-PATH. Diagnose führt nur bekannte Host-Probes
  (`--version`) und CLI-Hilfe aus, keine freien Autostart-Kommandos.
- D5 (2026-09-10): Die gewählte Runtime wird nach dem Laden der Shell-Profile
  vor den PATH gesetzt; Diagnose und Start teilen diese Vorbereitung.
- D6 (2026-09-10): Shell-, Workspace- und Engine-Prüfung sind native
  Desktop-Verträge in `agent_startup.rs`. Das Terminal verwendet das
  aufgelöste Binary für bekannte Hosts; freie Kommandos bleiben unverändert.
  Eine bestandene Versionsprüfung bedeutet weder Login noch erfolgreiche
  Wiederaufnahme. Die Aktivität meldet daher lediglich „Terminal geöffnet“.
- D7 (2026-09-10): pnpm 10.33.3 steht zentral in `packageManager`; alle
  CI-/Release-Jobs lesen diesen Wert. Node-Minimum 22.12.0 entspricht den
  installierten Astro-/Vite-Anforderungen. `strictDepBuilds` und die Allowlist
  für esbuild/sharp verhindern eine pauschale Freigabe weiterer Buildskripte.
- D8 (2026-09-10): Die asynchrone Startprüfung erfordert Listener vor dem
  Öffnen sowie Cleanup eines verspätet geöffneten Terminals. Dieser Teil von
  Befund F7 ist damit vorgezogen; UTF-8 und genaue Sitzungsidentität bleiben 009.

## Tasks

- [x] Runtime-Auswahl für Repo und installierte App als Vertrag festlegen.
- [x] Umgebungsdiagnose um projektbezogene Fähigkeiten und Fehler ergänzen.
- [x] Startweg und Diagnose an denselben Auswahlregeln ausrichten.
- [x] Entwickler-Setup und pnpm-Freigaben reproduzierbar machen und dokumentieren.
- [x] Fehlende/veraltete CLI sowie minimale und vorbereitete Start-PATHs automatisiert prüfen.

## Verification

Ausgangsbefunde F1 in [006](../006-bestandsaufnahme-agent-terminal/SPEC.md),
`scripts/dev.sh`, `terminal.rs`, `system_cmd.rs`, `engine.rs`,
`toolbox_cmd.rs` und `pnpm-workspace.yaml`.

- `cargo test -p speccify-desktop -- --nocapture`: 59 bestanden, einer
  weiterhin explizit ignoriert. Vier neue Starttests: fehlender Host/alte CLI,
  freie Kommandos, Runtime-Priorität und echter zsh-Profil-Lauf mit minimalem
  bzw. vorbereitetem PATH. Letzterer verwendet isolierte Profile und Pfade
  mit Leerzeichen, Apostroph und Dollarzeichen.
- `cargo fmt --check`: grün.
- `pnpm --filter speccify-desktop typecheck`: grün.
- `pnpm --filter speccify-desktop build`: grün; vorhandener Hinweis zur
  Bundle-Größe über 500 kB, kein Buildfehler.
- `bash -n scripts/dev.sh` und `./scripts/dev.sh --check`: grün; der Check
  installiert keine Abhängigkeiten und baut keine Sidecars.
- Frischer temporärer Workspace mit den Repository-Manifests und Lockfile:
  `pnpm install --frozen-lockfile` erfolgreich mit pnpm 10.33.3; die
  Installationsskripte von esbuild und sharp liefen ohne Rückfrage.
  Anschließend echte TypeScript-Transformation über Vite/esbuild und
  PNG-Encoding mit sharp erfolgreich.
- Der vorherige Offline-Versuch hatte keinen vollständigen Store zur
  Verfügung. Die eigentliche Prüfung erfolgte im temporären Workspace mit
  freigegebenem Cache-/Netzzugriff. Die bestehende `node_modules`-Installation
  des Projekts wurde nicht ersetzt.
- CI-Konfiguration: alle pnpm/action-setup-Schritte verwenden den zentralen
  packageManager-Wert; `git diff --check` grün.

Bereit zur menschlichen App-Abnahme, deshalb `Doing` mit `ready: true`.
Noch nicht live geprüft: Start per Finder im echten Projektfenster,
PowerShell/Windows und ein zweiter Mac. Die PATH-Tests simulieren die beiden
Startumgebungen, ersetzen aber keinen GUI-/Login-Nachweis. Keine vollständige
Praxisabnahme nach Spec 012 behauptet.

## Questions

Abnahme im echten Fenster: unter Agent „Startumgebung prüfen“, danach Codex
starten und die Runtime im Terminal aufklappen; zusätzlich „Nur Shell“ prüfen.
Auf einem zweiten Mac zuerst `./scripts/dev.sh --check` und anschließend das
Setup ausführen. Rückmeldungen gehören zu dieser Spec.
