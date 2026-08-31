// Pläne-Tab (Plan projektfenster.md, P1 + D20): Liste aus .agent/plans/
// mit Frontmatter-Metadaten; Auswahl rendert das Markdown. Bearbeiten
// (BO-Erweiterung 2026-08-28): Frontmatter-Felder als Formular + Body als
// Editor, gespeichert über project_write_file. Unbekannte Frontmatter-
// Zeilen bleiben unangetastet.

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import Markdown, { stripFrontmatter } from "../../components/Markdown";
import { copyPrompt } from "../../lib/prompt";
import { LoadingBoundary, useAsync } from "../../components/ui";

export interface PlanEntry {
  file: string;
  title: string;
  lifecycle: string | null;
  status: string | null;
  escalation: string | null;
  archived: boolean;
}

/** Zerlegt einen Plan in Frontmatter-Zeilen und Body (flach, zeilenbasiert). */
export function splitPlan(text: string): { frontmatter: string[]; body: string } {
  if (!text.startsWith("---\n")) return { frontmatter: [], body: text };
  const end = text.indexOf("\n---", 4);
  if (end === -1) return { frontmatter: [], body: text };
  const frontmatter = text.slice(4, end).split("\n");
  let body = text.slice(end + 4);
  if (body.startsWith("\n")) body = body.slice(1);
  return { frontmatter, body };
}

/** Baut den Plan neu: bekannte Felder ersetzt (oder ergänzt), unbekannte
 *  Frontmatter-Zeilen bleiben wörtlich erhalten, der Body kommt vom Editor. */
export function assemblePlan(
  original: string,
  fields: Record<string, string>,
  body: string,
): string {
  const { frontmatter } = splitPlan(original);
  const remaining = { ...fields };
  const lines = frontmatter.map((line) => {
    const colon = line.indexOf(":");
    if (colon === -1) return line;
    const key = line.slice(0, colon).trim();
    if (key in remaining) {
      const value = remaining[key];
      delete remaining[key];
      return `${key}: ${value}`;
    }
    return line;
  });
  for (const [key, value] of Object.entries(remaining)) {
    if (value.trim() !== "") lines.push(`${key}: ${value}`);
  }
  const bodyOut = body.endsWith("\n") ? body : body + "\n";
  if (lines.length === 0) return bodyOut;
  return `---\n${lines.join("\n")}\n---\n${bodyOut}`;
}

function frontmatterValue(frontmatter: string[], key: string): string {
  for (const line of frontmatter) {
    const colon = line.indexOf(":");
    if (colon !== -1 && line.slice(0, colon).trim() === key) {
      return line.slice(colon + 1).trim();
    }
  }
  return "";
}

function LifecycleBadge({ lifecycle }: { lifecycle: string | null }) {
  if (!lifecycle) return null;
  const tone =
    lifecycle === "active"
      ? "bg-emerald-100 text-emerald-800"
      : lifecycle === "done"
        ? "bg-slate-200 text-slate-600"
        : lifecycle === "onHold"
          ? "bg-sky-100 text-sky-800"
          : lifecycle === "research"
            ? "bg-violet-100 text-violet-800"
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

function PlanEditor({
  project,
  file,
  original,
  onSaved,
  onCancel,
}: {
  project: string;
  file: string;
  original: string;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const parts = splitPlan(original);
  const [lifecycle, setLifecycle] = useState(frontmatterValue(parts.frontmatter, "lifecycle"));
  const [status, setStatus] = useState(frontmatterValue(parts.frontmatter, "status"));
  const [body, setBody] = useState(parts.body);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const content = assemblePlan(original, { lifecycle, status }, body);
      await invoke("project_write_file", { project, file, content });
      onSaved();
    } catch (e) {
      setError(String(e));
      setSaving(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2">
        <label className="text-xs font-medium text-slate-500">lifecycle</label>
        <input
          value={lifecycle}
          onChange={(event) => setLifecycle(event.target.value)}
          spellCheck={false}
          className="rounded border border-slate-300 px-2 py-1 font-mono text-sm"
        />
        <label className="text-xs font-medium text-slate-500">status</label>
        <textarea
          value={status}
          onChange={(event) => setStatus(event.target.value.replace(/\n/g, " "))}
          rows={2}
          spellCheck={false}
          className="rounded border border-slate-300 px-2 py-1 font-mono text-xs"
        />
      </div>
      <textarea
        value={body}
        onChange={(event) => setBody(event.target.value)}
        spellCheck={false}
        className="min-h-0 flex-1 resize-none rounded border border-slate-300 p-3 font-mono text-xs leading-5"
      />
      {error ? <p className="text-xs text-red-600">{error}</p> : null}
      <div className="flex justify-end gap-2">
        <button
          onClick={onCancel}
          disabled={saving}
          className="rounded px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
        >
          Abbrechen
        </button>
        <button
          onClick={() => void save()}
          disabled={saving}
          className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {saving ? "Speichert…" : "Speichern"}
        </button>
      </div>
    </div>
  );
}

export default function PlansTab({ project, refresh }: { project: string; refresh?: number }) {
  const list = useAsync(
    () => invoke<PlanEntry[]>("project_plans", { project }),
    `plans:${project}`,
  );
  const [selected, setSelected] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const body = useAsync(
    () =>
      selected
        ? invoke<string>("project_read_file", { project, file: selected })
        : Promise.resolve(""),
    `plan-body:${project}:${selected ?? ""}`,
  );

  useEffect(() => {
    // Live-Reload — aber nie mitten ins Editieren hinein.
    if (refresh && !editing) {
      void list.reload();
      void body.reload();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh]);

  const plans = list.data ?? [];
  const active = plans.filter((plan) => !plan.archived);
  const archived = plans.filter((plan) => plan.archived);
  const selectedPlan = plans.find((plan) => plan.file === selected) ?? null;

  const select = (file: string) => {
    setSelected(file);
    setEditing(false);
  };

  return (
    <LoadingBoundary loading={list.loading} error={list.error} label="Pläne lesen…">
      {plans.length === 0 ? (
        <p className="text-sm text-slate-500">
          Keine Pläne unter <code>.agent/plans/</code>.
        </p>
      ) : (
        <div className="flex h-full min-h-0 gap-4">
          <div className="w-72 shrink-0 overflow-y-auto pr-1">
            <PlanList plans={active} selected={selected} onSelect={select} />
            {archived.length > 0 ? (
              <details className="mt-3">
                <summary className="cursor-pointer px-2 text-xs font-semibold text-slate-500">
                  Archiv ({archived.length})
                </summary>
                <div className="mt-1">
                  <PlanList plans={archived} selected={selected} onSelect={select} />
                </div>
              </details>
            ) : null}
          </div>
          <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white p-5">
            {selectedPlan ? (
              editing ? (
                <PlanEditor
                  project={project}
                  file={selectedPlan.file}
                  original={body.data ?? ""}
                  onSaved={() => {
                    setEditing(false);
                    void body.reload();
                    void list.reload();
                  }}
                  onCancel={() => setEditing(false)}
                />
              ) : (
                <div className="min-h-0 flex-1 overflow-y-auto">
                  {selectedPlan.escalation ? (
                    <div className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2">
                      <p className="text-xs text-red-800">
                        <span className="font-semibold">Eskalation:</span>{" "}
                        {selectedPlan.escalation}
                      </p>
                      <button
                        onClick={() =>
                          void invoke("project_plan_resolve_escalation", {
                            project,
                            file: selectedPlan.file,
                          }).then(() => {
                            void list.reload();
                            void body.reload();
                          })
                        }
                        className="shrink-0 rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700"
                      >
                        Auflösen
                      </button>
                    </div>
                  ) : null}
                  <div className="mb-3 flex items-start justify-between gap-3">
                    {selectedPlan.status ? (
                      <p className="rounded bg-slate-100 px-3 py-2 text-xs text-slate-600">
                        <span className="font-semibold">Status:</span> {selectedPlan.status}
                      </p>
                    ) : (
                      <span />
                    )}
                    <div className="flex shrink-0 gap-2">
                      {!selectedPlan.archived && selectedPlan.lifecycle !== "active" ? (
                        <button
                          onClick={() =>
                            void invoke("project_plan_activate", {
                              project,
                              file: selectedPlan.file,
                            }).then(() => void list.reload())
                          }
                          className="rounded bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700"
                        >
                          Aktivieren
                        </button>
                      ) : null}
                      <button
                        onClick={() =>
                          void copyPrompt(selectedPlan.file, body.data ?? "")
                        }
                        disabled={body.data === null}
                        className="rounded border border-slate-300 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 disabled:opacity-40"
                        title="Pfad + Inhalt als Markdown-Prompt in die Zwischenablage"
                      >
                        Als Prompt kopieren
                      </button>
                      <button
                        onClick={() => setEditing(true)}
                        disabled={body.loading || body.data === null}
                        className="rounded border border-slate-300 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 disabled:opacity-40"
                      >
                        Bearbeiten
                      </button>
                    </div>
                  </div>
                  <LoadingBoundary loading={body.loading} error={body.error} label="Plan lesen…">
                    <Markdown text={stripFrontmatter(body.data ?? "")} />
                  </LoadingBoundary>
                </div>
              )
            ) : (
              <p className="text-sm text-slate-400">Plan links auswählen.</p>
            )}
          </div>
        </div>
      )}
    </LoadingBoundary>
  );
}
