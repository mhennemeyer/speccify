import type { Terminal } from "@xterm/xterm";

export interface TerminalAttention { message: string; signal: boolean }

/** Inspect parsed screen cells: ANSI redraws and split PTY chunks are not text. */
export function observeTerminalAttention(terminal: Terminal, notify: (notice: TerminalAttention) => void) {
  let timer: ReturnType<typeof setTimeout> | undefined;
  let prompt = "";
  let lastSignal = 0;
  const seen = new Map<string, number>();
  const emit = (message: string, signal: boolean, key = message) => {
    const now = Date.now();
    if (now - (seen.get(key) ?? 0) < 30_000) return;
    if (seen.size > 100) seen.clear();
    seen.set(key, now);
    notify({ message, signal });
  };
  const signal = () => {
    lastSignal = Date.now();
    emit("Das Terminal hat um Aufmerksamkeit gebeten.", true);
  };
  const listeners = [
    // A response starts a new interaction; the next signal may use the same text.
    terminal.onData(() => seen.clear()),
    terminal.onBell(signal),
    terminal.parser.registerOscHandler(9, data => {
      // OSC 9;4 is a progress indicator, not a notification.
      if (!/^\d;/.test(data)) signal();
      return true;
    }),
    terminal.parser.registerOscHandler(777, data => {
      if (data.startsWith("notify;")) signal();
      return true;
    }),
    terminal.onWriteParsed(() => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const buffer = terminal.buffer.active;
        const end = buffer.baseY + buffer.cursorY;
        const lines = [];
        for (let row = Math.max(buffer.baseY, end - 14); row <= end; row++) {
          lines.push(buffer.getLine(row)?.translateToString(true) ?? "");
        }
        const screen = lines.join("\n");
        const approval = screen.match(/(?:would you like to (?:run|make|allow|proceed)[^?]*\?|do you (?:want to (?:proceed|allow|run)|trust)[^?]*\?|allow[^\n?]{0,160}\?|(?:befehl|zugriff|ausführung)[^?\n]{0,160}(?:zulassen|erlauben|genehmigen)[^?\n]*\?|(?:möchtest|wollen) (?:du|sie)[^?\n]*(?:fortfahren|ausführen|zulassen)[^?\n]*\?)/i);
        const choiceQuestion = /(?:\[y\/n\]|\(y\/n\)|\[j\/n\]|enter to (?:confirm|select)|esc to cancel|tab to (?:select|navigate))/i.test(screen)
          ? [...lines].reverse().find(line => line.trim().endsWith("?")) : undefined;
        const next = (approval?.[0] ?? choiceQuestion ?? "").replace(/\s+/g, " ").trim();
        if (next && next !== prompt && Date.now() - lastSignal > 2000) {
          emit("Das Terminal wartet möglicherweise auf eine Antwort oder Freigabe.", false, next);
        }
        prompt = next;
      }, 450);
    }),
  ];
  return () => { clearTimeout(timer); listeners.forEach(listener => listener.dispose()); };
}
