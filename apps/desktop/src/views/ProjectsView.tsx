// Projekte-Tab im Dashboard (Plan projektfenster.md, P1; ersetzt den
// Composer-Tab, D18): Projektverzeichnis wählen → eigenes Projektfenster.

import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { ActionButton, ErrorBox, useAsync } from "../components/ui";

export default function ProjectsView() {
  const [path, setPath] = useState("");
  const [error, setError] = useState<string | null>(null);
  const recent = useAsync(() => invoke<string[]>("project_recent"), "recent-projects");

  const openProject = async (target: string) => {
    setError(null);
    try {
      await invoke<string>("project_open", { path: target });
      await recent.reload();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="max-w-xl space-y-4">
      <p className="text-sm text-slate-600">
        Öffnet ein Projekt in einem eigenen Fenster: links Board, Pläne, Skills
        und Tools des Projekts, rechts der Inspektor, unten ein Agent-Terminal im
        Projektverzeichnis.
      </p>
      <div>
        <label
          htmlFor="project-path"
          className="mb-1 block text-xs font-medium text-slate-500"
        >
          Projektverzeichnis
        </label>
        <div className="flex gap-2">
          <input
            id="project-path"
            value={path}
            onChange={(event) => setPath(event.target.value)}
            placeholder="~/Projekte/mein-projekt"
            className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm"
            spellCheck={false}
          />
          <button
            onClick={async () => {
              const picked = await open({
                directory: true,
                title: "Projektverzeichnis wählen",
              });
              if (typeof picked === "string") {
                setPath(picked);
                await openProject(picked);
              }
            }}
            className="shrink-0 rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
            title="Verzeichnis wählen und öffnen"
          >
            Auswählen…
          </button>
        </div>
      </div>
      <ActionButton
        onClick={() => openProject(path)}
        className="bg-slate-800 text-white hover:bg-slate-700"
      >
        Projekt öffnen
      </ActionButton>
      {error ? <ErrorBox message={error} /> : null}
      {(recent.data ?? []).length > 0 ? (
        <div>
          <h3 className="mb-1 text-xs font-semibold text-slate-500">
            Zuletzt geöffnet
          </h3>
          <ul className="space-y-1">
            {(recent.data ?? []).map((entry) => (
              <li key={entry}>
                <button
                  onClick={() => void openProject(entry)}
                  className="w-full truncate rounded px-2 py-1.5 text-left font-mono text-xs text-slate-700 hover:bg-slate-100"
                  title={entry}
                >
                  {entry}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
