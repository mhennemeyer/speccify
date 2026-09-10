// Terminal-Seitenleiste (T6): xterm.js über dem PTY der Rust-Seite.
// Läuft im Working Dir (Settings); der Autostart-Command wird Rust-seitig
// vorgetippt. Die Komponente bleibt gemountet (Sidebar-Toggle versteckt
// nur), damit die Shell weiterläuft.

import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { readText, writeText } from "@tauri-apps/plugin-clipboard-manager";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import { beginActivity, endActivity } from "../lib/activity";
import { showTab } from "../lib/panels";
import type { AgentStartupReport } from "../lib/system";
import { StartupDetails } from "./AgentStartup";

/** Relativer Pfad mit Endung + `:zeile` (optional `:spalte`), wie Compiler
 *  und Test-Runner ihn ausgeben; absolute Pfade und URLs bleiben außen vor. */
const FILE_LINE_RE = /(?<![\w/:])((?:[\w.@-]+\/)*[\w.@-]+\.[a-zA-Z0-9]{1,8}):(\d+)(?::\d+)?/g;

interface TermOut {
  id: string;
  data: string;
}

// Ohne `cwd`/`autostart` gelten die App-Settings (Dashboard); das
// Projektfenster übergibt beides (cwd = Projektwurzel, Agent-Kommando).
export default function TerminalPanel({
  visible,
  cwd: cwdProp,
  autostart,
  onOpened,
}: {
  visible: boolean;
  cwd?: string;
  autostart?: string;
  onOpened?: (command: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  // W6/D24: „ins Terminal tippen" von anderen Tabs (z. B. Skill-Import).
  useEffect(() => {
    const handler = (event: Event) => {
      const data = (event as CustomEvent<string>).detail;
      if (idRef.current && data) {
        void invoke("terminal_write", { id: idRef.current, data });
      }
    };
    window.addEventListener("speccify:type-command", handler);
    return () => window.removeEventListener("speccify:type-command", handler);
  }, []);
  const terminalRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const idRef = useRef<string>("");
  const busyRef = useRef<string | null>(null);
  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [generation, setGeneration] = useState(0);
  const [cwd, setCwd] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [startup, setStartup] = useState<AgentStartupReport | null>(null);
  const onOpenedRef = useRef(onOpened);
  onOpenedRef.current = onOpened;

  const restart = useCallback(() => {
    const oldId = idRef.current;
    if (oldId) void invoke("terminal_kill", { id: oldId }).catch(() => {});
    setGeneration((current) => current + 1);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const id = `term-${Date.now()}-${generation}`;
    idRef.current = id;
    setStatus("");
    setStartup(null);

    const terminal = new Terminal({
      fontSize: 12,
      fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
      cursorBlink: true,
      theme: { background: "#0f172a" },
    });
    const fit = new FitAddon();
    terminal.loadAddon(fit);
    terminal.open(container);
    // I3: `pfad:zeile` in der Ausgabe (Compiler, Tests, grep) ist ein Link
    // in den Editor — ⌘/Strg-Klick wie in Terminals üblich, Hover zeigt es.
    terminal.registerLinkProvider({
      provideLinks(lineNumber, callback) {
        const row = terminal.buffer.active.getLine(lineNumber - 1);
        const text = row?.translateToString(true) ?? "";
        const links: Array<{
          range: { start: { x: number; y: number }; end: { x: number; y: number } };
          text: string;
          activate: () => void;
        }> = [];
        for (const match of text.matchAll(FILE_LINE_RE)) {
          const start = (match.index ?? 0) + 1;
          links.push({
            range: {
              start: { x: start, y: lineNumber },
              end: { x: start + match[0].length - 1, y: lineNumber },
            },
            text: match[0],
            activate: () => {
              window.dispatchEvent(
                new CustomEvent("speccify:open-file", { detail: `${match[1]}:${match[2]}` }),
              );
              showTab("files");
            },
          });
        }
        callback(links.length > 0 ? links : undefined);
      },
    });
    fit.fit();
    terminalRef.current = terminal;
    fitRef.current = fit;

    // Kopieren/Einfügen (BO-Finding): ⌘C kopiert die Selektion (ohne
    // Selektion normal weiterreichen — ^C bleibt SIGINT), ⌘V fügt ein.
    // Tauri-Clipboard-Plugin statt navigator.clipboard (WKWebView-sicher).
    terminal.attachCustomKeyEventHandler((event) => {
      if (event.type !== "keydown") return true;
      const modifier = event.metaKey || (event.ctrlKey && event.shiftKey);
      if (!modifier) return true;
      const key = event.key.toLowerCase();
      if (key === "c" && terminal.hasSelection()) {
        void writeText(terminal.getSelection());
        return false;
      }
      if (key === "v") {
        void readText()
          .then((text) => {
            if (text) terminal.paste(text);
          })
          .catch(() => {});
        return false;
      }
      return true;
    });

    const unlisteners: UnlistenFn[] = [];
    let disposed = false;

    void (async () => {
      try {
        unlisteners.push(
          await listen<TermOut>("term-out", (event) => {
            if (event.payload.id !== id) return;
            terminal.write(event.payload.data);
            // Output indicates terminal activity, not a successful task.
            if (!busyRef.current) busyRef.current = beginActivity("agent", "Agent-Terminal arbeitet");
            if (idleTimer.current) clearTimeout(idleTimer.current);
            idleTimer.current = setTimeout(() => {
              if (busyRef.current) endActivity(busyRef.current, "ok");
              busyRef.current = null;
            }, 2500);
          }),
          await listen<TermOut>("term-exit", (event) => {
            if (event.payload.id === id) {
              terminal.writeln("\r\n\x1b[33m[Shell beendet — bitte 'Neu starten']\x1b[0m");
            }
          }),
        );
        if (disposed) {
          unlisteners.forEach((unlisten) => unlisten());
          return;
        }
        setStatus("Startumgebung wird geprüft…");
        const opened = await invoke<{ cwd: string; startup: AgentStartupReport | null }>("terminal_open", {
          id, cols: terminal.cols, rows: terminal.rows, cwd: cwdProp, autostart,
        });
        if (disposed) {
          await invoke("terminal_kill", { id });
          return;
        }
        setCwd(opened.cwd);
        setStartup(opened.startup);
        setStatus("");
        onOpenedRef.current?.(autostart ?? "");
      } catch (error) {
        if (!disposed) {
          setStatus(String(error));
          terminal.writeln(`\x1b[31m${String(error)}\x1b[0m`);
        }
      }
    })();

    const dataListener = terminal.onData((data) => {
      void invoke("terminal_write", { id, data }).catch(() => {});
    });

    const observer = new ResizeObserver(() => {
      if (container.clientWidth === 0) return; // versteckt
      fit.fit();
      void invoke("terminal_resize", {
        id,
        cols: terminal.cols,
        rows: terminal.rows,
      }).catch(() => {});
    });
    observer.observe(container);

    return () => {
      disposed = true;
      if (idleTimer.current) clearTimeout(idleTimer.current);
      if (busyRef.current) endActivity(busyRef.current, "cancelled");
      busyRef.current = null;
      observer.disconnect();
      dataListener.dispose();
      unlisteners.forEach((unlisten) => unlisten());
      void invoke("terminal_kill", { id }).catch(() => {});
      terminal.dispose();
    };
  }, [generation]);

  // Beim Einblenden nachfitten (im hidden-Zustand ist die Breite 0).
  useEffect(() => {
    if (visible && fitRef.current && terminalRef.current) {
      requestAnimationFrame(() => {
        fitRef.current?.fit();
        void invoke("terminal_resize", {
          id: idRef.current,
          cols: terminalRef.current?.cols ?? 80,
          rows: terminalRef.current?.rows ?? 24,
        }).catch(() => {});
      });
    }
  }, [visible]);

  // Der Sidebar-Container (Breite, border, Toggle) gehört App.tsx — hier
  // nur der Terminal-Inhalt, damit AskBoPanel darüber wohnen kann.
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {startup ? (
        <details className="max-h-40 overflow-y-auto border-b border-slate-700 px-3 py-2 text-slate-400">
          <summary className="cursor-pointer text-xs">Startumgebung{startup.warnings.length ? ` · ${startup.warnings.length} Hinweise` : ""}</summary>
          <StartupDetails report={startup} />
        </details>
      ) : null}
      <div className="flex items-center gap-2 border-b border-slate-700 px-3 py-1.5">
        <span className="text-xs font-semibold text-slate-300">Agent-Terminal</span>
        <span className="truncate font-mono text-[10px] text-slate-500" title={cwd}>
          {cwd}
        </span>
        <button
          onClick={restart}
          className="ml-auto rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-200 hover:bg-slate-600"
        >
          Neu starten
        </button>
      </div>
      {status ? <p className="px-3 py-1 text-xs text-red-400">{status}</p> : null}
      <div ref={containerRef} className="min-h-0 flex-1 p-1" />
    </div>
  );
}
