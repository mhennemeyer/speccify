import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import AgentsView from "../views/AgentsView";

export default function AgentSettingsDialog() {
  const [open, setOpen] = useState(false);
  const [discard, setDiscard] = useState(false);
  const panel = useRef<HTMLDivElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { if (open) dialog.current?.showModal(); }, [open]);
  const close = () => {
    if (panel.current?.querySelector('[data-update-dirty="true"]')) setDiscard(true);
    else setOpen(false);
  };
  return <>
    <button className="rounded border border-slate-300 px-3 py-1.5 text-xs text-slate-700" onClick={() => setOpen(true)}>Agent-Einstellungen</button>
    {open && createPortal(<dialog ref={dialog} aria-label="Agent-Einstellungen"
      onCancel={event => { event.preventDefault(); close(); }}
      className="m-auto w-[calc(100vw-2rem)] max-w-5xl rounded-xl border-0 bg-transparent p-0 backdrop:bg-black/30">
      <div ref={panel} className="flex h-[90vh] w-full max-w-5xl flex-col gap-3 rounded-xl bg-white p-5 text-slate-800 shadow-xl">
        <div className="flex items-center justify-between"><h2 className="font-semibold">Agent-Einstellungen</h2>
          <button className="rounded border px-3 py-1 text-sm" onClick={close}>Schließen</button></div>
        {discard && <div role="alert" className="rounded border border-amber-300 p-3 text-sm">Ungespeicherte Änderungen verwerfen?
          <button className="ml-3 underline" onClick={() => { setDiscard(false); setOpen(false); }}>Verwerfen und schließen</button>
          <button className="ml-3 underline" onClick={() => setDiscard(false)}>Weiter bearbeiten</button>
        </div>}
        <div className="min-h-0 flex-1"><AgentsView /></div>
      </div>
    </dialog>, document.body)}
  </>;
}
