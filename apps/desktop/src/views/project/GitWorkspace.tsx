import { useRef, useState, type RefObject } from "react";
import { clearDraft, draftKey, readDraft, writeDraft } from "../../lib/autosave";
import type { GitBranch, GitStatus } from "../../lib/git";

export type BranchAction = "switch" | "create" | "rename" | "delete";
const button = "rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-100 disabled:opacity-40";
const field = "w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-xs";

/** Persistent controls live in the content area, never in a selection inspector. */
export default function GitWorkspace({ project, status, branches, stagedCount, busy,
  showBranches, setShowBranches, messageRef, onCommit, onBranch, onAgent,
}: {
  project: string; status: GitStatus; branches: GitBranch[]; stagedCount: number; busy: boolean;
  showBranches: boolean; setShowBranches: (open: boolean) => void;
  messageRef: RefObject<HTMLInputElement | null>;
  onCommit: (message: string) => Promise<boolean>;
  onBranch: (action: BranchAction, branch: string, name: string) => Promise<boolean>;
  onAgent: () => void;
}) {
  const key = draftKey(project, "git-commit");
  const [message, setMessage] = useState(() => readDraft(key) ?? "");
  const [draftSaved, setDraftSaved] = useState(true);
  const [query, setQuery] = useState("");
  const [pending, setPending] = useState<{ action: BranchAction; branch: string; from: string | null } | null>(null);
  const [name, setName] = useState("");
  const submitting = useRef(false);
  const [subject, ...rest] = message.split("\n");
  const body = rest.join("\n").replace(/^\n/, "");
  const edit = (subject: string, body: string) => {
    const next = subject + (body ? `\n\n${body}` : "");
    writeDraft(key, next);
    setDraftSaved(readDraft(key) === next);
    setMessage(next);
  };
  const reason = busy ? "Git-Aktion läuft…" : !subject.trim() ? "Bitte einen Betreff eingeben."
    : stagedCount === 0 ? "Erst Dateien oder Hunks stagen (+ in der Liste)."
    : status.entries.some(entry => entry.conflicted) ? "Zuerst die Konflikte auflösen." : null;
  const submit = async () => {
    if (reason || submitting.current) return;
    submitting.current = true;
    try {
      if (await onCommit(message)) { clearDraft(key); setMessage(""); }
    } finally { submitting.current = false; }
  };
  const choose = (action: BranchAction, branch = "") => {
    setPending({ action, branch, from: status.branch });
    setName(action === "rename" ? branch : "");
  };
  const branchChanged = !!pending && pending.from !== status.branch;
  const needsName = pending?.action === "create" || pending?.action === "rename";
  const perform = async () => {
    if (!pending || busy || submitting.current || branchChanged || (needsName && !name.trim())) return;
    submitting.current = true;
    try {
      if (await onBranch(pending.action, pending.branch, name.trim())) setPending(null);
    } finally { submitting.current = false; }
  };

  return (
    <section aria-label="Git-Arbeitsbereich" className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Repository / Worktree</p>
          <p className="break-all font-mono text-xs text-slate-600">{project}</p>
        </div>
        <button data-tone="blue" className="tone-surface rounded border px-3 py-1.5 text-xs font-semibold"
          aria-expanded={showBranches} aria-controls="git-branches" onClick={() => setShowBranches(!showBranches)}>
          ⎇ {status.branch ?? "Detached HEAD"} · Branches {showBranches ? "▴" : "▾"}
        </button>
      </div>
      <form aria-label="Commit erstellen" onSubmit={event => { event.preventDefault(); void submit(); }}
        onKeyDown={event => { if ((event.metaKey || event.ctrlKey) && event.key === "Enter") { event.preventDefault(); void submit(); } }}>
        <label className="block text-xs font-semibold text-slate-700">Commit-Betreff
          <input ref={messageRef} value={subject} disabled={busy} onChange={event => edit(event.target.value, body)}
            placeholder="feat: …" spellCheck={false} className={`${field} mt-1 font-mono`} />
        </label>
        <label className="mt-2 block text-[11px] text-slate-500">Beschreibung (optional)
          <textarea value={body} disabled={busy} onChange={event => edit(subject, event.target.value)} rows={2}
            placeholder="Was ändert sich und warum?" spellCheck={false} className={`${field} mt-1 font-mono`} />
        </label>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <button type="submit" data-tone="green" disabled={!!reason}
            className="tone-surface rounded border px-3 py-1.5 text-xs font-semibold disabled:opacity-40">
            {stagedCount} gestagete Datei(en) committen
          </button>
          <button type="button" className={button} disabled={busy} onClick={onAgent}>Commit-Auftrag ans Terminal</button>
          <span className="text-[11px] text-slate-500">Nur Index · kein Push · ⌘/Ctrl+Enter</span>
        </div>
        <p className="mt-2 text-[11px] text-slate-500" role="status">
          {reason ?? "Bereit zum Commit. Nicht gestagete Änderungen bleiben unangetastet."}
          {message ? draftSaved ? " Entwurf lokal gesichert." : " Lokaler Speicher nicht verfügbar: Entwurf vor Neustart kopieren." : ""}
        </p>
        {stagedCount > 0 ? <details className="mt-2 text-xs text-slate-600">
          <summary className="cursor-pointer">Index prüfen ({stagedCount} Dateien)</summary>
          <ul className="mt-1 max-h-24 overflow-y-auto font-mono text-[11px]">
            {status.entries.filter(entry => !entry.untracked && !entry.conflicted && entry.index !== ".").map(entry =>
              <li key={entry.path} className="break-all">{entry.index} · {entry.path}</li>)}
          </ul>
        </details> : null}
      </form>
      {showBranches ? (
        <section id="git-branches" aria-label="Branch-Verwaltung" className="mt-3 border-t border-slate-200 pt-3">
          <div className="flex gap-2">
            <input aria-label="Branches suchen" value={query} onChange={event => setQuery(event.target.value)}
              placeholder="Lokale und Remote-Branches suchen…" className={field} />
            <button className={`${button} shrink-0`} disabled={busy} onClick={() => choose("create")}>Neuer Branch</button>
          </div>
          <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto">
            {branches.filter(branch => branch.name.toLowerCase().includes(query.toLowerCase())).map(branch => (
              <li key={`${branch.remote ? "remote" : "local"}:${branch.name}`} data-branch={branch.name}
                className="flex flex-wrap items-center gap-2 rounded border border-slate-200 px-2 py-1.5">
                <div className="min-w-0 flex-1">
                  <p className="break-all font-mono text-xs">{branch.current ? "● " : "⎇ "}{branch.name}</p>
                  <p className="break-all text-[10px] text-slate-500">
                    {branch.remote ? "Remote · nur Anzeige" : branch.current ? "Lokal · aktuell" : "Lokal"}
                    {branch.upstream ? ` · verfolgt ${branch.upstream}` : ""}
                    {branch.worktree && !branch.current ? ` · Worktree: ${branch.worktree}` : ""}
                  </p>
                </div>
                {!branch.remote ? <div className="flex gap-1">
                  <button className={button} disabled={busy || branch.current || !!branch.worktree}
                    onClick={() => choose("switch", branch.name)}>Wechseln</button>
                  <button className={button} disabled={busy || (!!branch.worktree && !branch.current)}
                    onClick={() => choose("rename", branch.name)}>Umbenennen</button>
                  <button className={button} disabled={busy || branch.current || !!branch.worktree}
                    onClick={() => choose("delete", branch.name)}>Löschen…</button>
                </div> : null}
              </li>
            ))}
          </ul>
          {!branches.some(branch => branch.name.toLowerCase().includes(query.toLowerCase())) ?
            <p className="mt-2 text-xs text-slate-500">Keine passenden Branches.</p> : null}
          {pending ? <form aria-label="Branch-Aktion bestätigen" data-tone={pending.action === "delete" ? "rose" : "blue"}
            className="tone-surface mt-3 rounded border p-3" onSubmit={event => { event.preventDefault(); void perform(); }}>
            <p className="break-all text-xs">{project} · aktuell: {pending.from ?? "Detached HEAD"}</p>
            <p className="my-2 break-all text-xs font-semibold">
              {pending.action === "create" ? "Neuen Branch anlegen und wechseln" : `${pending.branch} — ${pending.action === "switch" ? "dorthin wechseln?" : pending.action === "rename" ? "umbenennen" : "lokal löschen?"}`}
            </p>
            {needsName ? <input autoFocus aria-label="Branch-Name" value={name} disabled={busy}
              onChange={event => setName(event.target.value)} className={field} /> : null}
            <p className="my-2 text-[11px]">
              {pending.action === "delete" ? "Nur wenn vollständig in HEAD integriert. Kein Force-Delete; Remote bleibt unverändert."
                : "Lokale Änderungen werden nicht verworfen oder gestasht. Git bricht bei gefährdeten Änderungen ab."}
            </p>
            {branchChanged ? <p className="mb-2 text-xs">Branch hat sich inzwischen geändert. Bitte Aktion neu auswählen.</p> : null}
            <div className="flex gap-2">
              <button className={button} type="submit" disabled={busy || branchChanged || (needsName && !name.trim())}>
                {busy ? "Läuft…" : "Bestätigen"}
              </button>
              <button className={button} type="button" disabled={busy} onClick={() => setPending(null)}>Abbrechen</button>
            </div>
          </form> : null}
        </section>
      ) : null}
    </section>
  );
}
