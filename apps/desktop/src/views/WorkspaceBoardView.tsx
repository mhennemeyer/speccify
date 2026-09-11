import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { invoke } from "@tauri-apps/api/core";
import Markdown from "../components/Markdown";
import { ErrorBox } from "../components/ui";
import type { SpecEntry } from "./project/BoardTab";

export interface WorkspaceSpecEntry {
  key: string; project_id: string; project_name: string;
  repository_id: string; repository_name: string;
  worktree_id: string; worktree_path: string; worktree_label: string;
  spec: SpecEntry;
}
interface Snapshot { workspace_id: string; revision: number; captured_at: number; specs: WorkspaceSpecEntry[]; warnings: string[]; partial: boolean }
const button = "rounded border border-slate-300 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-100 disabled:opacity-40";
const tones: Record<string, string> = { Backlog: "slate", Doing: "blue", Done: "green" };

export default function WorkspaceBoardView({ workspaceId, revision, refresh = 0, onSelect, listSlots }: {
  workspaceId: string; revision: number; refresh?: number; onSelect?: (entry: WorkspaceSpecEntry | null, focus?: boolean) => void; listSlots?: Record<string, HTMLElement | null>;
}) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [reload, setReload] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);
  const [opening, setOpening] = useState(false);
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    setLoading(true); setError(null);
    void invoke<Snapshot>("workspace_board", { workspaceId }).then(value => {
      if (!cancelled) {
        if (value.workspace_id !== workspaceId) { setError("Workspace-Antwort gehört zu einem anderen Kontext."); return; }
        setSnapshot(value);
      }
    }).catch(e => { if (!cancelled) setError(String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [workspaceId, revision, reload, refresh]);
  const data = snapshot?.workspace_id === workspaceId ? snapshot : null;
  const projects = [...new Map(data?.specs.map(entry => [entry.project_id, entry.project_name]) ?? []).entries()].sort((a,b) => a[1].localeCompare(b[1]));
  const query = search.trim().toLocaleLowerCase();
  const visible = (data?.specs ?? []).filter(entry => (!filter || entry.project_id === filter) &&
    [entry.spec.title, entry.spec.id, entry.spec.file, entry.project_name, entry.repository_name, entry.worktree_label].some(value => value.toLocaleLowerCase().includes(query)))
    .sort((a,b) => (a.spec.order ?? Infinity) - (b.spec.order ?? Infinity) || a.project_name.localeCompare(b.project_name) || a.spec.id.localeCompare(b.spec.id) || a.key.localeCompare(b.key));
  const detail = visible.find(entry => entry.key === selected);
  useEffect(() => { onSelect?.(detail ?? null); }, [detail, onSelect]);
  const stations = [...new Set(["Backlog", "Doing", "Done", ...visible.map(entry => entry.spec.station)])];
  const choose = (key: string) => { setSelected(key); setOpenError(null); onSelect?.(visible.find(entry => entry.key === key) ?? null, true); };
  const open = async (entry: WorkspaceSpecEntry) => {
    setOpening(true); setOpenError(null);
    try { await invoke("workspace_open", { workspaceId, worktreeId: entry.worktree_id }); }
    catch (e) { setOpenError(String(e)); }
    finally { setOpening(false); }
  };
  return <section aria-label="Workspace-Specs" className="min-w-0 space-y-3">
    <div className="flex flex-wrap items-end gap-3">
      <label className="text-xs text-slate-500">Projekt
        <select aria-label="Board-Projekt" value={filter} onChange={event => setFilter(event.target.value)} className="ml-2 max-w-full rounded border border-slate-300 bg-white p-2 text-slate-800">
          <option value="">Alle Projekte</option>
          {projects.map(([id,name]) => <option key={id} value={id}>{name}</option>)}
          {filter && !projects.some(([id]) => id === filter) && <option value={filter}>Projekt nicht mehr im Snapshot</option>}
        </select>
      </label>
      <input aria-label="Workspace-Specs suchen" placeholder="Specs, Projekte, Repos suchen…" value={search} onChange={event => setSearch(event.target.value)} className="min-w-40 flex-1 rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800" />
      <button className={button} disabled={loading} onClick={() => setReload(value => value + 1)}>Board aktualisieren</button>
    </div>
    <p role="status" className="text-xs text-slate-500">{loading ? "Snapshot laden…" : `${visible.length} von ${data?.specs.length ?? 0} Specs`}
      {data && ` · Stand ${new Date(data.captured_at).toLocaleTimeString()}`}. {onSelect ? "Gemeinsames lokales Board. Bearbeitung im Inspektor betrifft nur das gekennzeichnete Projekt; kein Team-Sync." : "Lesende lokale Übersicht, kein Team-Sync. Änderungen nach Aktualisieren sichtbar."}</p>
    {error && <ErrorBox message={`${error}${data ? " · Letzten Snapshot anzeigen, möglicherweise veraltet." : ""}`} />}
    {data && data.revision !== revision && <p role="status" className="text-xs text-amber-700">Projektzuordnung inzwischen geändert. Board und Workspace erneut aktualisieren.</p>}
    {data?.partial && <aside role="status" data-tone="amber" className="tone-surface rounded border p-3 text-xs"><strong>Board unvollständig</strong><ul className="mt-1 list-inside list-disc break-all">{data.warnings.map((warning,index) => <li key={index}>{warning}</li>)}</ul></aside>}
    {!loading && !error && visible.length === 0 && <p className="text-sm text-slate-500">Keine Specs für diese Auswahl. Projektfilter oder Suche prüfen.</p>}
    <div className={listSlots ? "min-w-0" : "grid min-w-0 gap-3 xl:grid-cols-[12rem_minmax(0,1fr)]"}>
      {listSlots ? Object.entries(listSlots).map(([id, slot]) => slot && createPortal(<div aria-label={`Specs ${id}`}>
        {visible.filter(entry => entry.worktree_id === id).map(entry => <button key={entry.key} aria-pressed={selected === entry.key} onClick={() => choose(entry.key)} data-tone="violet" className={`mb-1 block w-full rounded p-2 text-left text-xs ${selected === entry.key ? "tone-surface" : "text-slate-700 hover:bg-slate-100"}`}>{entry.spec.id} · {entry.spec.title}</button>)}
      </div>, slot, id)) : <aside aria-label="Workspace-Spec-Liste" className="max-h-96 overflow-auto rounded border border-slate-200 bg-white p-2">
        {visible.map(entry => <button key={entry.key} aria-pressed={selected === entry.key} onClick={() => choose(entry.key)} data-tone="violet"
          className={`mb-1 block w-full rounded p-2 text-left text-xs ${selected === entry.key ? "tone-surface" : "text-slate-700 hover:bg-slate-100"}`}>
          <span className="block font-medium">{entry.spec.id} · {entry.spec.title}</span>
          <span className="mt-1 block break-all text-[11px]">{entry.project_name} / {entry.repository_name} / {entry.worktree_label || "."}</span>
        </button>)}
      </aside>}
      <div aria-label="Workspace-Board" className="grid min-w-0 gap-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 13rem), 1fr))" }}>
        {stations.map(station => <section key={station} aria-label={`Workspace-Spalte ${station}`} data-tone={tones[station] ?? "slate"} className="min-w-0 rounded-lg border border-slate-200 bg-slate-50 p-2">
          <h3 className="mb-2 text-sm font-semibold text-slate-700">{station} <span className="text-xs font-normal">{visible.filter(entry => entry.spec.station === station).length}</span></h3>
          {visible.filter(entry => entry.spec.station === station).map(entry => <button key={entry.key} data-workspace-spec={entry.key} aria-pressed={selected === entry.key} onClick={() => choose(entry.key)}
            className={`mb-2 block w-full min-w-0 rounded border p-3 text-left text-sm ${selected === entry.key ? "tone-surface" : "border-slate-200 bg-white text-slate-800 hover:border-slate-400"}`}>
            <span className="block text-[11px]">{entry.spec.id}</span><span className="block font-semibold">{entry.spec.title}</span>
            <span data-tone="violet" className="tone-surface mt-2 block break-words rounded px-2 py-1 text-[11px]">{entry.project_name}</span>
            <span className="mt-1 block break-all text-[11px]">{entry.repository_name} · {entry.worktree_label || "."}</span>
            <span className="mt-2 block text-xs">{entry.spec.tasks_done}/{entry.spec.tasks_total} Aufgaben{entry.spec.ready && entry.spec.needs_human ? " · Abnahme offen" : ""}{entry.spec.open_question ? ` · Frage ${entry.spec.open_question}` : ""}{entry.spec.archived ? " · Altbestand" : ""}</span>
          </button>)}
        </section>)}
      </div>
    </div>
    {detail && !onSelect && <article aria-label="Workspace-Spec-Vorschau" className="min-w-0 rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="font-semibold text-slate-800">{detail.spec.title}</h3>
      <p className="mt-1 break-all text-xs text-slate-500">{detail.project_name} / {detail.repository_name} / {detail.worktree_label || "."}<br />{detail.worktree_path}/{detail.spec.file}</p>
      <p className="my-2 text-xs text-slate-500">Nur lesen. Bearbeitung und Abnahme im zugehörigen Projektfenster; dort diese Datei auswählen.</p>
      <button className={button} disabled={opening} onClick={() => void open(detail)}>Projektfenster öffnen: {detail.worktree_label || "."} ↗</button>
      {openError && <ErrorBox message={openError} />}
      <div className="mt-4 max-h-96 overflow-auto"><Markdown text={detail.spec.body} /></div>
    </article>}
  </section>;
}
