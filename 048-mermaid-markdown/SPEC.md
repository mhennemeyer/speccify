---
station: Doing
order: 48
needs_human: true
ready: false
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

- [ ] Renderer mit Theme, Fehlerdarstellung und lokalem Bundle integrieren.
- [ ] Diagramm aus betroffenem Playbook sowie Rendering-Regressionen prüfen.
- [ ] Produktplaybooks nachführen, lokale App aktualisieren, committen und pushen.

## Verification

Ausgangsbefund: `Markdown.tsx` nutzt nur react-markdown und remark-gfm;
Mermaid ist weder im Code noch in den App-Abhängigkeiten von 0.7 vorhanden.
Das gemeldete Playbook enthält einen Mermaid-Flowchart-Block. Nur lesend geprüft.

## Questions

Keine für die Korrektur; Windows-VM-Abnahme nach Bereitstellung eines Builds offen.
