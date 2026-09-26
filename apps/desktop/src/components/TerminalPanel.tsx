// Terminal-Seitenleiste (T6): xterm.js über dem PTY der Rust-Seite.
// Läuft im Working Dir (Settings); der Autostart-Command wird Rust-seitig
// vorgetippt. Die Komponente bleibt gemountet (Sidebar-Toggle versteckt
// nur), damit die Shell weiterläuft.

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { readText, writeText } from "@tauri-apps/plugin-clipboard-manager";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import { beginActivity, endActivity } from "../lib/activity";
import { showTab } from "../lib/panels";
import type { AgentStartupReport } from "../lib/system";
import type { AgentSession, SessionRequest } from "../lib/agents";
import { StartupDetails } from "./AgentStartup";
import { deliverToTerminal, registerTerminalWriter } from "../lib/handover";
import { registerQaTerminal } from "../lib/qa";
import { terminalTheme, useTerminalPreferences } from "../lib/terminalPreferences";
import { observeTerminalAttention, type TerminalAttention } from "../lib/terminalAttention";
import { foreignSelection, isCopyShortcut, isPasteShortcut, writeClipboard } from "../lib/terminalClipboard";

export interface TerminalOpened {
  cwd: string;
  startup: AgentStartupReport | null;
  session: AgentSession | null;
  launch: string;
  /** Spec 070: re-attached to a session that kept running in the PTY host. */
  reattached?: boolean;
}

/** Relativer Pfad mit Endung + `:zeile` (optional `:spalte`), wie Compiler
 *  und Test-Runner ihn ausgeben; absolute Pfade und URLs bleiben außen vor. */
const FILE_LINE_RE = /(?<![\w/:])((?:[\w.@-]+\/)*[\w.@-]+\.[a-zA-Z0-9]{1,8}):(\d+)(?::\d+)?/g;

interface TermOut {
  id: string;
  data: string;
}

// Ohne `cwd`/`autostart` gelten die App-Settings (Dashboard); das
// Projektfenster übergibt beides (cwd = Projektwurzel, Agent-Kommando).
import { useProjectActivity } from "../lib/projectActivity";
import { t } from "../i18n";

export default function TerminalPanel({
  visible,
  cwd: cwdProp,
  autostart,
  workspaceId,
  session,
  onOpened,
  onFailed,
}: {
  visible: boolean;
  cwd?: string;
  autostart?: string;
  workspaceId?: string;
  /** Spec 009: was mit der Sitzung geschehen soll; Default = neue Sitzung. */
  session?: SessionRequest;
  onOpened?: (opened: TerminalOpened) => void;
  /** Start abgelehnt oder gescheitert — die Eltern zeigen die Wahl statt „fortgesetzt“. */
  onFailed?: (error: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const projectActive = useProjectActivity();
  const { preferences, update: updatePreferences, error: preferencesError } = useTerminalPreferences();
  const preferencesRef = useRef(preferences);
  preferencesRef.current = preferences;
  const [attention, setAttention] = useState<TerminalAttention | null>(null);
  const [notificationError, setNotificationError] = useState("");
  // Spec 068: kurze Rückmeldung zum Kopieren („Kopiert" oder der Fehlergrund).
  const [clipboardHint, setClipboardHint] = useState("");
  const hintTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const showHint = useCallback((text: string, ms = 1800) => {
    setClipboardHint(text);
    if (hintTimer.current) clearTimeout(hintTimer.current);
    hintTimer.current = setTimeout(() => setClipboardHint(""), ms);
  }, []);

  // W6/D24 → Spec 011: „ins Terminal tippen" läuft über die bestätigte
  // Zustellung; das alte Event bleibt für Aufrufer ohne Rückmeldung.
  useEffect(() => {
    const handler = (event: Event) => {
      if (!projectActive.current) return;
      const data = (event as CustomEvent<string>).detail;
      if (data) void deliverToTerminal(data);
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
  const onFailedRef = useRef(onFailed);
  onFailedRef.current = onFailed;
  const sessionRef = useRef(session);
  sessionRef.current = session;

  const restart = useCallback(() => {
    const oldId = idRef.current;
    if (oldId) void invoke("terminal_kill", { id: oldId }).catch(() => {});
    setGeneration((current) => current + 1);
  }, []);

  useEffect(() => {
    let cleanup: (() => void) | undefined;
    // A cancelled mount must not construct a terminal or open a PTY. This also
    // keeps the development lifecycle probe out of xterm's deferred layout.
    const initialization = requestAnimationFrame(() => {
    const container = containerRef.current;
    if (!container) return;

    // Spec 070: beim Wiederanhängen ist die Id die der laufenden Host-Sitzung.
    const attachTo = sessionRef.current?.mode === "attach" ? sessionRef.current.id : null;
    const id = attachTo ?? `term-${crypto.randomUUID()}`;
    idRef.current = id;
    setStatus("");
    setStartup(null);
    setAttention(null);

    const terminal = new Terminal({
      fontSize: preferencesRef.current.font_size,
      fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
      cursorBlink: true,
      theme: terminalTheme(document.documentElement.dataset.theme === "dark"),
      minimumContrastRatio: 4.5,
      // Spec 068: beansprucht ein TUI die Maus, markiert ⌥-Ziehen trotzdem Text.
      macOptionClickForcesSelection: true,
    });
    const fit = new FitAddon();
    terminal.loadAddon(fit);
    terminal.open(container);
    const syncTheme = () => {
      const theme = terminalTheme(document.documentElement.dataset.theme === "dark");
      terminal.options.theme = theme;
      container.style.backgroundColor = theme.background ?? "";
    };
    syncTheme();
    const themeObserver = new MutationObserver(syncTheme);
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    // Spec 039: die QA-Brücke darf den Puffer lesen.
    const unregisterQa = registerQaTerminal(terminal);
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
    const stopAttention = observeTerminalAttention(terminal, notice => {
      setAttention(notice);
      if (preferencesRef.current.system_notifications) {
        void invoke("terminal_attention", { id }).catch(error => setNotificationError(String(error)));
      }
    });

    // Kopieren (Spec 068, nach BO-Finding 2026-07-27 und 2026-09-24): xterm hält
    // die Auswahl selbst, der DOM hat keine. Deshalb kopiert ein fensterweiter
    // Handler in der Capture-Phase — unabhängig davon, wo der Fokus liegt — und
    // schließt das Ereignis mit preventDefault ab; sonst sucht macOS im
    // Systemmenü ein „Kopieren", findet ohne DOM-Auswahl keins und piept.
    // Ohne Auswahl bleibt ^C dem Terminal (SIGINT). Tauri-Clipboard-Plugin
    // zuerst (WKWebView-sicher), mit Rückfallwegen und sichtbarem Ergebnis.
    const copySelection = () => {
      const text = terminal.getSelection();
      if (!text) return false;
      writeClipboard(text, writeText)
        .then(() => showHint("Kopiert"))
        .catch((error) => showHint(`Kopieren fehlgeschlagen: ${String(error)}`, 6000));
      return true;
    };
    const copyKeyListener = (event: KeyboardEvent) => {
      if (!isCopyShortcut(event) || !terminal.hasSelection()) return;
      if (container.clientWidth === 0) return; // verstecktes Terminal
      if (foreignSelection(document.activeElement, container)) return;
      event.preventDefault();
      copySelection();
    };
    // Menü „Bearbeiten → Kopieren" und Kontextmenü lösen ein copy-Ereignis aus.
    const nativeCopyListener = (event: ClipboardEvent) => {
      if (!terminal.hasSelection() || container.clientWidth === 0) return;
      if (foreignSelection(document.activeElement, container)) return;
      event.clipboardData?.setData("text/plain", terminal.getSelection());
      event.preventDefault();
      showHint("Kopiert");
    };
    window.addEventListener("keydown", copyKeyListener, true);
    document.addEventListener("copy", nativeCopyListener, true);

    terminal.attachCustomKeyEventHandler((event) => {
      if (event.type !== "keydown") return true;
      // xterm 5.5 drops Shift on Enter. CSI-u preserves the modifier for
      // host input editors without sending the CR that would submit a prompt.
      if (event.key === "Enter" && event.shiftKey && !event.altKey && !event.ctrlKey
        && !event.metaKey && !event.isComposing && event.keyCode !== 229) {
        event.preventDefault();
        terminal.input("\x1b[13;2u", true);
        return false;
      }
      if (isCopyShortcut(event)) {
        // Kopiert hat bereits der fensterweite Handler; hier nur ^C unterdrücken.
        if (!terminal.hasSelection()) return true;
        event.preventDefault();
        return false;
      }
      if (isPasteShortcut(event)) {
        event.preventDefault();
        void readText()
          .then((text) => {
            if (text) terminal.paste(text);
          })
          .catch((error) => showHint(t("Einfügen fehlgeschlagen: {error}", { error: String(error) }), 6000));
        return false;
      }
      return true;
    });

    const unlisteners: UnlistenFn[] = [];
    let disposed = false;
    let unregisterWriter: (() => void) | null = null;

    void (async () => {
      try {
        unlisteners.push(
          await listen<TermOut>("term-out", (event) => {
            if (event.payload.id !== id) return;
            terminal.write(event.payload.data);
            // Output indicates terminal activity, not a successful task.
            if (!busyRef.current) busyRef.current = beginActivity("agent", t("Agent-Terminal arbeitet"));
            if (idleTimer.current) clearTimeout(idleTimer.current);
            idleTimer.current = setTimeout(() => {
              if (busyRef.current) endActivity(busyRef.current, "ok");
              busyRef.current = null;
            }, 2500);
          }),
          await listen<TermOut>("term-exit", (event) => {
            if (event.payload.id === id) {
              setAttention(null);
              terminal.writeln(`\r\n\x1b[33m[${t("Shell beendet — bitte „Neu starten“")}]\x1b[0m`);
            }
          }),
        );
        if (disposed) {
          unlisteners.forEach((unlisten) => unlisten());
          return;
        }
        setStatus(attachTo ? t("Laufende Sitzung wird wieder verbunden…") : t("Startumgebung wird geprüft…"));
        // Listeners above are live before this call: early PTY output is not lost.
        // Spec 070: `terminal_attach` sends the host's buffer as term-out before it returns.
        const opened = attachTo
          ? await invoke<TerminalOpened>("terminal_attach", { id, cols: terminal.cols, rows: terminal.rows })
          : await invoke<TerminalOpened>("terminal_open", {
            id, cols: terminal.cols, rows: terminal.rows, cwd: cwdProp, autostart, workspaceId,
            session: sessionRef.current ?? { mode: "new" },
          });
        if (disposed) {
          await invoke("terminal_kill", { id });
          return;
        }
        setCwd(opened.cwd);
        setStartup(opened.startup);
        setStatus("");
        // Spec 011: nur ein laufendes Terminal nimmt Aufträge an — nur das aktive Projekt.
        unregisterWriter = registerTerminalWriter(async (data) => {
          if (!projectActive.current) throw new Error(t("Terminal gehört zu einem anderen Projekt."));
          await invoke("terminal_write", { id, data });
        });
        // BO-Finding: nach Start/Neustart soll die Eingabe sofort im Terminal landen.
        if (container.clientWidth > 0) terminal.focus();
        onOpenedRef.current?.(opened);
      } catch (error) {
        if (!disposed) {
          setStatus(String(error));
          terminal.writeln(`\x1b[31m${String(error)}\x1b[0m`);
          onFailedRef.current?.(String(error));
        }
      }
    })();

    const dataListener = terminal.onData((data) => {
      setAttention(null);
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

    cleanup = () => {
      disposed = true;
      unregisterWriter?.();
      unregisterQa();
      window.removeEventListener("keydown", copyKeyListener, true);
      document.removeEventListener("copy", nativeCopyListener, true);
      if (hintTimer.current) clearTimeout(hintTimer.current);
      if (idleTimer.current) clearTimeout(idleTimer.current);
      if (busyRef.current) endActivity(busyRef.current, "cancelled");
      busyRef.current = null;
      observer.disconnect();
      themeObserver.disconnect();
      stopAttention();
      dataListener.dispose();
      unlisteners.forEach((unlisten) => unlisten());
      void invoke("terminal_kill", { id }).catch(() => {});
      terminal.dispose();
      if (terminalRef.current === terminal) terminalRef.current = null;
      if (fitRef.current === fit) fitRef.current = null;
    };
    });
    return () => { cancelAnimationFrame(initialization); cleanup?.(); };
  }, [generation]);

  useEffect(() => {
    const terminal = terminalRef.current;
    if (!terminal) return;
    terminal.options.fontSize = preferences.font_size;
    const frame = requestAnimationFrame(() => {
      if (!containerRef.current?.clientWidth) return;
      fitRef.current?.fit();
      void invoke("terminal_resize", { id: idRef.current, cols: terminal.cols, rows: terminal.rows }).catch(() => {});
    });
    return () => cancelAnimationFrame(frame);
  }, [preferences.font_size]);

  // Beim Einblenden nachfitten (im hidden-Zustand ist die Breite 0).
  useEffect(() => {
    if (visible && fitRef.current && terminalRef.current) {
      const frame = requestAnimationFrame(() => {
        fitRef.current?.fit();
        terminalRef.current?.focus();
        void invoke("terminal_resize", {
          id: idRef.current,
          cols: terminalRef.current?.cols ?? 80,
          rows: terminalRef.current?.rows ?? 24,
        }).catch(() => {});
      });
      return () => cancelAnimationFrame(frame);
    }
  }, [visible]);

  // Der Sidebar-Container (Breite, border, Toggle) gehört App.tsx — hier
  // nur der Terminal-Inhalt, damit AskBoPanel darüber wohnen kann.
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {attention && preferences.popups && createPortal(
        <aside role="alert" aria-label={t("Terminal braucht Aufmerksamkeit")}
          className="fixed bottom-5 right-5 z-[100] w-96 max-w-[calc(100vw-2rem)] rounded-xl border border-amber-400 bg-white p-4 text-slate-800 shadow-xl">
          <h3 className="font-semibold">{t("Terminal braucht Aufmerksamkeit")}</h3>
          <p className="mt-1 text-sm">{attention.message}</p>
          <p className="my-2 break-all font-mono text-xs">{cwd || cwdProp}</p>
          {notificationError && <p className="text-xs text-amber-700">Systemmeldung: {notificationError}</p>}
          <div className="flex gap-2">
            <button className="rounded bg-slate-800 px-3 py-1 text-sm text-white" onClick={() => {
              window.dispatchEvent(new CustomEvent("speccify:show-terminal"));
              terminalRef.current?.scrollToBottom();
              terminalRef.current?.focus();
              setAttention(null);
            }}>{t("Zum Terminal")}</button>
            <button className="rounded border px-3 py-1 text-sm" onClick={() => setAttention(null)}>{t("Schließen")}</button>
          </div>
        </aside>, document.body) }
      {startup ? (
        <details className="max-h-40 overflow-y-auto border-b border-slate-700 px-3 py-2 text-slate-400">
          <summary className="cursor-pointer text-xs">Startumgebung{startup.warnings.length ? ` · ${startup.warnings.length} Hinweise` : ""}</summary>
          <StartupDetails report={startup} />
        </details>
      ) : null}
      <div className="flex items-center gap-2 border-b border-slate-700 px-3 py-1.5">
        <span className="text-xs font-semibold text-slate-300">{t("Agent-Terminal")}</span>
        <button aria-label={t("Terminal-Schrift verkleinern")} disabled={preferences.font_size <= 8}
          className="rounded border px-1 text-xs disabled:opacity-30"
          onClick={() => void updatePreferences({ font_size: preferences.font_size - 1 })}>{"A−"}</button>
        <span className="text-xs text-slate-500" aria-label={t("Aktuelle Terminal-Schriftgröße")}>{preferences.font_size} px</span>
        <button aria-label={t("Terminal-Schrift vergrößern")} disabled={preferences.font_size >= 32}
          className="rounded border px-1 text-xs disabled:opacity-30"
          onClick={() => void updatePreferences({ font_size: preferences.font_size + 1 })}>{"A+"}</button>
        <span className="truncate font-mono text-[10px] text-slate-500" title={cwd}>
          {cwd}
        </span>
        <button
          onClick={restart}
          className="ml-auto rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-200 hover:bg-slate-600"
        >
          {t("Neu starten")}
        </button>
      </div>
      {status ? <p className="px-3 py-1 text-xs text-red-400">{status}</p> : null}
      {clipboardHint ? <p role="status" aria-label="Zwischenablage" className="px-3 py-1 text-xs text-slate-400">{clipboardHint}</p> : null}
      {preferencesError ? <p role="alert" className="px-3 text-xs text-red-400">{preferencesError}</p> : null}
      <div ref={containerRef} className="min-h-0 flex-1 p-1" />
    </div>
  );
}
