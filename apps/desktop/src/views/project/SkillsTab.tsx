// Skills-Tab (Plan projektfenster.md, P1 + P4/D21/D24): links die
// expandierten Projekt-Skills, dazu der Modus „Quellen durchsuchen" —
// eine oder mehrere Skill-Quellen pro Projekt (Default aus den
// Dashboard-Settings), Ordnerstruktur als Organisation, Import = das
// `speccify add/expand`-Kommando wird ins Agent-Terminal getippt
// (D14-Haltung: Aktionen laufen über den Agenten, die App liest nur).

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
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

interface SkillSources {
  default: string | null;
  sources: string[];
}

interface BrowseSkill {
  name: string;
  category: string;
  file: string;
  description: string | null;
  id: string | null;
}

function importCommand(skill: BrowseSkill, source: string): string | null {
  if (!skill.id) return null;
  return `speccify add ${skill.id} --library "${source}" && speccify expand ${skill.name} --library "${source}"`;
}

function SourceBrowser({ project }: { project: string }) {
  const config = useAsync(
    () => invoke<SkillSources>("project_skill_sources", { project }),
    `skill-sources:${project}`,
  );
  const [source, setSource] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const all = [
    ...(config.data?.default ? [config.data.default] : []),
    ...(config.data?.sources ?? []),
  ];
  const activeSource = source ?? all[0] ?? null;

  const skills = useAsync(
    () =>
      activeSource
        ? invoke<BrowseSkill[]>("source_browse", { source: activeSource })
        : Promise.resolve([] as BrowseSkill[]),
    `source-browse:${activeSource ?? ""}`,
  );
  const preview = useAsync(
    () =>
      activeSource && selected
        ? invoke<string>("source_skill_read", { source: activeSource, file: selected })
        : Promise.resolve(""),
    `source-skill:${activeSource ?? ""}:${selected ?? ""}`,
  );

  const addSource = async () => {
    setError(null);
    const picked = await openDialog({ directory: true, title: "Skill-Quelle wählen" });
    if (typeof picked !== "string") return;
    try {
      const normalized = await invoke<string>("source_validate", { source: picked });
      const next = [...(config.data?.sources ?? [])];
      if (!next.includes(normalized)) next.push(normalized);
      await invoke("project_settings_set", {
        project,
        key: "speccify.sources",
        value: next,
      });
      await config.reload();
      setSource(normalized);
    } catch (e) {
      setError(String(e));
    }
  };

  const removeSource = async (entry: string) => {
    const next = (config.data?.sources ?? []).filter((known) => known !== entry);
    await invoke("project_settings_set", {
      project,
      key: "speccify.sources",
      value: next.length > 0 ? next : null,
    });
    await config.reload();
    if (source === entry) setSource(null);
  };

  const importSkill = (skill: BrowseSkill) => {
    if (!activeSource) return;
    const command = importCommand(skill, activeSource);
    if (!command) {
      setNotice(
        `${skill.name} hat kein metadata.speccify.scope — ohne Id kann speccify add nicht adressieren. Skill von Hand übernehmen oder scope ergänzen.`,
      );
      return;
    }
    window.dispatchEvent(new CustomEvent("speccify:type-command", { detail: command }));
    setNotice(
      `Kommando ins Agent-Terminal getippt (Enter dort bestätigt): ${skill.name} importieren.`,
    );
  };

  const grouped = new Map<string, BrowseSkill[]>();
  for (const skill of skills.data ?? []) {
    const group = grouped.get(skill.category) ?? [];
    group.push(skill);
    grouped.set(skill.category, group);
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <select
          value={activeSource ?? ""}
          onChange={(event) => {
            setSource(event.target.value || null);
            setSelected(null);
          }}
          className="max-w-md rounded border border-slate-300 px-2 py-1.5 font-mono text-xs"
        >
          {all.length === 0 ? <option value="">— keine Quelle —</option> : null}
          {all.map((entry) => (
            <option key={entry} value={entry}>
              {entry}
              {entry === config.data?.default ? "  (Default)" : ""}
            </option>
          ))}
        </select>
        <button
          onClick={() => void addSource()}
          className="rounded border border-slate-300 px-2.5 py-1.5 text-xs text-slate-600 hover:bg-slate-100"
        >
          + Quelle
        </button>
        {activeSource && activeSource !== config.data?.default ? (
          <button
            onClick={() => void removeSource(activeSource)}
            className="rounded px-2 py-1.5 text-xs text-slate-400 hover:text-red-600"
          >
            Quelle entfernen
          </button>
        ) : null}
      </div>
      {notice ? (
        <p className="mb-2 rounded bg-sky-50 px-3 py-2 text-xs text-sky-800">{notice}</p>
      ) : null}
      {error ? <p className="mb-2 text-xs text-red-600">{error}</p> : null}
      {all.length === 0 ? (
        <p className="text-sm text-slate-500">
          Keine Skill-Quelle — Default in den Dashboard-Settings setzen oder hier
          mit „+ Quelle" ein Repo wählen (Projekt-Einstellung, D21).
        </p>
      ) : (
        <div className="flex min-h-0 flex-1 gap-4">
          <div className="w-80 shrink-0 overflow-y-auto pr-1">
            <LoadingBoundary loading={skills.loading} error={skills.error} label="Quelle lesen…">
              {(skills.data ?? []).length === 0 ? (
                <p className="text-sm text-slate-500">Keine Skills in dieser Quelle.</p>
              ) : (
                [...grouped.entries()].map(([category, entries]) => (
                  <details key={category || "(wurzel)"} open className="mb-2">
                    <summary className="cursor-pointer px-1 text-xs font-semibold text-slate-500">
                      {category === "" ? "•" : category} ({entries.length})
                    </summary>
                    <ul className="mt-1 space-y-1">
                      {entries.map((entry) => (
                        <li key={entry.file}>
                          <button
                            onClick={() => setSelected(entry.file)}
                            className={`w-full rounded px-2 py-1.5 text-left ${
                              selected === entry.file
                                ? "bg-slate-800 text-white"
                                : "text-slate-700 hover:bg-slate-100"
                            }`}
                          >
                            <span className="block text-sm font-medium">{entry.name}</span>
                            {entry.description ? (
                              <span
                                className={`block truncate text-xs ${
                                  selected === entry.file ? "text-slate-300" : "text-slate-500"
                                }`}
                              >
                                {entry.description}
                              </span>
                            ) : null}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </details>
                ))
              )}
            </LoadingBoundary>
          </div>
          <div className="min-w-0 flex-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-5">
            {selected ? (
              <>
                <div className="mb-3 flex items-center justify-between gap-3">
                  <p className="truncate font-mono text-xs text-slate-400">{selected}</p>
                  {(() => {
                    const skill = (skills.data ?? []).find((entry) => entry.file === selected);
                    return skill ? (
                      <button
                        onClick={() => importSkill(skill)}
                        className="shrink-0 rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
                        title="Tippt speccify add + expand ins Agent-Terminal"
                      >
                        Importieren (expand)
                      </button>
                    ) : null;
                  })()}
                </div>
                <LoadingBoundary
                  loading={preview.loading}
                  error={preview.error}
                  label="SKILL.md lesen…"
                >
                  <Markdown text={stripFrontmatter(preview.data ?? "")} />
                </LoadingBoundary>
              </>
            ) : (
              <p className="text-sm text-slate-400">Skill links auswählen.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function SkillsTab({ project, refresh }: { project: string; refresh?: number }) {
  const { data, loading, error, reload } = useAsync(
    () => invoke<SkillEntry[]>("project_skills", { project }),
    `skills:${project}`,
  );
  const [mode, setMode] = useState<"project" | "browse">("project");
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
    <div className="flex h-full min-h-0 flex-col">
      <div className="mb-3 flex gap-1">
        {(
          [
            ["project", "Im Projekt"],
            ["browse", "Quellen durchsuchen"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            onClick={() => setMode(id)}
            className={`rounded px-3 py-1.5 text-xs font-medium ${
              mode === id
                ? "bg-slate-800 text-white"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {mode === "browse" ? (
        <SourceBrowser project={project} />
      ) : (
        <LoadingBoundary loading={loading} error={error} label="Skills lesen…">
          {skills.length === 0 ? (
            <p className="text-sm text-slate-500">
              Keine Skills unter <code>.agent/skills/</code> — über „Quellen
              durchsuchen" importieren oder den Agenten im Terminal bitten
              (<code>speccify expand</code>).
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
      )}
    </div>
  );
}
