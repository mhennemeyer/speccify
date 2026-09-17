---
station: Done
order: 59
created: 2026-09-17
needs_human: false
---
# Erneute Update-Suche nach einem Download findet neuere Versionen

## Why

BO-Befund 2026-09-17: Eine Installation hatte 0.8.2 gefunden; nach der
Veröffentlichung von 0.8.3 blieb „erneut suchen“ bei 0.8.2. Der öffentliche
Feed lieferte zu diesem Zeitpunkt nachweislich 0.8.3.

## What

Ursache im nativen Koordinator (`updates.rs`): Mit einem fertigen Download
(`bytes` gesetzt) kehrte `update_check` still zurück, die automatische Suche
pausierte, und der Dialog deaktivierte „Jetzt suchen“ in der Phase `ready`.
Ein geladenes Update verdeckte jede neuere Version bis zum App-Neustart.

- Suche ist auch mit fertigem Download möglich (manuell und im Intervall).
- Gleiche Version im Feed: Download bleibt installierbar. Andere Version:
  veralteter Download wird verworfen, die neue Version wird angeboten.
  Suchfehler: Download bleibt installierbar, Fehler wird angezeigt.
- Außerhalb: Release; bereits verteilte 0.8.1–0.8.3 behalten das Verhalten.

## Acceptance

- Wenn ein Update geladen ist und der Feed eine neuere Version nennt, dann zeigt
  eine erneute Suche diese Version und bietet deren Download an.
- Wenn der Feed unverändert oder nicht erreichbar ist, dann bleibt der geprüfte
  Download installierbar.

## Decisions

1. 2026-09-17: Ein Download einer überholten Version wird verworfen statt
   parallel gehalten: angeboten wird immer genau der aktuelle Feed-Stand.
2. 2026-09-17: Kein eigenes Release ohne BO-Zuruf. Umgehung für verteilte
   Versionen: App neu starten (verwirft den Download im Arbeitsspeicher) und
   erneut suchen, oder das geladene Update installieren und danach suchen.

## Tasks

- [x] Ursache belegen (Feed geprüft, Koordinator gelesen).
- [x] `apply_check` im Koordinator, Intervall-Suche ohne Download-Sperre.
- [x] Dialog: „Jetzt suchen“ in `ready` aktiv; Fixture bildet das Verhalten ab.
- [x] Rust-Test und Browser-Regression; Doku und Stand-Playbook.

## Verification

Feed 2026-09-17: `releases/latest/download/latest.json` → v0.8.3, Version 0.8.3.
Rust-Test mit echtem Tauri-Updater gegen lokalen Server: gleiche Version →
`ready` mit Download; Fehler → `ready` mit Fehlertext; Feed 1000.0.0 →
`available`, Download verworfen; danach Fehler → `error`. Desktop-Rust 134
bestanden/3 ignoriert, Cargo fmt, TypeScript grün. `scripts/test_updates.mjs`
besteht; gegen den alten Dialog scheitert es am deaktivierten „Jetzt suchen“.
Nicht nachgewiesen: Verhalten in einer gebauten App gegen den öffentlichen Feed
(erst mit dem nächsten Release möglich).

## Questions

Keine.
