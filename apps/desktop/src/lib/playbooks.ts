export type PlaybookStatus = "active" | "draft" | "invalid";

/** Flat frontmatter contract shared with playbook_cmd::playbook_status. */
export function playbookStatus(text: string): PlaybookStatus {
  const lines = text.replace(/^\uFEFF+/, "").split(/\r?\n/);
  if (lines[0] !== "---") return "active";
  const end = lines.indexOf("---", 1);
  if (end === -1) return "invalid";
  const values = lines.slice(1, end).filter(line => line.split(":", 1)[0].trim() === "status" && line.includes(":"));
  if (!values.length) return "active";
  if (values.length !== 1) return "invalid";
  const raw = values[0].slice(values[0].indexOf(":") + 1).trim().split(" #")[0].trim();
  const value = /^(".*"|'.*')$/.test(raw) ? raw.slice(1, -1) : raw;
  return value === "active" || value === "draft" ? value : "invalid";
}

export const PLAYBOOK_STATUS_LABELS: Record<PlaybookStatus, string> = {
  active: "Aktiv", draft: "Draft", invalid: "Status prüfen",
};

export function playbookNotice(status: PlaybookStatus): string {
  return status === "draft"
    ? "Draft — unverbindlicher Entwurf. Keine Arbeitsanweisung oder Umsetzungsfreigabe. Beim Bearbeiten den Draft-Status erhalten."
    : "Unbekannter oder ungültiger Playbook-Status — keine Arbeitsanweisung. Status vor einer Anwendung ausdrücklich klären.";
}
