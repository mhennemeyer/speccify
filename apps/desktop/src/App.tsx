import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import AskBoPanel, { type AskBoInteraction } from "./components/AskBoPanel";
import TerminalPanel from "./components/TerminalPanel";
import ComposerView from "./views/ComposerView";
import LibraryView from "./views/LibraryView";
import EnvironmentView from "./views/EnvironmentView";
import ServersView from "./views/ServersView";
import SettingsView from "./views/SettingsView";
import KnowledgebasesView from "./views/KnowledgebasesView";

const SECTIONS = [
  { id: "composer", label: "Composer", view: <ComposerView /> },
  { id: "library", label: "Bibliothek", view: <LibraryView /> },
  { id: "knowledgebases", label: "Knowledgebases", view: <KnowledgebasesView /> },
  { id: "environment", label: "Umgebung", view: <EnvironmentView /> },
  { id: "servers", label: "Server", view: <ServersView /> },
  { id: "settings", label: "Settings", view: <SettingsView /> },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

export default function App() {
  const [active, setActive] = useState<SectionId>("composer");
  const [sidebarVisible, setSidebarVisible] = useState(false);
  // Terminal erst beim ersten Öffnen über den Toggle mounten (sonst liefe
  // der Autostart-Command schon beim App-Start); danach gemountet lassen —
  // die Shell überlebt das Ein-/Ausklappen. ask_bo öffnet nur die Sidebar,
  // startet aber KEIN Terminal.
  const [terminalStarted, setTerminalStarted] = useState(false);
  const [interactions, setInteractions] = useState<AskBoInteraction[]>([]);

  const toggleTerminal = () => {
    setTerminalStarted(true);
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
      <nav className="flex w-48 flex-col border-r border-slate-200 bg-white p-3">
        <h1 className="mb-4 px-2 text-sm font-bold tracking-wide text-slate-500">
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
          <TerminalPanel visible={sidebarVisible} />
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <button
              onClick={() => setTerminalStarted(true)}
              className="rounded bg-slate-700 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-600"
            >
              Terminal starten
            </button>
          </div>
        )}
      </aside>
    </div>
  );
}
