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
