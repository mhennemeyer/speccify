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

/** Identity of a started session as the native side reported it (Spec 009,
 *  D4): Claude gets an app-chosen id (`--session-id`), Codex assigns its own
 *  and reports none. */
export interface AgentSession {
  host: string;
  id: string | null;
}

/** Remembered per project/dashboard in localStorage — a UI marker, no
 *  project data. `command` is the command the session was started with. */
export interface AgentSessionRecord extends AgentSession {
  command: string;
  startedAt: string;
}

/** What `terminal_open` should do about the session; the native side builds
 *  the actual command line and refuses anything it cannot do exactly. */
export type SessionRequest =
  | { mode: "new" }
  | { mode: "resume"; host: string; id: string | null }
  | { mode: "pick" }
  | { mode: "latest" };

/** Host name of a plain agent command; `null` for free commands or shell-only.
 *  Mirrors the native `known_host` for labelling only — the native side decides. */
export function hostOf(command: string): string | null {
  const trimmed = command.trim();
  if (!trimmed || /[$`;|&<>\n\r]/.test(trimmed)) return null;
  const name = trimmed.split(/\s+/)[0].split(/[\\/]/).pop()?.replace(/\.(cmd|exe)$/i, "") ?? "";
  return name === "claude" || name === "codex" ? name : null;
}

/** Human-readable form of what a request will run, for titles and activity. */
export function describeSessionRequest(request: SessionRequest, host: string | null): string {
  if (!host) return "";
  switch (request.mode) {
    case "new":
      return host === "claude" ? "Neue Sitzung mit fester Sitzungs-ID" : "Neue Sitzung";
    case "resume":
      return request.id
        ? host === "claude"
          ? `${host} --resume ${request.id}`
          : `${host} resume ${request.id}`
        : host === "claude"
          ? `${host} --resume (Auswahl)`
          : `${host} resume (Auswahl)`;
    case "pick":
      return host === "claude" ? `${host} --resume (Auswahl)` : `${host} resume (Auswahl)`;
    case "latest":
      return host === "claude"
        ? `${host} --continue — neueste Sitzung des Hosts in diesem Ordner, nicht zwingend die gemerkte`
        : `${host} resume --last — neueste Sitzung des Hosts, nicht zwingend die gemerkte`;
  }
}

export function loadSessionRecord(key: string): AgentSessionRecord | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    // Legacy marker "1": a session ran, identity unknown — offer choice, not automatic resume.
    if (raw === "1") return { host: "", id: null, command: "", startedAt: "" };
    const parsed = JSON.parse(raw) as Partial<AgentSessionRecord>;
    if (typeof parsed.host !== "string") return null;
    return {
      host: parsed.host,
      id: typeof parsed.id === "string" ? parsed.id : null,
      command: typeof parsed.command === "string" ? parsed.command : "",
      startedAt: typeof parsed.startedAt === "string" ? parsed.startedAt : "",
    };
  } catch {
    return null;
  }
}

export function saveSessionRecord(key: string, record: AgentSessionRecord | null) {
  try {
    if (record) localStorage.setItem(key, JSON.stringify(record));
    else localStorage.removeItem(key);
  } catch {
    // ohne Merker kein Fortsetzen — sonst egal
  }
}
