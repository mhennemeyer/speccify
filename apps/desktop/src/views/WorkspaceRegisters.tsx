import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { ErrorBox } from "../components/ui";

interface Identity { id: string; name: string }
interface Manifest { version: number; id: string; name: string; sources: Identity[]; repositories: Identity[]; default_source: string | null }
interface Binding { manifest: Manifest; bindings: Record<string, string[]> }
export interface RegisterTarget { id: string; name: string; path: string }
const button = "rounded border border-slate-300 px-3 py-1 text-xs disabled:opacity-40";

export default function WorkspaceRegisters({ workspaceId, name, targets, onChanged, onCreate }: {
  workspaceId: string; name: string; targets: RegisterTarget[]; onChanged: () => void; onCreate: (id: string) => void;
}) {
  const [saved, setSaved] = useState<Binding | null>(null);
  const [manifest, setManifest] = useState("");
  const [bindings, setBindings] = useState<Record<string, string[]>>({});
  const [storage, setStorage] = useState("");
  const [destination, setDestination] = useState("");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    let stopped = false;
    void invoke<Binding | null>("workspace_registers", { workspaceId }).then(value => {
      if (!stopped) { setSaved(value); setDestination(value?.manifest.default_source ?? ""); }
    }).catch(e => { if (!stopped) setError(String(e)); }).finally(() => { if (!stopped) setLoaded(true); });
    return () => { stopped = true; };
  }, [workspaceId]);
  const edit = () => {
    const sources = targets.map(target => ({ id: `register-${crypto.randomUUID()}`, name: target.name }));
    const value = saved ?? { manifest: { version: 1, id: workspaceId, name, sources, repositories: sources.map(source => ({ id: source.id.replace("register-", "repo-"), name: source.name })), default_source: null }, bindings: Object.fromEntries(sources.map((source, index) => [source.id, [targets[index].id]])) };
    setManifest(JSON.stringify(value.manifest, null, 2)); setBindings(value.bindings); setEditing(true); setError(null);
  };
  let parsed: Manifest | null = null;
  try { const value = JSON.parse(manifest); if (Array.isArray(value.sources) && value.sources.every((source: Identity) => typeof source.id === "string" && typeof source.name === "string")) parsed = value; } catch { /* Native save validates the complete portable contract. */ }
  const choices = saved ? saved.manifest.sources.map(source => ({ id: source.id, name: source.name, tree: saved.bindings[source.id]?.[0] })) : targets.map(target => ({ ...target, tree: target.id }));
  const operation = async (action: () => Promise<void>) => { setBusy(true); setError(null); try { await action(); } catch (e) { setError(String(e)); } finally { setBusy(false); } };
  return <section aria-label="Registerquellen" className="mb-3 space-y-2 rounded border border-slate-200 p-2 text-xs">
    <div className="flex flex-wrap items-center gap-2">
      <button className={button} disabled={!loaded || busy} onClick={edit}>Registerquellen…</button>
      <label>Neue Spec in <select aria-label="Kanonisches Register" className="ml-1 rounded border bg-white p-1" value={destination} onChange={e => setDestination(e.target.value)}>
        <option value="">Speicherort wählen…</option>{choices.map(choice => <option key={choice.id} value={choice.id}>{choice.name}</option>)}
      </select></label>
      <button className={button} disabled={!loaded || busy || !choices.find(choice => choice.id === destination)?.tree} onClick={() => { const tree = choices.find(choice => choice.id === destination)?.tree; if (tree) onCreate(tree); }}>+ Übergreifende Spec</button>
      <span>{saved ? `${saved.manifest.sources.length} gebundene Register · ${saved.manifest.name}` : "Lokale Quellen · noch keine gemeinsame Registerbindung"}</span>
    </div>
    {error && <ErrorBox message={error} />}
    {editing && <div role="dialog" aria-label="Registerquellen bearbeiten" className="space-y-3 border-t pt-3">
      <p>Geteilte Register-IDs und Code-Repo-IDs bleiben auf allen Rechnern gleich. Lokale Checkouts werden hier zugeordnet. Der erste Checkout ist das Schreibziel. Weitere Checkouts dienen dem Vergleich.</p>
      <label className="block">Geteiltes Manifest<textarea aria-label="Registermanifest" className="mt-1 block w-full rounded border p-2 font-mono" rows={8} value={manifest} onChange={e => setManifest(e.target.value)} /></label>
      {parsed?.sources.map(source => <div key={source.id} className="space-y-1"><strong>{source.name}</strong> <code>{source.id}</code>
        <select aria-label={`Schreibziel ${source.name}`} className="ml-2 rounded border bg-white p-1" value={bindings[source.id]?.[0] ?? ""} onChange={e => setBindings(old => ({ ...old, [source.id]: e.target.value ? [e.target.value, ...(old[source.id] ?? []).filter(id => id !== e.target.value)] : [] }))}>
          <option value="">Lokalen Checkout wählen…</option>{targets.map(target => <option key={target.id} value={target.id}>{target.name} · {target.path}</option>)}
        </select>
        <div className="flex flex-wrap gap-2">{targets.filter(target => target.id !== bindings[source.id]?.[0]).map(target => <label key={target.id}><input type="checkbox" checked={(bindings[source.id] ?? []).includes(target.id)} onChange={e => setBindings(old => ({ ...old, [source.id]: e.target.checked ? [...(old[source.id] ?? []), target.id] : (old[source.id] ?? []).filter(id => id !== target.id) }))} /> {target.name} vergleichen</label>)}</div>
      </div>)}
      <label className="block">Manifest in vorhandenem Register <select aria-label="Manifest-Speicherort" className="ml-1 rounded border bg-white p-1" value={storage} onChange={e => setStorage(e.target.value)}><option value="">Nur lokale Bindung speichern</option>{targets.map(target => <option key={target.id} value={target.id}>{target.name}</option>)}</select></label>
      <div className="flex gap-2">
        <button className={button} disabled={!storage || busy} onClick={() => void operation(async () => { const value = await invoke<Manifest>("workspace_register_import", { workspaceId, worktreeId: storage }); setManifest(JSON.stringify(value, null, 2)); setBindings({}); })}>Manifest von dort laden</button>
        <button className={button} disabled={!parsed || busy} onClick={() => void operation(async () => { const selectedBindings = Object.fromEntries((parsed?.sources ?? []).map(source => [source.id, bindings[source.id] ?? []])); const value = await invoke<Binding>("workspace_register_save", { workspaceId, manifest, bindings: selectedBindings, exportTarget: storage || null }); setSaved(value); setDestination(value.manifest.default_source ?? ""); setEditing(false); onChanged(); })}>Bindung speichern{storage ? " und Manifest teilen" : ""}</button>
        <button className={button} disabled={busy} onClick={() => setEditing(false)}>Abbrechen</button>
      </div>
      <p>Das Manifest enthält keine lokalen Pfade oder Zugangsdaten. Ein Export schreibt ausschließlich workspace-registers.json in das gewählte Register. Bestehende Specs werden nicht verschoben.</p>
    </div>}
  </section>;
}
