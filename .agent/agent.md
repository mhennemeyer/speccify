# Speccify project guidance

Sprache mit dem Nutzer: Deutsch, Ansprache „Du“. Produkttexte und öffentliche
Dokumentation sind Englisch, sofern der jeweilige Bestand nichts anderes
vorgibt.

## Produkt

Speccify ist ein agentenagnostischer Skill- und Tool-Manager für macOS und
Windows. Wiederverwendbares Wissen wird als `SKILL.md` über Git geteilt.
Plattformabhängige Werkzeuge werden nicht als fertige Skripte vorausgesetzt,
sondern durch `TOOL.md` spezifiziert und im Zielprojekt für die jeweilige
Plattform implementiert und geprüft.

Die Arbeit läuft über Specs unter `.agent/specs/` (Board Backlog / Doing /
Done, Tasks als Checkboxen; die Policy dazu liegt als Vorlage in
`apps/desktop/src-tauri/templates/workflow-policy.md` und kommt per
Einrichten-Knopf in die `agent.md` eines Projekts);
das Skill-und-Tool-Modell steht in `.agent/specs/skills-und-tools/SPEC.md`,
das Projektfenster im Archiv unter `.agent/specs/archive/`.
Beide sind auf ausdrücklichen BO-Entscheid parallel aktiv.

## Kanonische Projektstruktur

- `.agent/skills/<name>/SKILL.md`: normale, projektspezifische Skills.
- `.agent/tools/<name>/TOOL.md`: Tool-Vertrag; Implementierungen daneben als
  `<platform>.<ext>`.
- `.agent/speccify/expansions.yaml`: Herkunft, Hashes und Prüfstatus.
- `.agent/specs/<slug>/SPEC.md`: **eine Arbeitseinheit** (Spec) mit
  Stationen Backlog / Doing / Done und Tasks als Checkboxen; Fertiges
  unter `.agent/specs/archive/`. Ersetzt seit 2026-09-09 Pläne und Tickets
  (Spec `spec-workflow`); die alten Pläne liegen konvertiert im Archiv.
- `.agent/playbooks/`: stehende Anleitungen (Release, Deploy, …) — anders
  als Specs werden sie nicht abgearbeitet, sondern wiederverwendet.
- `.agent/actions.json`: benannte Projektaktionen.

Agent-spezifische Ordner sind nur Adapter: `.claude/skills` und
`.agents/skills` zeigen beide auf `.agent/skills`. Bearbeite Skills immer an
der kanonischen Stelle.

## Architektur

- `core/`: Python-Domänenlogik für Skills, Quellen, Lockfiles, Expansion und
  Tool-Prüfung.
- `cli/`: dünner Typer-Adapter über den Core.
- `mcp/`: dünner MCP-Adapter über denselben Core.
- `crates/`: Rust-MCPs für Exec, Discovery, Parallels und Toolbox.
- `apps/desktop/`: React/Tauri-2-App für macOS und Windows.
- `apps/marketing/`: öffentliche Website und Dokumentation.

CLI, MCP und Desktop dürfen keine parallelen Domänenmodelle erfinden. Neue
Funktionalität gehört zuerst in den Core oder in einen klaren, nativen
Desktop-Vertrag; Adapter bleiben klein.

## Arbeitsregeln

- Bestehende Nutzeränderungen nicht überschreiben oder zurücksetzen.
- Für Textänderungen die Editier-Werkzeuge des jeweiligen Hosts verwenden
  (Codex: `apply_patch`; Claude Code: Edit/Write) — keine sed/awk-Umbauten.
- Python: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`.
- Desktop-Frontend: `pnpm --filter speccify-desktop typecheck`.
- Desktop-Rust: `cargo test -p speccify-desktop` und `cargo fmt --check`.
- Gezielte Tests zuerst, breitere Checks nach erfolgreichem Kernpfad.
- Keine Secrets in `.mcp.json`, `.codex/config.toml`, `.agent/settings.json`
  oder andere getrackte Projektdateien schreiben.
- Committen ist in diesem Repo ausdrücklich erlaubt (BO, 2026-08-31:
  „committe gern selbst in diesem Projekt") — in sich abgeschlossene
  Conventional Commits mit Verifikationsstand. **Pushen** ebenfalls
  erlaubt (BO, 2026-09-06: „Mach commits und push gern selbst") — nach
  grünem Verifikationsstand; ein Push auf `main` deployt die Website
  (pages.yml), Tags lösen den Release-Workflow aus und bleiben BO-Zuruf.

## Skills und Tools

Lies einen passenden Skill vollständig, bevor Du ihn benutzt. `TOOL.md` ist
der Vertrag: Eingaben, Ausgaben, Effekte, Anforderungen und Beispiele müssen
vor einer Implementierung verstanden sein. Prüfe Implementierungen mit
`speccify tool check <name>`; ändere den Status in `expansions.yaml` nie von
Hand. `speccify verify` prüft Lock-, Bundle-, Expansions- und Tool-Drift.
