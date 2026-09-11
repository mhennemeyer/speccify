// Gespeicherte Workspaces im Projekte-Tab (Specs 015/024/026). Neue Workspaces
// entstehen seit Spec 027 über „Ordner öffnen“ (ProjectsView); hier bleiben
// Auswahl, erneutes Erkennen, Gruppen, Worktrees und das lesende Board.
import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { ErrorBox, useAsync } from "../components/ui";
import WorkspaceBoardView from "./WorkspaceBoardView";

export interface Worktree { id: string; path: string; relative_path: string; markers: string[]; available: boolean }
export interface Repository { id: string; name: string; common_dir: string | null; default_project_id: string; worktrees: Worktree[] }
export interface Project { id: string; name: string; repository_ids: string[] }
export interface Workspace { id: string; name: string; root: string; revision: number; projects: Project[]; repositories: Repository[]; warnings: string[]; partial: boolean }
type Edit = { kind: "rename"; project_id: string; name: string } | { kind: "group"; repository_ids: string[]; name: string } | { kind: "ungroup"; repository_id: string };
const selectionKey = "speccify.dashboard.workspace";
const button = "rounded border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-40";

/** `focus` wählt nach „Ordner öffnen“ den gerade gespeicherten Workspace; `token` erzwingt das Neuladen auch bei gleicher Id. */
export default function WorkspaceView({ focus }: { focus?: { id: string; token: number } | null }) {
  const list = useAsync(() => invoke<Workspace[]>("workspace_list"), "workspaces");
  const [active, setActive] = useState(() => { try { return localStorage.getItem(selectionKey) ?? ""; } catch { return ""; } });
  const [selected, setSelected] = useState<string[]>([]);
  const [groupName, setGroupName] = useState("");
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [mode, setMode] = useState<"projects" | "specs">("projects");
  const workspace = list.data?.find(entry => entry.id === active) ?? list.data?.[0];

  const select = (id: string) => {
    setActive(id); setSelected([]); setRenaming(null); setError(null); setNotice(null);
    try { localStorage.setItem(selectionKey, id); } catch { /* Selection remains usable without storage. */ }
  };
  useEffect(() => {
    if (!focus) return;
    let cancelled = false;
    void list.reload().then(() => { if (!cancelled) select(focus.id); });
    return () => { cancelled = true; };
    // `select` ist zustandslos außer über Setter; nur der Fokus löst neu aus.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus?.id, focus?.token]);
  const rescan = async (target: string) => {
    setBusy(true); setError(null); setNotice(null);
    try {
      const result = await invoke<Workspace>("workspace_discover", { path: target });
      await list.reload(); select(result.id);
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  };
  const edit = async (change: Edit) => {
    if (!workspace) return;
    setBusy(true); setError(null); setNotice(null);
    try {
      await invoke<Workspace>("workspace_edit", { workspaceId: workspace.id, expectedRevision: workspace.revision, change });
      await list.reload(); setSelected([]); setRenaming(null); setGroupName("");
      setNotice("Zuordnung gespeichert. Repository-Dateien und laufende Terminals bleiben unverändert.");
    } catch (e) {
      setError(String(e));
      if (String(e).includes("WORKSPACE_CHANGED")) { await list.reload(); setSelected([]); setRenaming(null); }
    } finally { setBusy(false); }
  };
  const openTree = async (tree: Worktree) => {
    setBusy(true); setError(null);
    try {
      await invoke("workspace_open", { workspaceId: workspace?.id, worktreeId: tree.id });
      setNotice(`Eigenes Projektfenster geöffnet: ${tree.path}. Bestehende Terminals behalten ihr Ziel.`);
    } catch (e) { setError(String(e)); }
    finally { setBusy(false); }
  };

  return <section aria-label="Workspaces" className="max-w-5xl space-y-4">
    <div>
      <h2 className="text-lg font-semibold text-slate-800">Gespeicherte Workspaces</h2>
      <p className="mt-1 max-w-3xl text-sm text-slate-500">Ein Arbeitsordner, mehrere Projekte: Repos und Worktrees fachlich gruppieren und gezielt öffnen. Specs gemeinsam überblicken; Dateien, Skills, Git und Terminals bleiben pro Worktree getrennt.</p>
    </div>
    {(error || list.error) && <ErrorBox message={error ?? list.error ?? ""} />}
    {notice && <p role="status" data-tone="green" className="tone-surface rounded p-3 text-xs">{notice}</p>}
    {list.loading && <p role="status" className="text-sm text-slate-500">Workspaces laden…</p>}
    {workspace ? <>
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-3">
        <label className="min-w-0 max-w-full text-xs text-slate-500">Gespeicherter Workspace
          <select aria-label="Gespeicherter Workspace" disabled={busy} value={workspace.id} onChange={event => select(event.target.value)} className="mt-1 block max-w-full rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-800">
            {list.data?.map(entry => <option key={entry.id} value={entry.id}>{entry.name} · {entry.root}</option>)}
          </select>
        </label>
        <button className={button} disabled={busy} onClick={() => void rescan(workspace.root)}>{busy ? "Bitte warten…" : "Erneut erkennen"}</button>
        <button data-tone="blue" className={`${button} tone-surface`} disabled={busy} onClick={async () => {
          setBusy(true); setError(null);
          try { await invoke("workspace_window_open", { workspaceId: workspace.id }); }
          catch (e) { setError(String(e)); }
          finally { setBusy(false); }
        }}>Workspace öffnen ↗</button>
        <span className="text-xs text-slate-500">{workspace.repositories.length} Repos/Ordner · {workspace.repositories.reduce((sum, repo) => sum + repo.worktrees.length, 0)} Worktrees</span>
        <p className="w-full break-all font-mono text-xs text-slate-500">{workspace.root}</p>
      </div>
      <nav aria-label="Workspace-Ansicht" className="flex gap-2">
        <button data-tone="violet" className={`${button} ${mode === "projects" ? "tone-surface" : ""}`} aria-pressed={mode === "projects"} onClick={() => setMode("projects")}>Projektgruppen</button>
        <button data-tone="violet" className={`${button} ${mode === "specs" ? "tone-surface" : ""}`} aria-pressed={mode === "specs"} onClick={() => setMode("specs")}>Alle Specs</button>
      </nav>
      {(workspace.partial || workspace.warnings.length > 0) && <aside role="status" data-tone="amber" className="tone-surface rounded border p-3 text-xs">
        <strong>{workspace.partial ? "Suche begrenzt" : "Hinweise zur Erkennung"}</strong>
        <ul className="mt-1 list-inside list-disc">{workspace.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>
        <p className="mt-1">Verfügbare Projekte können geöffnet werden. Bekannte Zuordnungen bleiben erhalten; nicht durchsuchte Unterordner bei Bedarf separat öffnen.</p>
      </aside>}
      {mode === "specs" ? <WorkspaceBoardView key={workspace.id} workspaceId={workspace.id} revision={workspace.revision} /> : <>
      <form onSubmit={event => { event.preventDefault(); void edit({ kind: "group", repository_ids: selected, name: groupName }); }} data-tone="violet" className="tone-surface flex flex-wrap items-center gap-2 rounded-lg border p-3">
        <span className="text-xs">{selected.length} ausgewählt</span>
        <input aria-label="Name der Projektgruppe" value={groupName} onChange={event => setGroupName(event.target.value)} disabled={busy} maxLength={100} placeholder="Gemeinsames Projekt, z. B. Kundenportal" className="min-w-64 flex-1 rounded border border-slate-300 bg-white px-2 py-1.5 text-sm" />
        <button className={`${button} tone-surface`} disabled={busy || selected.length < 2 || !groupName.trim()}>Als Projekt gruppieren</button>
      </form>
      {workspace.projects.filter(project => project.repository_ids.length > 0).map(project => <article key={project.id} data-project-id={project.id} className="rounded-lg border border-slate-200 bg-white p-4">
        <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
          {renaming === project.id ? <form className="flex gap-2" onSubmit={event => { event.preventDefault(); void edit({ kind: "rename", project_id: project.id, name: renameValue }); }}>
            <input autoFocus aria-label="Projektname" value={renameValue} onChange={event => setRenameValue(event.target.value)} maxLength={100} className="rounded border border-slate-300 px-2 py-1 text-sm" />
            <button className={button} disabled={busy || !renameValue.trim()}>Speichern</button>
            <button type="button" className={button} disabled={busy} onClick={() => setRenaming(null)}>Abbrechen</button>
          </form> : <>
            <h3 className="font-semibold text-slate-800">{project.name} <span data-tone="violet" className="tone-surface ml-2 rounded px-2 py-0.5 text-xs font-normal">{project.repository_ids.length} Repos/Ordner</span></h3>
            <button className={button} disabled={busy} onClick={() => { setRenaming(project.id); setRenameValue(project.name); }}>Umbenennen</button>
          </>}
        </header>
        <div className="space-y-3">{project.repository_ids.map(repoId => {
          const repo = workspace.repositories.find(entry => entry.id === repoId)!;
          return <div key={repo.id} data-repository-id={repo.id} className="rounded border border-slate-200 bg-slate-50 p-3">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700"><input type="checkbox" disabled={busy} checked={selected.includes(repo.id)} onChange={event => setSelected(previous => event.target.checked ? [...previous, repo.id] : previous.filter(id => id !== repo.id))} />{repo.name}
                <span className="text-xs font-normal text-slate-500">{repo.common_dir ? "Git" : "Ordner ohne Git"}{repo.worktrees.length > 1 ? ` · ${repo.worktrees.length} Worktrees, ein Repo` : ""}</span>
              </label>
              {project.id !== repo.default_project_id && <button className={button} disabled={busy} onClick={() => void edit({ kind: "ungroup", repository_id: repo.id })}>Aus Gruppe lösen</button>}
            </div>
            {repo.worktrees.map(tree => <div key={tree.id} className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 py-2">
              <div className="min-w-40 max-w-full flex-1"><p className="break-all font-mono text-xs text-slate-600" title={tree.path}>{tree.relative_path || "."}</p>
                <p className="mt-1 break-all text-[11px] text-slate-500">{tree.markers.join(" · ") || "Keine Projektanweisungen erkannt"}{!tree.available && " · Nicht verfügbar"}</p>
              </div>
              <button className={button} disabled={busy || !tree.available} title={tree.path} aria-label={`Worktree öffnen: ${tree.path}`} onClick={() => void openTree(tree)}>In eigenem Fenster öffnen ↗</button>
            </div>)}
          </div>;
        })}</div>
      </article>)}
      </>}
    </> : !list.loading && !list.error && <p className="rounded border border-dashed border-slate-300 p-6 text-sm text-slate-500">Noch kein Workspace gespeichert. Öffne oben einen Ordner, der mehrere Repositories oder Projekte enthält.</p>}
  </section>;
}
