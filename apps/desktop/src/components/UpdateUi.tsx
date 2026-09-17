import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import Markdown from "./Markdown";
import { installUpdateGuard, useUpdateSnapshot } from "../lib/updates";

export default function UpdateUi({ notifications = true }: { notifications?: boolean }) {
  const { snapshot: state, refresh } = useUpdateSnapshot();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string>();
  const [acting, setActing] = useState(false);
  useEffect(installUpdateGuard, []);
  useEffect(() => {
    const show = () => setOpen(true);
    window.addEventListener("speccify:updates", show);
    return () => window.removeEventListener("speccify:updates", show);
  }, []);
  if (!state) return null;
  const busy = acting || ["checking", "downloading", "preparing", "installing"].includes(state.phase);
  const run = async (command: string, args?: Record<string, unknown>) => {
    setError(undefined); setActing(true);
    try { await invoke(command, args); } catch (e) { setError(String(e)); }
    finally { await refresh().catch(() => {}); setActing(false); }
  };
  const available = !!state.version && state.phase !== 'current';
  return <div data-update-ui>
    {notifications && available && !open && <button
      className="fixed bottom-3 right-3 z-50 rounded-lg border border-blue-400 bg-blue-700 px-3 py-2 text-sm text-white shadow-lg"
      onClick={() => setOpen(true)}>Update {state.version}{state.phase === 'ready' ? ' bereit' : ' verfügbar'}</button>}
    {open && <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 p-6">
      <section role="dialog" aria-modal="true" aria-label="Speccify-Updates" className="flex max-h-[85vh] w-full max-w-xl flex-col rounded-xl bg-white p-5 text-slate-900 shadow-xl">
        <div className="flex shrink-0 items-center justify-between"><h2 className="text-lg font-semibold">Speccify-Updates</h2>
          <button onClick={() => setOpen(false)} aria-label="Updates schließen">Schließen</button></div>
        <div className="min-h-0 flex-1 overflow-auto">
        <p className="mt-2 text-sm">Installiert: {state.current_version}</p>
        {!state.supported && <p className="my-3 text-sm">{state.reason}</p>}
        <label className="mt-4 flex gap-2 text-sm"><input type="checkbox" checked={state.preferences.automatic} disabled={!state.supported || busy}
          onChange={e => void run('update_preferences', { preferences: { ...state.preferences, automatic: e.target.checked } })} />Automatisch nach Updates suchen</label>
        <label className="mt-2 flex items-center gap-2 text-sm">Suchintervall
          <select aria-label="Update-Suchintervall" value={state.preferences.interval_hours} disabled={!state.supported || busy}
            onChange={e => void run('update_preferences', { preferences: { ...state.preferences, interval_hours: Number(e.target.value) } })}>
            <option value={6}>Alle 6 Stunden</option><option value={24}>Täglich</option><option value={168}>Wöchentlich</option>
          </select></label>
        <p className="my-2 text-xs text-slate-500">Automatische Suche beim Start und im gewählten Intervall. Installiert wird erst nach Deinem Klick.</p>
        <button className="my-2 rounded border px-3 py-1" disabled={!state.supported || busy} onClick={() => void run('update_check')}>Jetzt suchen</button>
        {state.last_checked && <p className="text-xs text-slate-500">Letzter Suchversuch: {new Date(state.last_checked * 1000).toLocaleString()}</p>}
        {state.phase === 'checking' && <p role="status">Updates werden gesucht…</p>}
        {state.phase === 'current' && <p role="status">Speccify ist aktuell.</p>}
        {available && <div className="mt-3 border-t pt-3">
          <h3 className="font-semibold">Version {state.version}</h3>
          {state.notes && <div className="my-3 max-h-56 overflow-auto"><Markdown text={state.notes} /></div>}
          {state.phase === 'downloading' ? <>
            <progress aria-label="Update-Download" className="w-full" max={state.total ?? undefined} value={state.total ? state.downloaded : undefined} />
            <p role="status">{(state.downloaded / 1e6).toFixed(1)} MB geladen{state.total ? ` von ${(state.total / 1e6).toFixed(1)} MB` : ''}</p>
            <button className="mt-2 rounded border px-3 py-1" onClick={() => void invoke('update_cancel')}>Download abbrechen</button>
          </> : state.phase === 'ready' ? <>
            <p className="my-2 text-sm">Download und Signatur geprüft. Bitte Editoransichten speichern und schließen sowie Terminals und Aktionen beenden. Alle Fenster werden vor dem Neustart geprüft.</p>
            <button className="rounded bg-blue-700 px-3 py-2 text-white" disabled={busy} onClick={() => void run('update_install')}>Installieren und neu starten</button>
          </> : <button className="rounded border px-3 py-1" disabled={busy} onClick={() => void run('update_download')}>Update herunterladen</button>}
        </div>}
        </div>
        {(error || state.error) && <p role="alert" className="mt-3 max-h-40 shrink-0 overflow-auto whitespace-pre-wrap rounded bg-red-50 p-3 text-sm text-red-800">{error || state.error}</p>}
      </section>
    </div>}
  </div>;
}
