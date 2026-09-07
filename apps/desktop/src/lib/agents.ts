export interface AgentPreset {
  id: "claude" | "codex" | "shell";
  label: string;
  command: string;
}

const windows = navigator.userAgent.includes("Windows");

/** Host presets are conveniences, never the source of project data. */
export const AGENT_PRESETS: AgentPreset[] = [
  { id: "claude", label: "Claude", command: windows ? "claude.cmd" : "claude" },
  { id: "codex", label: "Codex", command: windows ? "codex.cmd" : "codex" },
  { id: "shell", label: "Nur Shell", command: "" },
];

/** Preserve the established default; every project can switch with one click. */
export const DEFAULT_AGENT_COMMAND = AGENT_PRESETS[0].command;

/** Dieselbe Sitzung wieder aufnehmen (Dogfooding, BO 2026-09-07): Claude
 *  Code und Codex schreiben ihr Protokoll fortlaufend auf Platte — nach
 *  einem App-Neustart holt `--continue` bzw. `resume --last` den vollen
 *  Kontext zurück, ohne dass jemand etwas prompten muss. Freie Kommandos
 *  bleiben unverändert, wenn wir das Werkzeug nicht kennen. */
export function continueCommand(command: string): string {
  const trimmed = command.trim();
  if (!trimmed) return trimmed;
  const tool = trimmed.split(/\s+/)[0].split(/[\\/]/).pop()?.replace(/\.(cmd|exe)$/i, "");
  if (/--continue|\bresume\b/.test(trimmed)) return trimmed;
  if (tool === "claude") return `${trimmed} --continue`;
  if (tool === "codex") return `${trimmed} resume --last`;
  return trimmed;
}
