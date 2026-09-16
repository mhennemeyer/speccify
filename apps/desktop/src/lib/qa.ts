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
  terminalAppearance: () => { fontSize: number | undefined; background: string | undefined; cols: number; rows: number } | null;
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
  // Umgebrochene Zeilen (isWrapped) gehören zur vorigen: der Puffer liefert
  // logische Zeilen, so wie der Text eingegeben oder ausgegeben wurde.
  const lines: string[] = [];
  for (let y = 0; y < buffer.length; y += 1) {
    const line = buffer.getLine(y);
    const text = line?.translateToString(true) ?? "";
    if (line?.isWrapped && lines.length > 0) lines[lines.length - 1] += text;
    else lines.push(text);
  }
  return lines.join("\n").replace(/\s+$/, "");
}

export function installQaHooks(): void {
  window.__speccifyQa = { terminalText, terminalReady,
    terminalAppearance: () => terminal ? { fontSize: terminal.options.fontSize, background: terminal.options.theme?.background, cols: terminal.cols, rows: terminal.rows } : null,
  };
}
