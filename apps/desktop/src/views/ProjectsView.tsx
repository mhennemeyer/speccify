// Projekte-Tab im Dashboard (Spec 027): ein Einstieg „Ordner öffnen“. Die App
// erkennt nativ, ob der Ordner ein Einzelprojekt (eigenes Git-Repo oder
// einfacher Ordner) oder ein Workspace mit mehreren Repos/Projekten ist, und
// öffnet das passende Fenster. Gespeicherte Workspaces und zuletzt geöffnete
// Projekte bleiben darunter erreichbar.

import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { ErrorBox, useAsync } from "../components/ui";
import WorkspaceView, { type Workspace } from "./WorkspaceView";

type FolderOpened = { kind: "project"; root: string } | { kind: "workspace"; workspace: Workspace };
const button = "rounded border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-40";

export default function ProjectsView() {
  const [path, setPath] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [opened, setOpened] = useState<FolderOpened | null>(null);
  const [focus, setFocus] = useState<{ id: string; token: number } | null>(null);
  const recent = useAsync(() => invoke<string[]>("project_recent"), "recent-projects");

  const openFolder = async (target: string) => {
    setBusy(true); setError(null); setOpened(null);
    try {
      const result = await invoke<FolderOpened>("folder_open", { path: target });
      setOpened(result);
      if (result.kind === "project") {
        setPath(result.root);
        await recent.reload();
      } else {
        setPath(result.workspace.root);
        setFocus({ id: result.workspace.id, token: Date.now() });
      }
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  };

  const worktrees = (workspace: Workspace) => workspace.repositories.reduce((sum, repo) => sum + repo.worktrees.length, 0);

  return (
    <div className="space-y-8">
      <section aria-label="Ordner öffnen" className="max-w-5xl space-y-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Ordner öffnen</h2>
          <p className="mt-1 max-w-3xl text-sm text-slate-500">
            Ein Ordner genügt. Ist er selbst ein Git-Repository oder ein einfaches Projekt, öffnet sich sein
            Projektfenster. Enthält er mehrere Repositories oder Projekte, wird er als Workspace gespeichert und
            im gemeinsamen Arbeitsfenster geöffnet.
          </p>
        </div>
        <form className="flex flex-wrap items-end gap-2" onSubmit={event => { event.preventDefault(); void openFolder(path); }}>
          <label className="min-w-56 flex-1 text-xs text-slate-500">Ordner
            <input aria-label="Ordner" value={path} onChange={event => setPath(event.target.value)} placeholder="~/Projekte/mein-projekt oder ~/Projekte" spellCheck={false} disabled={busy}
              className="mt-1 block w-full rounded border border-slate-300 bg-white px-3 py-2 font-mono text-sm text-slate-800" />
          </label>
          <button type="button" className={button} disabled={busy} onClick={async () => {
            try {
              const picked = await open({ directory: true, title: "Ordner wählen" });
              if (typeof picked === "string") { setPath(picked); void openFolder(picked); }
            } catch (e) { setError(String(e)); }
          }}>Auswählen…</button>
          <button type="submit" disabled={busy || !path.trim()} data-tone="blue" className={`${button} tone-surface`}>{busy ? "Bitte warten…" : "Öffnen"}</button>
        </form>
        <p className="text-xs text-slate-500">Workspace-Erkennung: 16 Ebenen, ohne Symlinks, Abhängigkeits- und Buildordner. Keine Git- oder Projektdateien werden verändert.</p>
        {error && <ErrorBox message={error} />}
        {opened?.kind === "project" && <p role="status" data-tone="green" className="tone-surface rounded p-3 text-xs">Einzelprojekt erkannt. Projektfenster geöffnet: <span className="font-mono">{opened.root}</span></p>}
        {opened?.kind === "workspace" && <p role="status" data-tone="green" className="tone-surface rounded p-3 text-xs">Workspace erkannt: {opened.workspace.repositories.length} Repos/Ordner · {worktrees(opened.workspace)} Worktrees. Arbeitsfenster geöffnet; Projektgruppen unten anpassen.</p>}
        {(recent.data ?? []).length > 0 && (
          <div>
            <h3 className="mb-1 text-xs font-semibold text-slate-500">Zuletzt geöffnete Projekte</h3>
            <ul className="space-y-1">
              {(recent.data ?? []).map(entry => (
                <li key={entry}>
                  <button disabled={busy} onClick={() => void openFolder(entry)} className="w-full truncate rounded px-2 py-1.5 text-left font-mono text-xs text-slate-700 hover:bg-slate-100 disabled:opacity-40" title={entry}>{entry}</button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
      <WorkspaceView focus={focus} />
    </div>
  );
}
