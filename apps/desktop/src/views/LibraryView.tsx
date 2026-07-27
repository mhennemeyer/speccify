// Bibliothek: Toolbox-Manifeste (Tools / MCPs / KBs) mit Tag-Filter und
// Requirements-Badges — komplett nativ aus dem Rust-Kern (T2 + R3).

import { useMemo, useState } from "react";
import { fetchDoctor } from "../lib/system";
import {
  fetchToolbox,
  scaffoldManifest,
  type ToolboxManifest,
} from "../lib/toolbox";
import { ActionButton, ErrorBox, LoadingBoundary, Spinner, useAsync } from "../components/ui";

const KIND_LABEL: Record<ToolboxManifest["kind"], string> = {
  tool: "Tools",
  mcp: "MCP-Server",
  kb: "Knowledgebases",
};

const KIND_BADGE: Record<ToolboxManifest["kind"], string> = {
  tool: "bg-sky-100 text-sky-800",
  mcp: "bg-violet-100 text-violet-800",
  kb: "bg-emerald-100 text-emerald-800",
};

const SOURCE_LABEL: Record<ToolboxManifest["source"], string | null> = {
  builtin: null,
  global: "(global)",
  workingdir: "(working dir)",
};

interface LibraryData {
  manifests: ToolboxManifest[];
  warnings: string[];
  foundBinaries: Record<string, boolean>;
}

export default function LibraryView() {
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [scaffoldOpen, setScaffoldOpen] = useState(false);
  const [scaffoldSlug, setScaffoldSlug] = useState("");
  const [scaffoldKind, setScaffoldKind] = useState<"tool" | "mcp" | "kb">("tool");
  const [scaffoldName, setScaffoldName] = useState("");
  const [scaffoldError, setScaffoldError] = useState<string | null>(null);
  const [scaffoldStatus, setScaffoldStatus] = useState("");

  const { data, loading, refreshing, error, reload } = useAsync<LibraryData>(async () => {
    const [toolbox, doctor] = await Promise.all([
      fetchToolbox(),
      fetchDoctor().catch(() => ({ checks: [] })),
    ]);
    return {
      manifests: toolbox.manifests,
      warnings: toolbox.warnings,
      foundBinaries: Object.fromEntries(
        doctor.checks.map((c) => [c.binary, c.found]),
      ),
    };
  }, "library");

  const manifests = data?.manifests ?? [];
  const allTags = useMemo(
    () => [...new Set(manifests.flatMap((m) => m.tags))].sort(),
    [manifests],
  );
  const visible = activeTag
    ? manifests.filter((m) => m.tags.includes(activeTag))
    : manifests;
  const kinds: ToolboxManifest["kind"][] = ["tool", "mcp", "kb"];
  const missingFor = (m: ToolboxManifest) =>
    m.requires_binaries.filter((b) => data?.foundBinaries[b] === false);

  const submitScaffold = async () => {
    setScaffoldError(null);
    try {
      const created = await scaffoldManifest(scaffoldSlug, scaffoldKind, scaffoldName);
      setScaffoldStatus(`Angelegt: ${created}`);
      setScaffoldSlug("");
      setScaffoldName("");
      setScaffoldOpen(false);
      await reload();
    } catch (e) {
      setScaffoldError(String(e));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <ActionButton
          onClick={reload}
          className="bg-slate-800 text-white hover:bg-slate-700"
        >
          Aktualisieren
        </ActionButton>
        <button
          onClick={() => setScaffoldOpen((open) => !open)}
          className="rounded bg-slate-100 px-3 py-1 text-sm text-slate-700 hover:bg-slate-200"
        >
          + Neues Manifest
        </button>
        {refreshing && <Spinner />}
        {allTags.map((tag) => (
          <button
            key={tag}
            onClick={() => setActiveTag(activeTag === tag ? null : tag)}
            className={`rounded-full px-3 py-1 text-sm ${
              activeTag === tag
                ? "bg-slate-800 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            {tag}
          </button>
        ))}
      </div>

      {scaffoldOpen ? (
        <div className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-3">
          <div>
            <label className="mb-1 block text-xs text-slate-500">Slug</label>
            <input
              value={scaffoldSlug}
              onChange={(e) => setScaffoldSlug(e.target.value)}
              placeholder="mein-tool"
              className="rounded border border-slate-300 px-2 py-1 text-sm"
              spellCheck={false}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">Art</label>
            <select
              value={scaffoldKind}
              onChange={(e) => setScaffoldKind(e.target.value as "tool" | "mcp" | "kb")}
              className="rounded border border-slate-300 px-2 py-1 text-sm"
            >
              <option value="tool">tool</option>
              <option value="mcp">mcp</option>
              <option value="kb">kb</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">Name (optional)</label>
            <input
              value={scaffoldName}
              onChange={(e) => setScaffoldName(e.target.value)}
              className="rounded border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          <ActionButton
            onClick={submitScaffold}
            className="bg-slate-800 text-white hover:bg-slate-700"
          >
            ins Working Dir anlegen
          </ActionButton>
          <span className="text-xs text-slate-400">
            → &lt;Working Dir&gt;/.speccify/toolbox/&lt;slug&gt;.toml
          </span>
        </div>
      ) : null}
      {scaffoldError ? <ErrorBox message={scaffoldError} /> : null}
      {scaffoldStatus ? <p className="text-xs text-slate-500">{scaffoldStatus}</p> : null}

      <LoadingBoundary loading={loading} error={error} label="Toolbox wird geladen…">
        {(data?.warnings ?? []).map((w) => (
          <p key={w} className="text-sm text-amber-600">⚠ {w}</p>
        ))}

        {kinds.map((kind) => {
          const group = visible.filter((m) => m.kind === kind);
          if (group.length === 0) return null;
          return (
            <section key={kind} className="mb-6">
              <h2 className="mb-2 text-lg font-semibold text-slate-800">
                {KIND_LABEL[kind]}
              </h2>
              <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                {group.map((m) => (
                  <article
                    key={m.slug}
                    className="rounded-lg border border-slate-200 bg-white p-4"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded px-1.5 py-0.5 text-xs font-medium ${KIND_BADGE[m.kind]}`}
                      >
                        {m.kind}
                      </span>
                      <h3 className="font-medium text-slate-900">{m.name}</h3>
                      {SOURCE_LABEL[m.source] && (
                        <span className="text-xs text-slate-400">
                          {SOURCE_LABEL[m.source]}
                        </span>
                      )}
                      {m.requires_binaries.length > 0 &&
                        (missingFor(m).length === 0 ? (
                          <span className="ml-auto rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-800">
                            ✓ bereit
                          </span>
                        ) : (
                          <span className="ml-auto rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800">
                            ⚠ fehlt: {missingFor(m).join(", ")}
                          </span>
                        ))}
                    </div>
                    <p className="mt-1 text-sm text-slate-600">{m.description}</p>
                    {m.run ? (
                      <p className="mt-2 font-mono text-xs text-slate-400">
                        {m.run.command} {m.run.args.join(" ")} · {m.run.transport}
                      </p>
                    ) : null}
                    <p className="mt-1 text-xs text-slate-400">{m.tags.join(" · ")}</p>
                  </article>
                ))}
              </div>
            </section>
          );
        })}

        {manifests.length === 0 && (
          <p className="text-slate-500">Toolbox ist leer.</p>
        )}
      </LoadingBoundary>
    </div>
  );
}
