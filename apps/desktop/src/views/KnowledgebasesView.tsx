// Knowledgebases: lokale KBs (~/Knowledgebase) als Master-Detail —
// Layout-Vorlage: KnowledgebaseView der alten Mac-App.

import { useState } from "react";
import { openPath } from "@tauri-apps/plugin-opener";
import { fetchKnowledgebases, type Knowledgebase } from "../lib/system";
import { ActionButton, LoadingBoundary, Spinner, useAsync } from "../components/ui";

export default function KnowledgebasesView() {
  const { data, loading, refreshing, error, reload } = useAsync(
    fetchKnowledgebases,
    "knowledgebases",
  );
  const [selectedName, setSelectedName] = useState<string | null>(null);

  const kbs = data?.knowledgebases ?? [];
  const selected =
    kbs.find((kb) => kb.name === selectedName) ?? kbs[0] ?? null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <ActionButton
          onClick={reload}
          className="bg-slate-800 text-white hover:bg-slate-700"
        >
          Aktualisieren
        </ActionButton>
        {refreshing && <Spinner />}
        {data && (
          <span className="text-xs text-slate-400">
            Basis: {data.base_dir}
          </span>
        )}
      </div>

      <LoadingBoundary
        loading={loading}
        error={error}
        label="Knowledgebases werden geladen…"
      >
        {kbs.length === 0 ? (
          <div className="rounded-lg border border-slate-200 bg-white p-6 text-slate-500">
            <p className="font-medium text-slate-700">Keine Knowledgebases</p>
            <p className="mt-1 text-sm">
              Erstelle eine mit:{" "}
              <code className="rounded bg-slate-100 px-1">
                dotagent kb init &lt;books-dir&gt; --name &lt;name&gt;
              </code>
            </p>
          </div>
        ) : (
          <div className="flex gap-4">
            <div className="w-72 shrink-0 space-y-2">
              {kbs.map((kb) => (
                <button
                  key={kb.name}
                  onClick={() => setSelectedName(kb.name)}
                  className={`w-full rounded-lg border p-3 text-left ${
                    selected?.name === kb.name
                      ? "border-slate-800 bg-white ring-1 ring-slate-800"
                      : "border-slate-200 bg-white hover:border-slate-400"
                  }`}
                >
                  <p className="font-medium text-slate-900">📚 {kb.name}</p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {kb.books} Bücher · {kb.chunks.toLocaleString("de-DE")} Chunks ·{" "}
                    {kb.index_size_mb.toLocaleString("de-DE")} MB
                  </p>
                </button>
              ))}
            </div>

            {selected && <KnowledgebaseDetail kb={selected} />}
          </div>
        )}
      </LoadingBoundary>
    </div>
  );
}

function KnowledgebaseDetail({ kb }: { kb: Knowledgebase }) {
  const [copied, setCopied] = useState<string | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);

  const copy = async (command: string) => {
    await navigator.clipboard.writeText(command);
    setCopied(command);
    setTimeout(() => setCopied(null), 1500);
  };

  const openBook = async (path: string) => {
    setOpenError(null);
    try {
      await openPath(path);
    } catch (e) {
      setOpenError(`Öffnen fehlgeschlagen: ${e}`);
    }
  };

  const commands = [
    `dotagent kb search "…" --name ${kb.name}`,
    `dotagent kb ask "…" --name ${kb.name}`,
  ];

  return (
    <article className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white p-5">
      <h3 className="text-lg font-semibold text-slate-900">{kb.name}</h3>
      <p className="truncate text-xs text-slate-400">{kb.path}</p>

      <dl className="mt-4 grid grid-cols-3 gap-3">
        {(
          [
            ["Bücher", String(kb.books)],
            ["Chunks", kb.chunks.toLocaleString("de-DE")],
            ["Index", `${kb.index_size_mb.toLocaleString("de-DE")} MB`],
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="rounded bg-slate-50 p-3 text-center">
            <dt className="text-xs text-slate-500">{label}</dt>
            <dd className="text-lg font-semibold text-slate-900">{value}</dd>
          </div>
        ))}
      </dl>

      <h4 className="mt-5 mb-2 text-sm font-medium text-slate-700">Abfragen</h4>
      <div className="space-y-1.5">
        {commands.map((command) => (
          <div
            key={command}
            className="flex items-center justify-between gap-2 rounded bg-slate-50 px-3 py-1.5"
          >
            <code className="truncate text-xs text-slate-700">{command}</code>
            <button
              onClick={() => copy(command)}
              className="shrink-0 rounded bg-slate-800 px-2 py-0.5 text-xs text-white hover:bg-slate-700"
            >
              {copied === command ? "✓" : "Kopieren"}
            </button>
          </div>
        ))}
      </div>

      <h4 className="mt-5 mb-2 text-sm font-medium text-slate-700">
        Bücher ({kb.book_entries.length})
      </h4>
      {openError && (
        <p className="mb-2 rounded bg-red-50 px-3 py-1.5 text-xs text-red-700">
          {openError}
        </p>
      )}
      <ul className="max-h-64 space-y-1 overflow-auto">
        {kb.book_entries.map((book) => (
          <li
            key={book.file}
            className="flex items-center justify-between gap-2 rounded px-1 py-0.5 hover:bg-slate-50"
          >
            <span className="truncate text-sm text-slate-600">
              • {book.title}
            </span>
            {book.path && (
              <button
                onClick={() => openBook(book.path!)}
                title={book.path}
                className="shrink-0 rounded bg-slate-800 px-2 py-0.5 text-xs text-white hover:bg-slate-700"
              >
                Öffnen
              </button>
            )}
          </li>
        ))}
      </ul>
    </article>
  );
}
