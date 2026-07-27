import { useState } from "react";
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
  const [terminalVisible, setTerminalVisible] = useState(false);
  // Erst beim ersten Öffnen mounten (sonst liefe der Autostart-Command
  // schon beim App-Start); danach gemountet lassen — Shell überlebt Toggle.
  const [terminalStarted, setTerminalStarted] = useState(false);

  const toggleTerminal = () => {
    setTerminalStarted(true);
    setTerminalVisible((current) => !current);
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
            terminalVisible
              ? "bg-slate-800 text-white"
              : "text-slate-700 hover:bg-slate-100"
          }`}
        >
          ⌨ Terminal
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
      {terminalStarted ? <TerminalPanel visible={terminalVisible} /> : null}
    </div>
  );
}
