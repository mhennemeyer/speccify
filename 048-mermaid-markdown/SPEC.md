---
station: Doing
order: 48
needs_human: true
ready: true
---

# Mermaid-Diagramme in Markdown anzeigen

## Why

In Windows 0.7 zeigt das Programm-Playbook in AVC/rekas seine Mermaid-Diagramme
nicht an. Der gemeinsame Markdown-Renderer stellt Codeblöcke bisher ausschließlich
als Text dar; Mermaid fehlt auf allen Plattformen.

## What

Mermaid-Codeblöcke im gemeinsamen Desktop-Markdown-Renderer lokal als Diagramme
darstellen. Normale Codeblöcke bleiben unverändert. Keine Änderung am Kundenprojekt,
keine externe Rendering-API, kein neuer Release-Tag ohne Nutzerauftrag.

## Acceptance

- Das konkrete Flowchart des gemeldeten Playbooks wird als lesbares SVG dargestellt.
- Mehrere Diagramme, Theme-Wechsel und Dokumentwechsel funktionieren ohne veraltete Ausgabe.
- Ungültige Diagramme zeigen einen Hinweis und ihren Quelltext; das Dokument bleibt lesbar.
- Der gebündelte Renderer braucht zum Anzeigen keine Internetverbindung und führt
  keine Diagramm-Callbacks aus. Normales Markdown/Code bleibt kompatibel.
- Chromium und die lokale gebündelte App sind geprüft; eine Windows-VM-Abnahme
  wird nur bei tatsächlicher Durchführung als bestanden dokumentiert.

## Decisions

1. 2026-09-16: Nutzerfehlermeldung autorisiert Untersuchung und Korrektur. Neue
   Spec, da die bisherigen Multi-Projekt-Specs zur Abnahme geparkt sind.
2. 2026-09-16: Mermaid 11 mit gebündelten Modulen; v12 setzt laut aktueller
   Dokumentation neuere Browser voraus. Strikter Rendering-Modus, keine Callback-Bindung.

## Tasks

- [x] Renderer mit Theme, Fehlerdarstellung und lokalem Bundle integrieren.
- [x] Diagramm aus betroffenem Playbook sowie Rendering-Regressionen prüfen.
- [x] Produktplaybooks nachführen und lokale App aktualisieren.
- [ ] Committen und pushen; Windows-CI mit Diagramm-Regression prüfen.

## Verification

Ausgangsbefund: `Markdown.tsx` nutzt nur react-markdown und remark-gfm;
Mermaid ist weder im Code noch in den App-Abhängigkeiten von 0.7 vorhanden.
Das gemeldete Playbook enthält einen Mermaid-Flowchart-Block. Nur lesend geprüft.

2026-09-16:

- Typecheck und Produktions-Frontend-Build grün; bekannte Chunk-Größenwarnung.
- `test_markdown_mermaid.mjs`: Flowchart mit Subgraph/mehrzeiligen Labels,
  Sequenzdiagramm, Syntaxfehler mit Quelltext, Theme-Wechsel, Navigation,
  eindeutige SVG-IDs, deaktivierte Callbacks und unveränderte Text-Codeblöcke grün.
  Externe Requests während dieser Tests blockiert; keine aufgetreten.
- Optionales lokales Reproduktionsdokument: das konkrete Programm-Playbook
  gerendert; kein Kundeninhalt in getrackte Testdaten übernommen.
- `test_playbook_drafts.mjs` und `test_handover.mjs` grün.
- Selbststartender Testserver (`--serve`) separat erfolgreich geprüft;
  Diagramm-Test in den Windows-CI-Job aufgenommen.
- Lokaler signierter Bundle-Build erfolgreich; `codesign --verify --deep --strict`
  erfolgreich. PID 68087, dieselben vier Fenster wieder offen, keine laufenden
  Terminals oder ungesicherten Entwürfe beendet. Kein App-Watcher.
- Native QA im tatsächlichen AVC-Workspace: Programm-Playbook ausgewählt,
  SVG-Geometrie und Beschriftungen geprüft, Datei-Hash unverändert. Ein zusätzlicher
  nativer Screenshot war wegen `screencapture: could not create image from rect`
  nicht verfügbar; DOM-Prüfung erfolgreich. Keine Windows-WebView2-Abnahme behauptet.
- Skill: `macos-notarize-tauri` für lokale Signaturprüfung; kein öffentlicher Release,
  keine neue Notarisierung oder Änderung der veröffentlichten Installer.

## Questions

Keine für die Korrektur; Windows-VM-Abnahme nach Bereitstellung eines Builds offen.
