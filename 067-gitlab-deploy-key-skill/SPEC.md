---
station: Doing
order: 67
created: 2026-09-22
modules: agent-knowledge
---
# Skill und Tool: Nur-Lese-Deploy-Key in GitLab hinterlegen

## Why

BO 2026-09-22: Die Frage Q1 zu Spec 008 (AVC/rekas) verlangt, einen auf der VM
erzeugten öffentlichen Schlüssel als Deploy Key in drei GitLab-Projekten zu
hinterlegen. Token (`GITLAB_TOKEN`, Scope `api`) und Rechte (Owner) sind da,
aber der Weg war ein Ad-hoc-`curl`, und das Anlegen ist eine Rechtevergabe,
die der Auto-Modus blockiert. Gewünscht: ein benannter, prüfbarer Weg als
Skill mit Tool nach dem Speccify-Modell, damit die Freigabe an einer klaren
Stelle fällt.

## What

- `.agent/tools/gitlab-deploy-key/TOOL.md`: Vertrag (Eingaben Host, Projekte,
  Titel, Schlüssel, `can_push`, `mode` plan|check|apply; Ausgaben je Projekt;
  Effekte; Anforderungen `GITLAB_TOKEN`, python3) mit offline prüfbaren
  Beispielen; Implementierung `macos.py` und `linux.py` (identisch).
- `.agent/skills/gitlab-deploy-key/SKILL.md`: Ablauf Schlüssel entgegennehmen →
  `check` → Freigabe des Menschen → `apply` → Nachweis (Liste, `git ls-remote`
  von der VM), Fallstricke, `## In this project` mit Host und Projekten.
- Modulkatalog um `agent-knowledge` (Skills, Tools, Playbooks unter `.agent/`).
- `speccify tool check gitlab-deploy-key` grün; Status in `expansions.yaml`
  schreibt das Werkzeug.
- Außerhalb: Ausführen von `apply` (braucht BOs Freigabe), Windows-Implementierung,
  ein allgemeines GitLab-MCP.

## Acceptance

- Wenn `speccify tool check gitlab-deploy-key` läuft, dann bestehen alle
  Beispiele ohne Netzwerk und `speccify verify` nennt das Tool nicht als fehlend.
- Wenn `mode: check` mit gesetztem Token läuft, dann meldet das Tool Nutzer,
  Token-Scope, Zugriffsstufe je Projekt und ob der Schlüssel schon hinterlegt ist,
  ohne etwas zu ändern.
- Wenn `mode: apply` läuft, dann existiert der Schlüssel danach nur lesend in
  allen genannten Projekten (einmal angelegt, sonst aktiviert), und die Ausgabe
  belegt es je Projekt.
- Wenn der Token fehlt oder der Schlüssel kein gültiger öffentlicher Schlüssel
  ist, dann bricht das Tool mit klarer Meldung ab, bevor es die API berührt.

## Decisions

1. 2026-09-22: Python statt Shell — JSON, HTTPS und Fehlerbehandlung ohne
   Zusatzwerkzeuge; `macos.py` und `linux.py` sind dieselbe Datei.
2. 2026-09-22: Dreistufig: `plan` (nur Eingaben prüfen, für `tool check`),
   `check` (nur lesen), `apply` (schreiben). Der Skill verlangt vor `apply`
   die ausdrückliche Freigabe des Menschen; das Tool selbst verweigert nichts.
3. 2026-09-22: Token nur aus der Umgebung (`GITLAB_TOKEN`), nie aus der Eingabe
   und nie in der Ausgabe.

## Tasks

- [ ] `TOOL.md` mit Schema, Verhalten und Beispielen (plan ok, plan mit
      ungültigem Schlüssel, plan ohne Projekte).
- [ ] `macos.py`/`linux.py`: plan/check/apply gegen GitLab API v4.
- [ ] `SKILL.md` mit Ablauf, Verify-Zeilen, Fallstricken, Projektabschnitt.
- [ ] Katalog `agent-knowledge`; `speccify tool check`, `speccify verify`.
- [ ] `mode: check` gegen git.itsd-consulting.de ausführen (lesend) und Befund notieren.

## Verification

Noch nichts ausgeführt.

## Questions
