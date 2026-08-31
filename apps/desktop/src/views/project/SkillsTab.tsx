// Skills-Tab (Plan projektfenster.md, P1): normale, expandierte Skills aus
// .agent/skills/ (D8) mit Herkunft aus expansions.yaml. Lesend.

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import Markdown, { stripFrontmatter } from "../../components/Markdown";
import { LoadingBoundary, useAsync } from "../../components/ui";

export interface SkillEntry {
  name: string;
  file: string;
  description: string | null;
  origin: {
    source: string;
    version: string | null;
    expanded: string | null;
    tools: string[];
  } | null;
}

export default function SkillsTab({ project, refresh }: { project: string; refresh?: number }) {
  const { data, loading, error, reload } = useAsync(
    () => invoke<SkillEntry[]>("project_skills", { project }),
    `skills:${project}`,
  );
  const [selected, setSelected] = useState<string | null>(null);
  const skills = data ?? [];
  const skill = skills.find((entry) => entry.name === selected) ?? null;
  const body = useAsync(
    () =>
      skill
        ? invoke<string>("project_read_file", { project, file: skill.file })
        : Promise.resolve(""),
    `skill-body:${project}:${skill?.file ?? ""}`,
  );

  useEffect(() => {
    if (refresh) {
      void reload();
      void body.reload();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh]);

  return (
    <LoadingBoundary loading={loading} error={error} label="Skills lesen…">
      {skills.length === 0 ? (
        <p className="text-sm text-slate-500">
          Keine Skills unter <code>.agent/skills/</code> — im Terminal rechts kann
          der Agent welche expandieren (<code>speccify expand</code>).
        </p>
      ) : (
        <div className="flex h-full min-h-0 gap-4">
          <ul className="w-72 shrink-0 space-y-1 overflow-y-auto pr-1">
            {skills.map((entry) => (
              <li key={entry.name}>
                <button
                  onClick={() => setSelected(entry.name)}
                  className={`w-full rounded px-2 py-1.5 text-left ${
                    selected === entry.name
                      ? "bg-slate-800 text-white"
                      : "text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  <span className="block text-sm font-medium">{entry.name}</span>
                  {entry.description ? (
                    <span
                      className={`block truncate text-xs ${
                        selected === entry.name ? "text-slate-300" : "text-slate-500"
                      }`}
                    >
                      {entry.description}
                    </span>
                  ) : null}
                </button>
              </li>
            ))}
          </ul>
          <div className="min-w-0 flex-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-5">
            {skill ? (
              <>
                {skill.origin ? (
                  <p className="mb-3 rounded bg-slate-100 px-3 py-2 text-xs text-slate-600">
                    Expandiert aus <code>{skill.origin.source}</code>
                    {skill.origin.version ? ` ${skill.origin.version}` : ""}
                    {skill.origin.expanded ? ` am ${skill.origin.expanded}` : ""}
                    {skill.origin.tools.length > 0
                      ? ` · Tools: ${skill.origin.tools.join(", ")}`
                      : ""}
                  </p>
                ) : (
                  <p className="mb-3 rounded bg-slate-100 px-3 py-2 text-xs text-slate-600">
                    Projekteigener Skill (keine Herkunft in{" "}
                    <code>expansions.yaml</code>).
                  </p>
                )}
                <LoadingBoundary
                  loading={body.loading}
                  error={body.error}
                  label="SKILL.md lesen…"
                >
                  <Markdown text={stripFrontmatter(body.data ?? "")} />
                </LoadingBoundary>
              </>
            ) : (
              <p className="text-sm text-slate-400">Skill links auswählen.</p>
            )}
          </div>
        </div>
      )}
    </LoadingBoundary>
  );
}
