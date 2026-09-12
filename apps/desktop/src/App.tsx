import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import AskBoPanel, { type AskBoInteraction } from "./components/AskBoPanel";
import TerminalPanel, { type TerminalOpened } from "./components/TerminalPanel";
import SessionChoice, { useSessionState } from "./components/SessionChoice";
import { useTheme } from "./lib/theme";
import { isMac } from "./lib/platform";
import {
  hostOf,
  loadSessionRecord,
  saveSessionRecord,
  type AgentSessionRecord,
  type SessionRequest,
} from "./lib/agents";

export const DASHBOARD_SESSION_KEY = "speccify.dashboard.agentSession";
export const DASHBOARD_RESUME_KEY = "speccify.dashboard.resumeAgent";
import AgentsView from "./views/AgentsView";
import HelpView from "./views/HelpView";
import LibraryView from "./views/LibraryView";
import ProjectsView from "./views/ProjectsView";
import EnvironmentView from "./views/EnvironmentView";
import ServersView from "./views/ServersView";
import SettingsView from "./views/SettingsView";
import KnowledgebasesView from "./views/KnowledgebasesView";

const SECTIONS = [
  // Projekte statt Composer (Plan projektfenster.md, D18 — Composer in P3 zurückgebaut).
  { id: "projects", label: "Projekte", view: <ProjectsView /> },
  { id: "library", label: "Bibliothek", view: <LibraryView /> },
  { id: "knowledgebases", label: "Knowledgebases", view: <KnowledgebasesView /> },
  { id: "environment", label: "Umgebung", view: <EnvironmentView /> },
  { id: "servers", label: "Server", view: <ServersView /> },
  { id: "agents", label: "Agents", view: <AgentsView /> },
  { id: "settings", label: "Settings", view: <SettingsView /> },
  { id: "help", label: "Hilfe", view: <HelpView /> },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

export default function App() {
  useTheme(); // Erscheinungsbild anwenden + auf Wechsel aus anderen Fenstern hören
  const [active, setActive] = useState<SectionId>("projects");
  const [sidebarVisible, setSidebarVisible] = useState(false);
  // Terminal erst beim ersten Öffnen über den Toggle mounten (sonst liefe
  // der Autostart-Command schon beim App-Start); danach gemountet lassen —
  // die Shell überlebt das Ein-/Ausklappen. ask_bo öffnet nur die Sidebar,
  // startet aber KEIN Terminal.
  const [terminalStarted, setTerminalStarted] = useState(false);
  const [interactions, setInteractions] = useState<AskBoInteraction[]>([]);

  // Dashboard-Terminal: dieselbe Sitzung nach einem Neustart fortsetzen
  // (BO 2026-09-08 „gerne überall") → Spec 009 wie im Projektfenster: nur die
  // genau bekannte Sitzung automatisch, sonst sichtbare Wahl in der Seitenleiste.
  // Das Kommando kommt aus den App-Settings.
  const [dashboardCommand, setDashboardCommand] = useState<string>("");
  const [sessionRequest, setSessionRequest] = useState<SessionRequest>({ mode: "new" });
  const [sessionRecord, setSessionRecord] = useState<AgentSessionRecord | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [resumeWanted, setResumeWanted] = useState(true);
  const sessionState = useSessionState(sessionRecord, dashboardCommand);
  const autoResumed = useRef(false);
  useEffect(() => {
    void invoke<{ terminal_autostart_command: string }>("get_settings")
      .then((settings) => {
        setDashboardCommand(settings.terminal_autostart_command ?? "");
        try {
          setSessionRecord(loadSessionRecord(DASHBOARD_SESSION_KEY));
          setResumeWanted(localStorage.getItem(DASHBOARD_RESUME_KEY) !== "0");
        } catch {
          // kein Storage — kein Fortsetzen
        }
      })
      .catch(() => {});
  }, []);
  const startTerminal = (request: SessionRequest) => {
    setStartError(null);
    setSessionRequest(request);
    setTerminalStarted(true);
    setSidebarVisible(true);
  };
  useEffect(() => {
    if (autoResumed.current || !resumeWanted || terminalStarted) return;
    if (sessionState.kind === "exact" && hostOf(dashboardCommand)) {
      autoResumed.current = true;
      startTerminal({ mode: "resume", host: hostOf(dashboardCommand) ?? "", id: sessionState.id });
    } else if (sessionState.kind !== "checking" && sessionState.kind !== "none") {
      autoResumed.current = true;
      setSidebarVisible(true); // die Wahl sichtbar machen, nicht still ersetzen
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionState, resumeWanted, terminalStarted]);
  const terminalOpened = (opened: TerminalOpened) => {
    const record: AgentSessionRecord | null = opened.session
      ? { ...opened.session, command: dashboardCommand, startedAt: new Date().toISOString() }
      : null;
    saveSessionRecord(DASHBOARD_SESSION_KEY, record);
    setSessionRecord(record);
    if (opened.session?.id) {
      setSessionRequest({ mode: "resume", host: opened.session.host, id: opened.session.id });
    }
  };
  const terminalFailed = (error: string) => {
    setStartError(error);
    setTerminalStarted(false);
    setSessionRequest({ mode: "new" });
  };

  const toggleTerminal = () => {
    setSidebarVisible((current) => !current);
  };

  useEffect(() => {
    // Offene Fragen zusätzlich AKTIV abholen (Events sind flüchtig:
    // Reload/HMR/Race beim Start — BO-Finding: UI zeigte ask_bo nicht).
    const mergePending = async () => {
      try {
        const pending = await invoke<AskBoInteraction[]>("ask_bo_pending");
        if (pending.length === 0) return;
        setInteractions((current) => {
          const known = new Set(current.map((interaction) => interaction.id));
          const fresh = pending.filter((interaction) => !known.has(interaction.id));
          if (fresh.length === 0) return current;
          setSidebarVisible(true);
          return [...current, ...fresh];
        });
      } catch {
        // Command noch nicht bereit (App-Start) — nächster Tick.
      }
    };
    void mergePending();
    const pollTimer = setInterval(() => void mergePending(), 5000);

    const unlistenPromises = [
      // Neue Agent-Frage: in die Liste + Sidebar automatisch öffnen.
      listen<AskBoInteraction>("ask-bo", (event) => {
        setInteractions((current) =>
          current.some((interaction) => interaction.id === event.payload.id)
            ? current
            : [...current, { ...event.payload }],
        );
        setSidebarVisible(true);
      }),
      // Beantwortet (egal von wo): Element einfrieren.
      listen<{ id: string; selected_options: string[]; field_values: string[] }>(
        "ask-bo-answered",
        (event) => {
          setInteractions((current) =>
            current.map((interaction) =>
              interaction.id === event.payload.id
                ? {
                    ...interaction,
                    answered: {
                      selectedOptions: event.payload.selected_options,
                      fieldValues: event.payload.field_values,
                    },
                  }
                : interaction,
            ),
          );
        },
      ),
    ];
    return () => {
      clearInterval(pollTimer);
      unlistenPromises.forEach((promise) => void promise.then((unlisten) => unlisten()));
    };
  }, []);

  const answerInteraction = (
    id: string,
    selectedOptions: string[],
    fieldValues: string[],
  ) => {
    void invoke("ask_bo_answer", { id, selectedOptions, fieldValues }).catch((error) =>
      console.error(error),
    );
  };

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900">
      <nav
        className="flex w-48 flex-col border-r border-slate-200 bg-white p-3"
        style={{ paddingTop: isMac ? 40 : 12 }}
      >
        {/* Auf macOS liegt die Ampel über dieser Ecke; die Kopfzeile ist Drag-Region. */}
        <h1
          data-tauri-drag-region
          className="mb-4 px-2 text-sm font-bold tracking-wide text-slate-500"
        >
          Speccify
        </h1>
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            onClick={() => setActive(s.id)}
            className={`mb-1 rounded px-3 py-2 text-left text-sm ${
              active === s.id
                ? "bg-slate-800 text-white"
                : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            {s.label}
          </button>
        ))}
        <button
          onClick={toggleTerminal}
          className={`mt-auto rounded px-3 py-2 text-left text-sm ${
            sidebarVisible
              ? "bg-slate-800 text-white"
              : "text-slate-700 hover:bg-slate-100"
          }`}
        >
          ⌨ Terminal
          {interactions.some((interaction) => !interaction.answered) ? (
            <span className="ml-2 rounded-full bg-amber-500 px-1.5 text-xs text-white">
              ?
            </span>
          ) : null}
        </button>
      </nav>
      <main className="flex-1 overflow-auto p-6">
        {/* Alle Views bleiben gemountet (nur inaktive versteckt): Tab-Wechsel
            ist damit sofortig und der Fetch-State bleibt erhalten. */}
        {SECTIONS.map((s) => (
          <div key={s.id} className={active === s.id ? "" : "hidden"}>
            <h2 className="mb-4 text-xl font-semibold">{s.label}</h2>
            {s.view}
          </div>
        ))}
      </main>
      <aside
        className={`${sidebarVisible ? "flex" : "hidden"} w-[520px] shrink-0 flex-col border-l border-slate-700 bg-slate-900`}
      >
        <AskBoPanel interactions={interactions} onAnswer={answerInteraction} />
        {terminalStarted ? (
          <TerminalPanel
            visible={sidebarVisible}
            session={sessionRequest}
            onOpened={terminalOpened}
            onFailed={terminalFailed}
          />
        ) : (
          <div className="flex flex-1 items-center justify-center p-4">
            <SessionChoice
              state={sessionState}
              command={dashboardCommand}
              record={sessionRecord}
              error={startError}
              onStart={startTerminal}
            />
          </div>
        )}
      </aside>
    </div>
  );
}
