// Übergabe an den Agenten (Spec 011): ein Weg für Specs, Playbooks, Skills,
// Tools und Dateien. Der Text nennt Projekt, Pfad, bei Specs ID und Station,
// die Absicht und die geltenden Regeln; die Datei bleibt die Quelle der
// Wahrheit. Zugestellt wird nur an das Terminal dieses Fensters, mit
// bestätigtem Ergebnis; Absenden (Enter) bleibt eine bewusste Nutzeraktion.

import { writeText } from "@tauri-apps/plugin-clipboard-manager";
import { fencedPrompt } from "./prompt";
import { playbookStatus, playbookNotice } from "./playbooks";
import { t } from "../i18n";

export type HandoverKind = "implement" | "review" | "read" | "edit";
export type HandoverItemType = "spec" | "playbook" | "skill" | "tool" | "file";

export interface HandoverItem {
  type: HandoverItemType;
  /** Pfad relativ zur Projektwurzel. */
  path: string;
  title?: string;
  /** Specs: Ordner-ID und Station. */
  id?: string;
  station?: string;
}

export const KIND_LABELS: Record<HandoverKind, string> = {
  implement: "Umsetzen",
  review: "Prüfen",
  read: t("Lesen und anwenden"),
  edit: "Bearbeiten",
};

export function kindsFor(type: HandoverItemType, content?: string | null): HandoverKind[] {
  if (type === "playbook" && (content == null || playbookStatus(content) !== "active")) return ["review", "edit"];
  return type === "spec" ? ["implement", "review", "read"] : ["read", "edit"];
}

function what(item: HandoverItem): string {
  switch (item.type) {
    case "spec":
      return `Spec ${item.id ?? item.path}${item.station ? ` (Station ${item.station})` : ""}`;
    case "playbook":
      return `Playbook ${item.title ?? item.path}`;
    case "skill":
      return `Skill ${item.title ?? item.path}`;
    case "tool":
      return `Tool-Vertrag ${item.title ?? item.path}`;
    default:
      return `Datei ${item.path}`;
  }
}

function order(kind: HandoverKind, item: HandoverItem): string {
  switch (kind) {
    case "implement":
      return "Auftrag: Arbeite diese Spec nach dem Spec-Workflow in `.agent/agent.md`: prüfe sie zuerst auf Lücken, hake Tasks ab, ergänze Decisions und Verification, hänge die History-Zeile an. Frag per ask_bo oder show_ui, wenn etwas unklar ist; committe nur im Rahmen der Projektregeln.";
    case "review":
      if (item.type === "playbook") return "Auftrag: Besprich diesen Playbook-Entwurf, prüfe Annahmen und offene Fragen. Wende seine Vorschläge nicht an und ändere seinen Status nicht.";
      return "Auftrag: Prüfe diese Spec gegen ihre Acceptance-Punkte — versuche zu belegen, dass etwas nicht stimmt. Führe die genannten Prüfungen aus, ändere keinen Produktivcode, und schreibe Befunde als Notiz unter Verification.";
    case "edit":
      return `Auftrag: Bearbeite ${item.type === "spec" ? "diese Spec" : "diese Datei"} wie unten beschrieben; halte Dich an die Projektregeln in \`.agent/agent.md\` und ändere nichts anderes.`;
    default:
      return item.type === "spec"
        ? "Auftrag: Lies diese Spec und fasse Stand, offene Punkte und nächsten Schritt zusammen. Ändere nichts."
        : "Auftrag: Lies dies vollständig, bevor Du es anwendest. Ändere nichts ohne Auftrag.";
  }
}

/** Der Übergabetext: Kopf mit Projekt/Pfad/Absicht, dann die Datei als Zaun. */
export function buildHandover(
  project: string,
  item: HandoverItem,
  kind: HandoverKind,
  content: string,
): string {
  const restricted = item.type === "playbook" && playbookStatus(content) !== "active";
  const safeKind = restricted && kind !== "edit" ? "review" : kind;
  const head = [
    `Projekt: ${project}`,
    `Quelle: ${project.replace(/[\\/]$/, "")}/${item.path}. Zielprojekt und Ausführungs-cwd: ${project}. Relative Tool-Abhängigkeiten dort auflösen; das gemeinsame Terminal behält seinen Root-cwd. Ein anderes Arbeitsziel muss ausdrücklich benannt werden.`,
    `${what(item)} — Datei: ${item.path} (Quelle der Wahrheit; Änderungen dort, nicht im Chat).`,
    order(safeKind, item),
    "Regeln: `.agent/agent.md` (Spec-Workflow, Commit-Rechte, Herkunft).",
  ].join("\n");
  return guardPlaybookHandover(item, content, `${head}\n\n${fencedPrompt(item.path, content)}`);
}

/** Preserve the current file's status even when a custom prompt was edited. */
export function guardPlaybookHandover(item: HandoverItem, content: string, prompt: string): string {
  if (item.type !== "playbook" || playbookStatus(content) === "active") return prompt;
  const notice = playbookNotice(playbookStatus(content));
  return prompt.startsWith(notice) ? prompt : `${notice}\nDieser Auftrag dient nur der Besprechung oder Bearbeitung dieses Inhalts; keine Umsetzung oder Aktivierung.\n\n${prompt}`;
}

// --- Zustellung ---------------------------------------------------------------

type Writer = (data: string) => Promise<void>;
let writer: Writer | null = null;
let writerSince: number | null = null;

/** Das Terminal dieses Fensters meldet sich an, solange es läuft. */
export function registerTerminalWriter(write: Writer): () => void {
  writer = write;
  writerSince = Date.now();
  return () => {
    if (writer === write) {
      writer = null;
      writerSince = null;
    }
  };
}

export function terminalReady(): boolean {
  return writer !== null;
}

/** Wie lange das Terminal schon Aufträge annimmt (ms); `null` ohne Terminal. */
export function terminalAgeMs(): number | null {
  return writerSince === null ? null : Date.now() - writerSince;
}

/** Befund F-QA-1 (Spec 011): direkt nach dem Start zeigt der Host oft noch
 *  keine Eingabezeile (Claude fragt bei neuen Ordnern erst „Trust this
 *  folder?“); ein Paste in diesem Moment geht verloren. Solange warnen. */
export const FRESH_TERMINAL_MS = 20_000;

export function terminalIsFresh(): boolean {
  const age = terminalAgeMs();
  return age !== null && age < FRESH_TERMINAL_MS;
}

export type Delivery =
  | { status: "delivered" }
  | { status: "no-terminal" }
  | { status: "error"; message: string };

const ESC = String.fromCharCode(27);
/** Bracketed-Paste-Marker: Shells und Hosts nehmen mehrzeiligen Text als eine
 *  Eingabe und führen nichts vorzeitig aus. */
export const PASTE_START = `${ESC}[200~`;
export const PASTE_END = `${ESC}[201~`;

/** Mehrzeiliges als Bracketed Paste; kein Zeilenumbruch am Ende — Enter tippt die Person. */
export function pastePayload(text: string): string {
  return text.includes("\n") ? `${PASTE_START}${text}${PASTE_END}` : text;
}

export async function deliverToTerminal(text: string): Promise<Delivery> {
  if (!writer) return { status: "no-terminal" };
  try {
    await writer(pastePayload(text));
    window.dispatchEvent(new CustomEvent("speccify:show-terminal"));
    return { status: "delivered" };
  } catch (error) {
    return { status: "error", message: String(error) };
  }
}

export async function copyHandover(text: string): Promise<void> {
  await writeText(text);
}
