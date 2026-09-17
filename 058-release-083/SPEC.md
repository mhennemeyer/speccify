---
station: Doing
order: 58
created: 2026-09-17
needs_human: false
---
# Speccify 0.8.3 veröffentlichen und Abläufe als Skills festhalten

## Why

Schlägt „Installieren und neu starten“ fehl, stand die Fehlermeldung unter dem
Knopf im scrollenden Update-Dialog und war bei langen Release-Notizen oder
kleinem Fenster nicht sichtbar. Der Fix (`01beefa`) soll als Update ankommen.
Außerdem existieren wiederkehrende Abläufe (Release, Prüfstand, lokale App
aktualisieren) bisher nur verstreut in `docs/release.md`, Playbooks und
früheren Release-Specs.

## What

- Release 0.8.3 mit dem Update-Dialog-Fix; Website-Notizen, signierter Feed.
- Wiederkehrende Abläufe als Projekt-Skills unter `.agent/skills/`.
- Außerhalb: neue Funktionen, 0.9.0/itsdcloud, Windows-/Linux-Praxisabnahme.

## Acceptance

- Wenn die Installation blockiert wird, dann ist die Fehlermeldung ohne
  Scrollen im Dialog sichtbar (Browserprüfung bei kleinem Fenster).
- Wenn der Tag `v0.8.3` gebaut ist, dann sind alle vier Plattform-Jobs und die
  Manifest-Prüfung grün, das Release veröffentlicht und `latest.json` öffentlich.
- Wenn ein Agent „Release erstellen“ o. Ä. hört, dann findet er unter
  `.agent/skills/` einen vollständigen, geprüften Ablauf.

## Decisions

1. 2026-09-17: Nutzer autorisiert im Chat „als 0.8.3 veröffentlichen“ — das ist
   der Zuruf für den Tag.
2. 2026-09-17: Skills verweisen auf `docs/release.md` für Einrichtung und
   Hintergründe, statt es zu duplizieren; der Skill hält den Ablauf und die
   in 049–057 gelernten Fallstricke.

## Tasks

- [x] Fix Update-Dialog (`01beefa`), Typecheck und Browserprüfung.
- [ ] Version, Release-Notizen, Playbooks; volle Prüfläufe.
- [ ] Commit/Push, CI grün, Tag, Release-Workflow und Paketprüfung.
- [ ] Veröffentlichen, Feed/Website prüfen, lokale App aktualisieren.
- [ ] Abläufe als Skills anlegen und gegen diesen Release-Lauf prüfen.

## Verification

## Questions

Keine.
