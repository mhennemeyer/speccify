// Liste der Skill-Quellen mit Hinzufügen (Git-URL oder Ordner), Aktualisieren
// und Entfernen — im Dashboard (Bibliothek, global) und im Skills-Tab
// (Projekt). Plan skill-quellen-und-export.md, Q2.

import { useState } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import {
  SOURCE_KIND_LABEL,
  SOURCE_SCOPE_LABEL,
  addSource,
  looksLikeGit,
  refreshSource,
  removeSource,
  type SourceInfo,
} from "../lib/sources";

export function SourceAddForm({
  project,
  onAdded,
  compact = false,
}: {
  project?: string | null;
  onAdded: (source: SourceInfo) => void | Promise<void>;
  compact?: boolean;
}) {
  const [location, setLocation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) return;
    setBusy(true);
    setError(null);
    try {
      const added = await addSource(trimmed, project);
      setLocation("");
      await onAdded(added);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const pickFolder = async () => {
    const picked = await openDialog({ directory: true, title: "Skill-Ordner wählen" });
    if (typeof picked === "string") await submit(picked);
  };

  const size = compact ? "px-2 py-1.5 text-xs" : "px-3 py-2 text-sm";
  return (
    <div>
      <div className="flex flex-wrap gap-2">
        <input
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void submit(location);
          }}
          placeholder="https://github.com/…/skills.git · git@gitlab…:team/skills.git · ~/Ordner"
          className={`min-w-0 flex-1 rounded border border-slate-300 bg-white font-mono ${size}`}
          spellCheck={false}
          disabled={busy}
        />
        <button
          onClick={() => void submit(location)}
          disabled={busy || !location.trim()}
          className={`shrink-0 rounded bg-slate-800 text-white hover:bg-slate-700 disabled:opacity-40 ${size}`}
        >
          {busy ? (looksLikeGit(location) ? "Klont…" : "Prüft…") : "Hinzufügen"}
        </button>
        <button
          onClick={() => void pickFolder()}
          disabled={busy}
          className={`shrink-0 rounded border border-slate-300 bg-white text-slate-700 hover:bg-slate-100 ${size}`}
        >
          Ordner…
        </button>
      </div>
      {error ? (
        <pre className="mt-2 whitespace-pre-wrap rounded bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </pre>
      ) : null}
    </div>
  );
}

export function SourceRow({
  source,
  project,
  removable,
  onChanged,
}: {
  source: SourceInfo;
  /** Projektpfad — nötig, um eine Projekt-Quelle zu entfernen. */
  project?: string | null;
  removable: boolean;
  onChanged: () => void | Promise<void>;
}) {
  const [busy, setBusy] = useState<"refresh" | "remove" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (kind: "refresh" | "remove") => {
    setBusy(kind);
    setError(null);
    try {
      if (kind === "refresh") await refreshSource(source);
      else await removeSource(source.location, source.scope === "project" ? project : null);
      await onChanged();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const stateBadge =
    source.state === "ready"
      ? "bg-emerald-100 text-emerald-800"
      : "bg-amber-100 text-amber-800";
  return (
    <li className="rounded border border-slate-200 bg-white px-3 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-slate-800">{source.name}</span>
        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600">
          {SOURCE_KIND_LABEL[source.kind]}
        </span>
        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600">
          {SOURCE_SCOPE_LABEL[source.scope]}
        </span>
        <span className={`rounded px-1.5 py-0.5 text-[11px] ${stateBadge}`}>
          {source.state === "ready" ? "bereit" : "nicht geklont"}
        </span>
      </div>
      <p className="mt-0.5 truncate font-mono text-xs text-slate-500" title={source.location}>
        {source.location}
      </p>
      {source.path && source.path !== source.location ? (
        <p className="truncate font-mono text-[11px] text-slate-400" title={source.path}>
          → {source.path}
        </p>
      ) : null}
      {source.detail && source.state !== "ready" ? (
        <p className="mt-1 text-xs text-amber-700">{source.detail}</p>
      ) : null}
      {source.kind === "git" || removable ? (
        <div className="mt-1 flex justify-end gap-1">
          {source.kind === "git" ? (
            <button
              onClick={() => void run("refresh")}
              disabled={busy !== null}
              title="git pull --ff-only (bzw. klonen)"
              className="rounded px-2 py-1 text-xs text-slate-600 hover:bg-slate-100 disabled:opacity-40"
            >
              {busy === "refresh" ? "Zieht…" : "Aktualisieren"}
            </button>
          ) : null}
          {removable ? (
            <button
              onClick={() => void run("remove")}
              disabled={busy !== null}
              title="Aus der Liste nehmen — der Checkout bleibt als Cache"
              className="rounded px-2 py-1 text-xs text-slate-400 hover:text-red-600 disabled:opacity-40"
            >
              {busy === "remove" ? "Entfernt…" : "Entfernen"}
            </button>
          ) : null}
        </div>
      ) : null}
      {error ? (
        <pre className="mt-1 whitespace-pre-wrap rounded bg-red-50 px-2 py-1 text-xs text-red-700">
          {error}
        </pre>
      ) : null}
    </li>
  );
}
