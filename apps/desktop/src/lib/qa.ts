// QA-Haken (Spec 039): `window.__speccifyQa` gibt einem Prüfwerkzeug, das
// über die QA-Brücke JavaScript im Fenster ausführt, lesenden Zugriff auf
// Dinge, die im DOM nicht stehen — vor allem den Terminalpuffer. Nur lesen,
// keine Steuerung: Klicks und Eingaben laufen über das DOM.

import type { Terminal } from "@xterm/xterm";
import { terminalReady } from "./handover";

export interface QaHooks {
  /** Sichtbarer Pufferinhalt des Agent-Terminals dieses Fensters, `null` ohne Terminal. */
  terminalText: () => string | null;
  /** Ob ein Terminal Aufträge annimmt (Spec 011). */
  terminalReady: () => boolean;
}

declare global {
  interface Window {
    __speccifyQa?: QaHooks;
  }
}

let terminal: Terminal | null = null;

export function registerQaTerminal(instance: Terminal): () => void {
  terminal = instance;
  return () => {
    if (terminal === instance) terminal = null;
  };
}

export function terminalText(): string | null {
  if (!terminal) return null;
  const buffer = terminal.buffer.active;
  const lines: string[] = [];
  for (let y = 0; y < buffer.length; y += 1) {
    lines.push(buffer.getLine(y)?.translateToString(true) ?? "");
  }
  return lines.join("\n").replace(/\s+$/, "");
}

export function installQaHooks(): void {
  window.__speccifyQa = { terminalText, terminalReady };
}
