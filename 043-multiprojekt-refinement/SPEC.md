---
station: Doing
order: 43
needs_human: true
ready: false
---

# Multi-Projekt-Refinement und Web-App-Recherche

## Why

Gemischte Workspace-Ordner enthalten Repos, normale Ordner und Root-Dateien.
Die tägliche Arbeit braucht gemeinsame Wissenslisten und ein gemeinsames Board,
während Dateien und Git ihre konkreten Ziele behalten. Eine mögliche Web-App
soll zunächst recherchiert werden, ohne den Entwicklungsflow vorwegzunehmen.

## What

Den Nutzerauftrag vom 2026-09-16 gegen den Bestand prüfen, umsetzbare
Folgespecs schneiden und die Web-App-Recherche als unverbindlichen
Playbook-Draft ablegen. Den Draft-Vertrag für dieses Repo dokumentieren.
Keine Desktop-Implementierung, keine Kundenrepo-Migration, kein Serverbetrieb
und keine Veröffentlichung eines neuen Releases in diesem Refinement.

## Acceptance

- Der Befund erklärt, warum normale Root-Inhalte im gemischten Workspace fehlen.
- Root-Dateien, gemeinsame Wissensansichten, Multi-Repo-Register und Playbook-Drafts
  haben konkrete Folgespecs mit überprüfbaren Akzeptanzfällen.
- Bestehende gemeinsame Boards und Multi-Repo-Web-Board-Fähigkeiten werden von
  tatsächlichen Lücken unterschieden; vorhandene Verträge werden weiterverwendet.
- Der Web-App-Draft nennt Primärquellen mit Prüfdatum, Anmeldewege, Grenzen,
  Architekturvorschläge und einen möglichen Nachweis ohne Umsetzungsfreigabe.
- Der Draft bleibt ausdrücklich unverbindlich; aktive Playbooks stellen
  geplante Funktionen nicht als bereits implementiert dar.

## Decisions

1. 2026-09-16: Auftrag als Refinement ausgearbeitet; Desktop-Umsetzung in
   separaten Backlog-Specs. Die optionale Rückfrage nach sofortiger Umsetzung
   ist keine notwendige Freigabe für die beauftragte Recherche.
2. 2026-09-16: Toyota strukturell gelesen. `Resourcen` ist ein gewöhnlicher
   Root-Unterordner neben Repos und Root-Dateien; private Dateiinhalte und
   Remote-Adressen werden für die Recherche nicht benötigt.
3. 2026-09-16: Keine neue zentrale Spec-Datenbank voraussetzen. Ausgangspunkt
   bleiben die kanonischen Register-Branches aus 028 und die Aggregation 026/032.
4. 2026-09-16: `status: draft` ist eine Inhaltsmarkierung, keine Board-Station
   und kein ungespeicherter Editorzustand. Repo-Guidance gilt sofort;
   die native App-Unterstützung bleibt eine eigene Umsetzung.

## Tasks

- [x] Workspace-Erkennung, Wissensnavigation, Register und Playbooks prüfen.
- [x] Folgespecs 044–047 mit Zielbindung und Fehlerfällen ausarbeiten.
- [x] Offizielle Codex-/Claude-Quellen und lokale Codex-CLI-Hilfe prüfen.
- [x] Web-App-Research als Playbook-Draft mit nichtbindendem Status ablegen.
- [x] Produktvision, Bestandsbuch und Repo-Draft-Regel aktualisieren.
- [ ] Dokumente und Befunde verifizieren, Änderungen synchronisieren.

## Verification

Quellcodebasis `a6a90b1`; lokale gebündelte App läuft mit PID 92597.
Keine Implementierungsänderungen und kein Neustart erforderlich.

- `workspace_cmd.rs`: normale Ordner ohne Git-/Projektmarker fehlen als
  eigenständige Ziele; Root-Fallback nur bei leerer Projektmenge.
- `WorkspaceShell.tsx`: gemeinsames Spec-Board vorhanden; Wissensbereiche
  weiterhin im Kontext einzelner Worktrees.
- `Source.specs_dirs`: Root-Register bewirkt frühe Rückgabe vor Kind-Registern.
  Mit der echten `Source`-/`RepoConfig`-Implementierung und temporären Ordnern
  reproduziert: zunächst `workspace/repo-a`, nach Anlegen eines leeren
  `.agent/specs` am Root ausschließlich `workspace`. Keine Remotes beteiligt.
- `playbook_cmd.rs` / `PlaybooksTab.tsx`: kein fachliches Draft-Feld im Vertrag.
- Quellen und Gültigkeitsgrenzen stehen im [Research-Draft](../../playbooks/speccify-web-app.md).
  Kein praktischer Browser-/Server-Login getestet.
- Neun Dokumente: lokale Markdown-Links, geschlossene Codeblöcke, YAML-Frontmatter
  und Pflichtabschnitte der Specs geprüft; `git diff --check` grün.
  Keine Code-Tests nötig, da ausschließlich Refinement/Dokumentation geändert.

Folgespecs: [044](../044-workspace-root-dateien/SPEC.md),
[045](../045-workspace-wissenskatalog/SPEC.md),
[046](../046-multi-repo-register/SPEC.md),
[047](../047-playbook-drafts/SPEC.md).

## Questions

Keine offene Frage blockiert dieses Refinement. Produktentscheidungen zur
Web-App verbleiben im Draft; sie starten keine Implementierung.
