// Terminal-Seitenleiste (T6): xterm.js über dem PTY der Rust-Seite.
// Läuft im Working Dir (Settings); der Autostart-Command wird Rust-seitig
// vorgetippt. Die Komponente bleibt gemountet (Sidebar-Toggle versteckt
// nur), damit die Shell weiterläuft.

import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";

interface TermOut {
  id: string;
  data: string;
}

export default function TerminalPanel({ visible }: { visible: boolean }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const terminalRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const idRef = useRef<string>("");
  const [generation, setGeneration] = useState(0);
  const [cwd, setCwd] = useState<string>("");
  const [status, setStatus] = useState<string>("");

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

    const terminal = new Terminal({
      fontSize: 12,
      fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
      cursorBlink: true,
      theme: { background: "#0f172a" },
    });
    const fit = new FitAddon();
    terminal.loadAddon(fit);
    terminal.open(container);
    fit.fit();
    terminalRef.current = terminal;
    fitRef.current = fit;

    const unlisteners: UnlistenFn[] = [];
    let disposed = false;

    void (async () => {
      try {
        const startedIn = await invoke<string>("terminal_open", {
          id,
          cols: terminal.cols,
          rows: terminal.rows,
        });
        if (!disposed) setCwd(startedIn);
      } catch (error) {
        if (!disposed) {
          setStatus(String(error));
          terminal.writeln(`\x1b[31m${String(error)}\x1b[0m`);
        }
        return;
      }
      unlisteners.push(
        await listen<TermOut>("term-out", (event) => {
          if (event.payload.id === id) terminal.write(event.payload.data);
        }),
        await listen<TermOut>("term-exit", (event) => {
          if (event.payload.id === id) {
            terminal.writeln("\r\n\x1b[33m[Shell beendet — bitte 'Neu starten']\x1b[0m");
          }
        }),
      );
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
