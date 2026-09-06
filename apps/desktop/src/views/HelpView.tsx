// Integrierte Hilfe (Plan projektfenster.md, P6b, Vorbild tec-e2e):
// Master-Detail über die einkompilierte Doku-Registry. Das erste Dokument
// ist ohne Klick offen; über dem Text steht der Repo-Quellpfad — wer etwas
// ändern will, weiß welche Datei.

import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import Markdown from "../components/Markdown";
import { LoadingBoundary, useAsync } from "../components/ui";
import { InspectorPanel, InspectorPortal, NavigatorPortal, inlineInspector } from "../lib/panels";

interface HelpDocMeta {
  slug: string;
  title: string;
  description: string;
  source_path: string;
}

export default function HelpView() {
  const list = useAsync(() => invoke<HelpDocMeta[]>("help_docs"), "help-docs");
  const [selected, setSelected] = useState<string | null>(null);
  const docs = list.data ?? [];
  const current = docs.find((doc) => doc.slug === selected) ?? docs[0] ?? null;
  const body = useAsync(
    () =>
      current
        ? invoke<string>("help_doc", { slug: current.slug })
        : Promise.resolve(""),
    `help-doc:${current?.slug ?? ""}`,
  );

  return (
    <LoadingBoundary loading={list.loading} error={list.error} label="Hilfe laden…">
      <div className="flex h-full min-h-0 gap-4">
        <NavigatorPortal tab="help">
        <nav className="space-y-1">
          {docs.map((doc) => (
            <button
              key={doc.slug}
              onClick={() => setSelected(doc.slug)}
              className={`w-full rounded px-2 py-2 text-left ${
                current?.slug === doc.slug
                  ? "bg-slate-800 text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              <span className="block text-sm font-medium">{doc.title}</span>
              <span
                className={`block text-xs ${
                  current?.slug === doc.slug ? "text-slate-300" : "text-slate-500"
                }`}
              >
                {doc.description}
              </span>
            </button>
          ))}
        </nav>
        </NavigatorPortal>
        <article className="min-w-0 flex-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-6">
          {current ? (
            <>
              <InspectorPortal tab="help" fallback={inlineInspector}>
                <InspectorPanel
                  title={current.title}
                  subtitle={current.source_path}
                  meta={[
                    { label: "Inhalt", value: current.description },
                    {
                      label: "Quelle",
                      value: (
                        <span>
                          <span className="font-mono">{current.source_path}</span> im Repository —
                          wer etwas ändern will, ändert diese Datei.
                        </span>
                      ),
                    },
                  ]}
                />
              </InspectorPortal>
              <LoadingBoundary loading={body.loading} error={body.error} label="Dokument laden…">
                <Markdown text={body.data ?? ""} />
              </LoadingBoundary>
            </>
          ) : null}
        </article>
      </div>
    </LoadingBoundary>
  );
}
