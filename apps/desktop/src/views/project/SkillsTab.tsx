// Skills-Tab (Plan projektfenster.md, P1 + P4/D21/D24): links die
// expandierten Projekt-Skills, dazu der Modus „Quellen durchsuchen" —
// eine oder mehrere Skill-Quellen pro Projekt (Default aus den
// Dashboard-Settings), Ordnerstruktur als Organisation, Import = das
// `speccify add/expand`-Kommando wird ins Agent-Terminal getippt
// (D14-Haltung: Aktionen laufen über den Agenten, die App liest nur).

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import Markdown, { stripFrontmatter } from "../../components/Markdown";
import { SourceAddForm, SourceRow } from "../../components/SourcesPanel";
import { listSources, type SourceInfo } from "../../lib/sources";
import { LoadingBoundary, useAsync } from "../../components/ui";
import {
  InspectorButton,
  InspectorPanel,
  InspectorPortal,
  NavEmpty,
  NavigatorPortal,
  inlineInspector,
  showTab,
  useInspector,
} from "../../lib/panels";
import { copyPrompt } from "../../lib/prompt";

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

interface BrowseSkill {
  name: string;
  category: string;
  file: string;
  description: string | null;
  id: string | null;
}

/// `--source` ist die Quelle selbst (URL oder Ordner, D3): `add` merkt sie in
/// speccify.yaml, danach finden lock/verify/expand den Skill ohne Angabe.
function quoteArgument(value: string): string {
  return "'" + value.replace(/'/g, /Win/.test(navigator.platform) ? "''" : "'\"'\"'") + "'";
}

function importCommand(skill: BrowseSkill, location: string, project: string): string | null {
  if (!skill.id) return null;
  return `speccify add ${quoteArgument(skill.id)} --source ${quoteArgument(location)} --project ${quoteArgument(project)} && speccify expand ${quoteArgument(skill.name)} --project ${quoteArgument(project)}`;
}

function SourceBrowser({ project }: { project: string }) {
  const config = useAsync(() => listSources(project), `skill-sources:${project}`);
  const [source, setSource] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  const all: SourceInfo[] = config.data ?? [];
  const active = all.find((entry) => entry.location === source) ?? all[0] ?? null;
  const activeSource = active?.location ?? null;

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

  const importSkill = (skill: BrowseSkill) => {
    if (!active?.path) return;
    const command = importCommand(skill, active.location, project);
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
      <NavigatorPortal tab="skills" fallback={(children) => children}>
      <div className="mb-2 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={activeSource ?? ""}
            onChange={(event) => {
              setSource(event.target.value || null);
              setSelected(null);
            }}
            className="min-w-0 flex-1 rounded border border-slate-300 px-2 py-1.5 text-xs"
          >
            {all.length === 0 ? <option value="">— keine Quelle —</option> : null}
            {all.map((entry) => (
              <option key={entry.location} value={entry.location}>
                {entry.name} · {entry.scope === "project" ? "Projekt" : "global"}
                {entry.kind === "git" ? " · Git" : ""}
                {entry.state !== "ready" ? " · nicht geklont" : ""}
              </option>
            ))}
          </select>
          <button
            onClick={() => setAdding((value) => !value)}
            className="rounded border border-slate-300 px-2.5 py-1.5 text-xs text-slate-600 hover:bg-slate-100"
            title="Git-URL oder Ordner für dieses Projekt anbinden"
          >
            {adding ? "Abbrechen" : "+ Quelle"}
          </button>
        </div>
        {adding ? (
          <SourceAddForm
            compact
            project={project}
            onAdded={async (added) => {
              setAdding(false);
              await config.reload();
              setSource(added.location);
              setSelected(null);
            }}
          />
        ) : null}
        {active ? (
          <ul>
            <SourceRow
              source={active}
              project={project}
              removable={active.scope === "project"}
              onChanged={async () => {
                await config.reload();
                setSelected(null);
                await skills.reload();
              }}
            />
          </ul>
        ) : null}
      </div>
      </NavigatorPortal>
      {notice ? (
        <p className="mb-2 rounded bg-sky-50 px-3 py-2 text-xs text-sky-800">{notice}</p>
      ) : null}
      {all.length === 0 ? (
        <NavigatorPortal tab="skills" fallback={(children) => children}>
          <NavEmpty
            title="Keine Skill-Quelle"
            action={{ label: "+ Quelle für dieses Projekt", onClick: () => setAdding(true) }}
          >
            Ein Repo (GitHub, GitLab, …) oder ein Ordner mit{" "}
            <code>skills/&lt;name&gt;/SKILL.md</code>. Global für alle Projekte im
            Dashboard unter <strong>Bibliothek</strong>, oder hier nur für dieses
            Projekt.
          </NavEmpty>
        </NavigatorPortal>
      ) : (
        <div className="flex min-h-0 flex-1 gap-4">
          <NavigatorPortal tab="skills">
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
          </NavigatorPortal>
          <div className="min-w-0 flex-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-5">
            {selected ? (
              <>
                {(() => {
                  const skill = (skills.data ?? []).find((entry) => entry.file === selected);
                  return skill ? (
                    <InspectorPortal tab="skills" fallback={inlineInspector}>
                      <InspectorPanel
                        title={skill.name}
                        subtitle={selected}
                        meta={[
                          {
                            label: "Quelle",
                            value: (
                              <span>
                                {active?.name}{" "}
                                <span className="font-mono text-xs text-slate-500">{activeSource}</span>
                              </span>
                            ),
                          },
                          { label: "Kategorie", value: skill.category || "— (Wurzel)" },
                          {
                            label: "Id",
                            value: skill.id ? (
                              <span className="font-mono">{skill.id}</span>
                            ) : (
                              "— kein metadata.speccify.scope"
                            ),
                          },
                          { label: "Beschreibung", value: skill.description ?? "—" },
                        ]}
                        actions={
                          <InspectorButton
                            tone="primary"
                            title="Tippt speccify add + expand ins Agent-Terminal"
                            onClick={() => importSkill(skill)}
                          >
                            Importieren (expand)
                          </InspectorButton>
                        }
                      />
                    </InspectorPortal>
                  ) : null;
                })()}
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

/// Quelle + Ordner wählen → `speccify export` ins Agent-Terminal (D4: die App
/// committet nicht selbst; das macht der Git-Tab im Checkout oder der Agent).
function ExportForm({
  project,
  skill,
  sources,
  onDone,
}: {
  project: string;
  skill: string;
  sources: SourceInfo[];
  onDone: (message: string | null) => void;
}) {
  const ready = sources.filter((entry) => entry.path);
  const [location, setLocation] = useState<string | null>(null);
  const [category, setCategory] = useState("skills");
  const target = ready.find((entry) => entry.location === location) ?? ready[0];
  if (!target) {
    return (
      <p className="rounded bg-amber-50 px-3 py-2 text-xs text-amber-800">
        Keine Quelle bereit — im Modus „Quellen durchsuchen“ eine anbinden (Git-URL oder
        Ordner) oder im Dashboard unter Bibliothek.
      </p>
    );
  }
  const folder = category.trim() || "skills";
  const command = `speccify export ${quoteArgument(skill)} --to ${quoteArgument(target.path!)} --category ${quoteArgument(folder)} --project ${quoteArgument(project)}`;
  return (
    <div className="space-y-2 rounded border border-slate-200 bg-slate-50 p-3 text-xs">
      <label className="block">
        <span className="mb-1 block font-medium text-slate-600">Quelle</span>
        <select
          value={target.location}
          onChange={(event) => setLocation(event.target.value)}
          className="w-full rounded border border-slate-300 bg-white px-2 py-1.5"
        >
          {ready.map((entry) => (
            <option key={entry.location} value={entry.location}>
              {entry.name} · {entry.scope === "project" ? "Projekt" : "global"}
              {entry.kind === "git" ? " · Git" : ""}
            </option>
          ))}
        </select>
      </label>
      <label className="block">
        <span className="mb-1 block font-medium text-slate-600">Ordner in der Quelle (Kategorie)</span>
        <input
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          className="w-full rounded border border-slate-300 bg-white px-2 py-1.5 font-mono"
          spellCheck={false}
        />
      </label>
      <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-white px-2 py-1.5 font-mono text-[11px] text-slate-600">
        {command}
      </pre>
      <p className="text-slate-500">
        Der Export streicht „## In this project“, setzt Version und Scope, nimmt Tools als
        Vertrag mit und listet Stellen, die projektspezifisch aussehen. Committen und Pushen
        passiert danach im Quell-Checkout — per Git-Tab oder Agent.
      </p>
      <div className="flex gap-2">
        <button
          onClick={() => {
            window.dispatchEvent(new CustomEvent("speccify:type-command", { detail: command }));
            onDone(
              `Kommando ins Agent-Terminal getippt (Enter dort bestätigt): ${skill} nach ${target.name} exportieren.`,
            );
          }}
          className="rounded bg-slate-800 px-3 py-1.5 text-white hover:bg-slate-700"
        >
          Ins Terminal tippen
        </button>
        <button
          onClick={() => onDone(null)}
          className="rounded px-3 py-1.5 text-slate-500 hover:bg-slate-100"
        >
          Abbrechen
        </button>
      </div>
    </div>
  );
}

export default function SkillsTab({ project, refresh }: { project: string; refresh?: number }) {
  const { data, loading, error, reload } = useAsync(
    () => invoke<SkillEntry[]>("project_skills", { project }),
    `skills:${project}`,
  );
  const [mode, setMode] = useState<"project" | "browse">("project");
  // Export (Plan skill-quellen-und-export.md, Q3): Quelle + Ordner wählen,
  // `speccify export` landet im Agent-Terminal — committet wird im Checkout.
  const [exporting, setExporting] = useState<string | null>(null);
  const [exportNotice, setExportNotice] = useState<string | null>(null);
  const sources = useAsync(() => listSources(project), `skill-sources:${project}`);
  const [selected, setSelected] = useState<string | null>(null);
  const inspector = useInspector("skills");
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
      <NavigatorPortal tab="skills" fallback={(children) => children}>
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
      </NavigatorPortal>
      {mode === "browse" ? (
        <SourceBrowser project={project} />
      ) : (
        <LoadingBoundary loading={loading} error={error} label="Skills lesen…">
          {skills.length === 0 ? (
            <>
              <NavigatorPortal tab="skills" fallback={() => null}>
                <NavEmpty
                  title="Noch keine Skills im Projekt"
                  action={{ label: "Quellen durchsuchen", onClick: () => setMode("browse") }}
                >
                  Skills liegen unter <code>.agent/skills/</code> und kommen per{" "}
                  <code>speccify expand</code> aus einer Quelle. Durchsuche eine Quelle
                  und importiere — oder bitte den Agenten im Terminal darum.
                </NavEmpty>
              </NavigatorPortal>
              <p className="text-sm text-slate-500">
                Keine Skills unter <code>.agent/skills/</code> — über „Quellen
                durchsuchen" importieren oder den Agenten im Terminal bitten
                (<code>speccify expand</code>).
              </p>
            </>
          ) : (
            <div className="flex h-full min-h-0 gap-4">
              <NavigatorPortal tab="skills">
              <ul className="space-y-1">
                {skills.map((entry) => (
                  <li key={entry.name}>
                    <button
                      onClick={() => {
                        setSelected(entry.name);
                        inspector.reveal();
                      }}
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
              </NavigatorPortal>
              <div className="min-w-0 flex-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-5">
                {skill ? (
                  <>
                    <InspectorPortal tab="skills" fallback={inlineInspector}>
                      <InspectorPanel
                        title={skill.name}
                        subtitle={skill.file}
                        meta={
                          skill.origin
                            ? [
                                {
                                  label: "Herkunft",
                                  value: <span className="font-mono">{skill.origin.source}</span>,
                                },
                                { label: "Version", value: skill.origin.version ?? "—" },
                                { label: "Expandiert", value: skill.origin.expanded ?? "—" },
                                {
                                  label: "Tools",
                                  value:
                                    skill.origin.tools.length > 0
                                      ? skill.origin.tools.join(", ")
                                      : "—",
                                },
                              ]
                            : [
                                {
                                  label: "Herkunft",
                                  value: "Projekteigener Skill (keine Herkunft in expansions.yaml)",
                                },
                              ]
                        }
                        actions={
                          <>
                            <InspectorButton
                              title="Pfad + Inhalt als Markdown-Prompt in die Zwischenablage"
                              disabled={body.data === null}
                              onClick={() => void copyPrompt(skill.file, body.data ?? "")}
                            >
                              Als Prompt kopieren
                            </InspectorButton>
                            {skill.origin && skill.origin.tools.length > 0 ? (
                              <InspectorButton onClick={() => showTab("tools")}>
                                Tools ansehen
                              </InspectorButton>
                            ) : null}
                            <InspectorButton
                              title="Als allgemeinen Skill in eine Quelle exportieren (speccify export)"
                              onClick={() => {
                                setExportNotice(null);
                                setExporting(exporting === skill.name ? null : skill.name);
                              }}
                            >
                              Exportieren…
                            </InspectorButton>
                          </>
                        }
                      >
                        {exporting === skill.name ? (
                          <ExportForm
                            project={project}
                            skill={skill.name}
                            sources={sources.data ?? []}
                            onDone={(message) => {
                              setExporting(null);
                              setExportNotice(message);
                            }}
                          />
                        ) : exportNotice ? (
                          <p className="rounded bg-sky-50 px-3 py-2 text-xs text-sky-800">
                            {exportNotice}
                          </p>
                        ) : null}
                      </InspectorPanel>
                    </InspectorPortal>
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
