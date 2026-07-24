// Bibliothek: Registry-Manifeste (Tools / KBs / MCPs) mit Tag-Filter
// und Requirements-Badges (Manifest-[requires] × Doctor-Befund).

import { useMemo, useState } from "react";
import { fetchDoctor, fetchRegistry, type Manifest } from "../lib/dotagent";
import { ActionButton, LoadingBoundary, Spinner, useAsync } from "../components/ui";

const KIND_LABEL: Record<Manifest["kind"], string> = {
  tool: "Tools",
  mcp: "MCP-Server",
  kb: "Knowledgebases",
};

const KIND_BADGE: Record<Manifest["kind"], string> = {
  tool: "bg-sky-100 text-sky-800",
  mcp: "bg-violet-100 text-violet-800",
  kb: "bg-emerald-100 text-emerald-800",
};

interface LibraryData {
  manifests: Manifest[];
  warnings: string[];
  foundBinaries: Record<string, boolean>;
}

export default function LibraryView() {
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const { data, loading, refreshing, error, reload } = useAsync<LibraryData>(async () => {
    const [registry, doctor] = await Promise.all([
      fetchRegistry(),
      fetchDoctor().catch(() => ({ checks: [] })),
    ]);
    return {
      manifests: registry.manifests,
      warnings: registry.warnings,
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
  const kinds: Manifest["kind"][] = ["tool", "mcp", "kb"];
  const missingFor = (m: Manifest) =>
    m.requires_binaries.filter((b) => data?.foundBinaries[b] === false);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <ActionButton
          onClick={reload}
          className="bg-slate-800 text-white hover:bg-slate-700"
        >
          Aktualisieren
        </ActionButton>
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

      <LoadingBoundary loading={loading} error={error} label="Registry wird geladen…">
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
                      {m.source === "project" && (
                        <span className="text-xs text-slate-400">(projektlokal)</span>
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
                    <p className="mt-2 text-xs text-slate-400">{m.tags.join(" · ")}</p>
                  </article>
                ))}
              </div>
            </section>
          );
        })}

        {manifests.length === 0 && (
          <p className="text-slate-500">
            Registry ist leer — <code>dotagent registry sync</code> holt die
            Built-in-Manifeste.
          </p>
        )}
      </LoadingBoundary>
    </div>
  );
}
