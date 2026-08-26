// Pläne-Tab (Plan projektfenster.md, P1): Liste aus .agent/plans/ mit
// Frontmatter-Metadaten, Auswahl rendert das Markdown. Lesend — Pläne
// fortschreiben ist Sache des Agenten im Terminal rechts.

import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import Markdown, { stripFrontmatter } from "../../components/Markdown";
import { LoadingBoundary, useAsync } from "../../components/ui";

export interface PlanEntry {
  file: string;
  title: string;
  lifecycle: string | null;
  status: string | null;
  archived: boolean;
}

function LifecycleBadge({ lifecycle }: { lifecycle: string | null }) {
  if (!lifecycle) return null;
  const tone =
    lifecycle === "active"
      ? "bg-emerald-100 text-emerald-800"
      : lifecycle === "done"
        ? "bg-slate-200 text-slate-600"
        : "bg-amber-100 text-amber-800";
  return (
    <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${tone}`}>
      {lifecycle}
    </span>
  );
}

function PlanList({
  plans,
  selected,
  onSelect,
}: {
  plans: PlanEntry[];
  selected: string | null;
  onSelect: (file: string) => void;
}) {
  return (
    <ul className="space-y-1">
      {plans.map((plan) => (
        <li key={plan.file}>
          <button
            onClick={() => onSelect(plan.file)}
            className={`w-full rounded px-2 py-1.5 text-left text-sm ${
              selected === plan.file
                ? "bg-slate-800 text-white"
                : "text-slate-700 hover:bg-slate-100"
            }`}
            title={plan.status ?? undefined}
          >
            <span className="mr-2">{plan.title}</span>
            <LifecycleBadge lifecycle={plan.lifecycle} />
          </button>
        </li>
      ))}
    </ul>
  );
}

export default function PlansTab({ project }: { project: string }) {
  const { data, loading, error } = useAsync(
    () => invoke<PlanEntry[]>("project_plans", { project }),
    `plans:${project}`,
  );
  const [selected, setSelected] = useState<string | null>(null);
  const body = useAsync(
    () =>
      selected
        ? invoke<string>("project_read_file", { project, file: selected })
        : Promise.resolve(""),
    `plan-body:${project}:${selected ?? ""}`,
  );

  const plans = data ?? [];
  const active = plans.filter((plan) => !plan.archived);
  const archived = plans.filter((plan) => plan.archived);
  const selectedPlan = plans.find((plan) => plan.file === selected) ?? null;

  return (
    <LoadingBoundary loading={loading} error={error} label="Pläne lesen…">
      {plans.length === 0 ? (
        <p className="text-sm text-slate-500">
          Keine Pläne unter <code>.agent/plans/</code>.
        </p>
      ) : (
        <div className="flex h-full min-h-0 gap-4">
          <div className="w-72 shrink-0 overflow-y-auto pr-1">
            <PlanList plans={active} selected={selected} onSelect={setSelected} />
            {archived.length > 0 ? (
              <details className="mt-3">
                <summary className="cursor-pointer px-2 text-xs font-semibold text-slate-500">
                  Archiv ({archived.length})
                </summary>
                <div className="mt-1">
                  <PlanList plans={archived} selected={selected} onSelect={setSelected} />
                </div>
              </details>
            ) : null}
          </div>
          <div className="min-w-0 flex-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-5">
            {selectedPlan ? (
              <>
                {selectedPlan.status ? (
                  <p className="mb-3 rounded bg-slate-100 px-3 py-2 text-xs text-slate-600">
                    <span className="font-semibold">Status:</span> {selectedPlan.status}
                  </p>
                ) : null}
                <LoadingBoundary
                  loading={body.loading}
                  error={body.error}
                  label="Plan lesen…"
                >
                  <Markdown text={stripFrontmatter(body.data ?? "")} />
                </LoadingBoundary>
              </>
            ) : (
              <p className="text-sm text-slate-400">Plan links auswählen.</p>
            )}
          </div>
        </div>
      )}
    </LoadingBoundary>
  );
}
