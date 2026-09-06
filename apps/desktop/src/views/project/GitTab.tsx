// Git-Tab (Plan ide-im-projektfenster.md, I2): Status, Diff, Stagen,
// Commit, Log — über das System-git (git_cmd.rs). Pull/Push laufen mit
// Live-Ausgabe über die Aktions-Mechanik (project_action_run, run_id
// „git:…") und erscheinen in der Aktivitätsanzeige. Navigator: Branch +
// Änderungen; Mitte: Commit-Box, Diff, Log; Inspektor: die gewählte Datei.

import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { writeText } from "@tauri-apps/plugin-clipboard-manager";
import { beginActivity, endActivity, trackActivity } from "../../lib/activity";
import { fencedPrompt } from "../../lib/prompt";
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

interface GitEntry {
  path: string;
  index: string;
  worktree: string;
  untracked: boolean;
  conflicted: boolean;
  renamed_from: string | null;
}

interface GitStatus {
  repo: boolean;
  branch: string | null;
  upstream: string | null;
  ahead: number;
  behind: number;
  entries: GitEntry[];
  error: string | null;
}

interface GitCommit {
  hash: string;
  short: string;
  author: string;
  date: string;
  subject: string;
}

interface Selection {
  path: string;
  staged: boolean;
}

const STATUS_LABEL: Record<string, string> = {
  M: "geändert",
  A: "neu",
  D: "gelöscht",
  R: "umbenannt",
  C: "kopiert",
  T: "Typ geändert",
  U: "Konflikt",
  "?": "unversioniert",
};

function label(entry: GitEntry, staged: boolean): string {
  if (entry.conflicted) return "Konflikt";
  if (entry.untracked) return "unversioniert";
  const code = staged ? entry.index : entry.worktree;
  return STATUS_LABEL[code] ?? code;
}

function isStaged(entry: GitEntry): boolean {
  return !entry.untracked && !entry.conflicted && entry.index !== ".";
}

function isUnstaged(entry: GitEntry): boolean {
  return entry.untracked || entry.conflicted || entry.worktree !== ".";
}

function DiffView({ text }: { text: string }) {
  if (!text.trim()) return <p className="p-4 text-xs text-slate-400">Kein Unterschied.</p>;
  return (
    <pre className="overflow-auto p-3 font-mono text-[11.5px] leading-5">
      {text.split("\n").map((line, index) => {
        const tone = line.startsWith("+++") || line.startsWith("---")
          ? "text-slate-500"
          : line.startsWith("+")
            ? "bg-emerald-50 text-emerald-800"
            : line.startsWith("-")
              ? "bg-red-50 text-red-800"
              : line.startsWith("@@")
                ? "text-sky-700"
                : "text-slate-700";
        return (
          <div key={index} className={`whitespace-pre ${tone}`}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}

export default function GitTab({
  project,
  refresh,
  visible = true,
}: {
  project: string;
  refresh?: number;
  /** Tab ist zu sehen — dann Status beim Erscheinen und alle 4 s nachladen.
   *  Der Watcher kennt nur die .agent-Bereiche, nicht den Arbeitsbaum
   *  (BO-Finding 2026-09-06: geänderte Datei fehlte im Git-Tab). */
  visible?: boolean;
}) {
  const [status, setStatus] = useState<GitStatus | null>(null);
  const [log, setLog] = useState<GitCommit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Selection | null>(null);
  const [diff, setDiff] = useState<string>("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [run, setRun] = useState<{ id: string; lines: string[]; running: boolean; exit: number | null } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const inspector = useInspector("git");
  const activityRef = useRef<string | null>(null);
  const messageRef = useRef<HTMLTextAreaElement>(null);

  // BO 2026-09-06: Committen auch „via Button" — mit eigener Nachricht
  // oder durch den Agenten. Der Agent bekommt den Auftrag ins Terminal
  // getippt (wie der Skill-Import) und bestätigt ihn dort mit Enter.
  const askAgentToCommit = (stagedCount: number) => {
    const prompt =
      stagedCount > 0
        ? "Bitte prüfe die gestageten Änderungen (git diff --cached), schreibe eine Conventional-Commit-Nachricht auf Deutsch und committe sie. Nicht pushen."
        : "Bitte sieh dir die Änderungen an (git status, git diff), stage was zusammengehört, schreibe eine Conventional-Commit-Nachricht auf Deutsch und committe. Nicht pushen.";
    window.dispatchEvent(new CustomEvent("speccify:type-command", { detail: prompt }));
    setNotice(
      "Auftrag ins Agent-Terminal getippt — dort mit Enter bestätigen. (Läuft kein Terminal, zuerst „Agent-Terminal starten“.)",
    );
  };

  const load = useCallback(async () => {
    try {
      const next = await invoke<GitStatus>("project_git_status", { project });
      setStatus(next);
      setError(next.error);
      if (next.repo) setLog(await invoke<GitCommit[]>("project_git_log", { project, limit: 20 }));
    } catch (e) {
      setError(String(e));
    }
  }, [project]);

  useEffect(() => {
    void load();
  }, [load, refresh]);

  // Sichtbar: sofort und dann alle 4 s `git status` (billig, lokal) —
  // so erscheinen Änderungen aus Editor, Agent-Terminal oder von außen.
  useEffect(() => {
    if (!visible) return;
    void load();
    const timer = setInterval(() => void load(), 4000);
    return () => clearInterval(timer);
  }, [visible, load]);

  // Speichern im Dateien-Tab meldet sich direkt.
  useEffect(() => {
    const handler = () => void load();
    window.addEventListener("speccify:worktree-changed", handler);
    return () => window.removeEventListener("speccify:worktree-changed", handler);
  }, [load]);

  // Diff der Auswahl nachladen (auch nach Watcher-Meldungen).
  useEffect(() => {
    if (!selected) {
      setDiff("");
      return;
    }
    void invoke<string>("project_git_diff", { project, path: selected.path, staged: selected.staged })
      .then(setDiff)
      .catch((e) => setDiff(String(e)));
  }, [project, selected, refresh]);

  // Pull/Push: Live-Ausgabe über die Aktions-Events.
  useEffect(() => {
    const out = listen<{ run_id: string; line: string }>("action-output", (event) => {
      if (!event.payload.run_id.startsWith("git:")) return;
      setRun((previous) =>
        previous && previous.id === event.payload.run_id
          ? { ...previous, lines: [...previous.lines, event.payload.line].slice(-400) }
          : previous,
      );
    });
    const exit = listen<{ run_id: string; exit_code: number | null; error: string | null }>(
      "action-exit",
      (event) => {
        if (!event.payload.run_id.startsWith("git:")) return;
        setRun((previous) =>
          previous && previous.id === event.payload.run_id
            ? { ...previous, running: false, exit: event.payload.exit_code }
            : previous,
        );
        if (activityRef.current) {
          endActivity(
            activityRef.current,
            event.payload.error || (event.payload.exit_code ?? 0) !== 0 ? "error" : "ok",
            event.payload.error ?? undefined,
          );
          activityRef.current = null;
        }
        void load();
      },
    );
    return () => {
      void out.then((dispose) => dispose());
      void exit.then((dispose) => dispose());
    };
  }, [load]);

  const remote = async (verb: "fetch" | "pull" | "push") => {
    const id = `git:${verb}`;
    setRun({ id, lines: [], running: true, exit: null });
    activityRef.current = beginActivity("action", `git ${verb}`, status?.branch ?? undefined);
    try {
      await invoke("project_action_run", { project, runId: id, commandLine: `git ${verb}` });
    } catch (e) {
      setRun({ id, lines: [String(e)], running: false, exit: -1 });
      if (activityRef.current) endActivity(activityRef.current, "error", String(e));
      activityRef.current = null;
    }
  };

  const stage = async (paths: string[], value: boolean) => {
    setBusy(true);
    setError(null);
    try {
      await invoke("project_git_stage", { project, paths, stage: value });
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const commit = async () => {
    setBusy(true);
    setError(null);
    try {
      const summary = await trackActivity("action", "git commit", () =>
        invoke<string>("project_git_commit", { project, message }),
      );
      setMessage("");
      setRun({ id: "git:commit", lines: [summary], running: false, exit: 0 });
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const entries = status?.entries ?? [];
  const staged = entries.filter(isStaged);
  const unstaged = entries.filter(isUnstaged);
  const current = selected ? entries.find((entry) => entry.path === selected.path) ?? null : null;

  const row = (entry: GitEntry, stagedList: boolean) => {
    const active = selected?.path === entry.path && selected.staged === stagedList;
    return (
      <div
        key={`${stagedList ? "s" : "u"}:${entry.path}`}
        className={`flex items-center gap-1 rounded px-1 ${active ? "bg-slate-800 text-white" : "hover:bg-slate-100"}`}
      >
        <button
          onClick={() => {
            setSelected({ path: entry.path, staged: stagedList });
            inspector.reveal();
          }}
          className="min-w-0 flex-1 truncate py-1 text-left text-[12.5px]"
          title={`${entry.path} — ${label(entry, stagedList)}`}
        >
          <span className={`mr-1.5 inline-block w-3 text-center font-mono text-[10px] ${active ? "text-slate-300" : "text-slate-400"}`}>
            {entry.conflicted ? "U" : entry.untracked ? "?" : stagedList ? entry.index : entry.worktree}
          </span>
          {entry.path}
        </button>
        <button
          onClick={() => void stage([entry.path], !stagedList)}
          disabled={busy}
          title={stagedList ? "Aus dem Index nehmen" : "Stagen"}
          className={`px-1.5 text-xs ${active ? "text-slate-300 hover:text-white" : "text-slate-400 hover:text-slate-800"}`}
        >
          {stagedList ? "−" : "+"}
        </button>
      </div>
    );
  };

  const navigator = (
    <NavigatorPortal tab="git">
      {status && !status.repo ? (
        <NavEmpty
          title="Kein Git-Repository"
          action={{
            label: "Repository anlegen (git init)",
            onClick: () =>
              void trackActivity("action", "git init", () => invoke("project_git_init", { project })).then(load),
          }}
        >
          Dieses Projekt ist noch kein Git-Repository. Mit einem Repository sieht der Agent
          seine Änderungen, und Commits landen in der Ticket-Historie.
        </NavEmpty>
      ) : (
        <>
          <div className="mb-2 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2">
            <div className="flex items-center justify-between gap-2">
              <span className="truncate font-mono text-xs font-semibold text-slate-800">
                {status?.branch ?? "(kein Branch)"}
              </span>
              <span className="shrink-0 font-mono text-[10px] text-slate-500">
                {status?.upstream ? `↑${status.ahead} ↓${status.behind}` : "kein Upstream"}
              </span>
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1">
              <button
                onClick={() => {
                  setSelected(null);
                  inspector.reveal();
                  setTimeout(() => messageRef.current?.focus(), 50);
                }}
                className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-medium text-white hover:bg-slate-700"
                title="Commit-Nachricht schreiben oder den Agenten committen lassen"
              >
                Commit…
              </button>
              {(["fetch", "pull", "push"] as const).map((verb) => (
                <button
                  key={verb}
                  onClick={() => void remote(verb)}
                  disabled={run?.running}
                  className="rounded border border-slate-300 bg-white px-2 py-0.5 text-[11px] text-slate-600 hover:bg-slate-100 disabled:opacity-40"
                >
                  {verb}
                </button>
              ))}
            </div>
          </div>
          {entries.length === 0 ? (
            <NavEmpty title="Alles committet">
              Keine Änderungen im Arbeitsverzeichnis. Was der Agent ändert, erscheint hier
              sofort — zum Sichten, Stagen und Committen.
            </NavEmpty>
          ) : (
            <>
              <div className="mb-1 flex items-center justify-between px-1">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Staged ({staged.length})
                </span>
                {staged.length > 0 ? (
                  <button
                    onClick={() => void stage(staged.map((entry) => entry.path), false)}
                    className="text-[11px] text-slate-400 hover:text-slate-800"
                  >
                    alle −
                  </button>
                ) : null}
              </div>
              <div className="mb-3 space-y-0.5">{staged.map((entry) => row(entry, true))}</div>
              <div className="mb-1 flex items-center justify-between px-1">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Änderungen ({unstaged.length})
                </span>
                {unstaged.length > 0 ? (
                  <button
                    onClick={() => void stage(unstaged.map((entry) => entry.path), true)}
                    className="text-[11px] text-slate-400 hover:text-slate-800"
                  >
                    alle +
                  </button>
                ) : null}
              </div>
              <div className="space-y-0.5">{unstaged.map((entry) => row(entry, false))}</div>
            </>
          )}
        </>
      )}
    </NavigatorPortal>
  );

  // Ohne Dateiauswahl zeigt der Inspektor das Commit-Panel.
  const commitPanel =
    status?.repo && !(current && selected) ? (
      <InspectorPortal tab="git" fallback={inlineInspector}>
        <InspectorPanel
          title="Commit"
          subtitle={status.branch ?? undefined}
          meta={[
            { label: "Staged", value: `${staged.length} Datei(en)` },
            { label: "Änderungen", value: `${unstaged.length} Datei(en)` },
          ]}
          actions={
            <>
              <InspectorButton
                tone="primary"
                disabled={busy || staged.length === 0 || !message.trim()}
                onClick={() => void commit()}
                title={staged.length === 0 ? "Erst stagen (+ in der Liste)" : "Gestagete Änderungen committen"}
              >
                Commit
              </InspectorButton>
              <InspectorButton
                disabled={busy || unstaged.length === 0 || !message.trim()}
                onClick={() =>
                  void stage(unstaged.map((entry) => entry.path), true).then(() => commit())
                }
                title="Alle Änderungen stagen und mit dieser Nachricht committen"
              >
                Alles committen
              </InspectorButton>
              <InspectorButton
                onClick={() => askAgentToCommit(staged.length)}
                title="Der Agent liest die Änderungen, schreibt die Nachricht und committet"
              >
                Agent committen lassen
              </InspectorButton>
            </>
          }
        >
          <textarea
            ref={messageRef}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={(event) => {
              if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && staged.length > 0 && message.trim()) {
                void commit();
              }
            }}
            placeholder="Commit-Nachricht… (⌘⏎ committet)"
            rows={3}
            spellCheck={false}
            className="w-full resize-none rounded border border-slate-300 bg-white px-2 py-1.5 font-mono text-xs"
          />
          {notice ? <p className="mt-2 text-xs text-sky-800">{notice}</p> : null}
        </InspectorPanel>
      </InspectorPortal>
    ) : null;

  const details = current && selected ? (
    <InspectorPortal tab="git" fallback={inlineInspector}>
      <InspectorPanel
        title={current.path.split("/").pop() ?? current.path}
        subtitle={current.path}
        meta={[
          { label: "Zustand", value: label(current, selected.staged) },
          { label: "Index", value: <span className="font-mono">{current.index}</span> },
          { label: "Arbeitsbaum", value: <span className="font-mono">{current.worktree}</span> },
          ...(current.renamed_from ? [{ label: "Vorher", value: current.renamed_from }] : []),
        ]}
        actions={
          <>
            <InspectorButton
              tone="primary"
              disabled={busy}
              onClick={() => void stage([current.path], !selected.staged)}
            >
              {selected.staged ? "Aus dem Index nehmen" : "Stagen"}
            </InspectorButton>
            <InspectorButton
              onClick={() => {
                window.dispatchEvent(new CustomEvent("speccify:open-file", { detail: current.path }));
                showTab("files");
              }}
            >
              Im Editor öffnen
            </InspectorButton>
            <InspectorButton
              title="Diff als Markdown-Prompt in die Zwischenablage"
              onClick={() => void writeText(fencedPrompt(`git diff ${current.path}`, diff))}
            >
              Diff als Prompt
            </InspectorButton>
          </>
        }
      />
    </InspectorPortal>
  ) : null;

  return (
    <div className="flex h-full min-h-0 gap-4">
      {navigator}
      <div className="flex min-w-0 flex-1 flex-col gap-3 overflow-y-auto">
        {commitPanel}
        {details}
        {error ? <p className="rounded bg-red-50 px-3 py-2 text-xs text-red-700">{error}</p> : null}
        {status?.repo && !selected && !run ? (
          <p className="text-sm text-slate-400">
            Datei links wählen für den Diff. Committen im Inspektor: Nachricht schreiben oder den
            Agenten committen lassen.
          </p>
        ) : null}
        {run ? (
          <div className="rounded-lg border border-slate-200 bg-slate-900 p-3 font-mono text-[11px] text-slate-200">
            <div className="mb-1 flex items-center justify-between text-slate-400">
              <span>{run.id.replace("git:", "git ")}</span>
              <span>{run.running ? "läuft…" : run.exit === 0 ? "✓ fertig" : `✕ Exit ${run.exit ?? "?"}`}</span>
            </div>
            <pre className="max-h-48 overflow-auto whitespace-pre-wrap">{run.lines.join("\n") || " "}</pre>
          </div>
        ) : null}
        {selected ? (
          <div className="rounded-lg border border-slate-200 bg-white">
            <div className="border-b border-slate-200 px-3 py-1.5 font-mono text-[11px] text-slate-500">
              {selected.staged ? "Index" : "Arbeitsbaum"} · {selected.path}
            </div>
            <DiffView text={diff} />
          </div>
        ) : null}
        {status?.repo ? (
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Letzte Commits
            </h3>
            {log.length === 0 ? (
              <p className="text-xs text-slate-400">Noch kein Commit.</p>
            ) : (
              <ul className="space-y-1 text-xs">
                {log.map((entry) => (
                  <li key={entry.hash} className="flex gap-2">
                    <span className="shrink-0 font-mono text-slate-400">{entry.short}</span>
                    <span className="min-w-0 flex-1 truncate text-slate-800" title={entry.subject}>
                      {entry.subject}
                    </span>
                    <span className="shrink-0 text-slate-400">{entry.date.slice(0, 10)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
