// Git-Tab (Plan ide-im-projektfenster.md, I2 + I3): Status, Diff mit
// Hunk-Staging, Stagen, Verwerfen, Commit, Log mit Commit-Details, Datei-
// Historie, Branches — über das System-git (git_cmd.rs). Pull/Push laufen
// mit Live-Ausgabe über die Aktions-Mechanik (project_action_run, run_id
// „git:…") und erscheinen in der Aktivitätsanzeige. Navigator: Branch +
// Änderungen; Mitte: Commit/Branches, Diff, Ausgabe, Log; Inspektor: Auswahl mit Tabs.

import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { writeText } from "@tauri-apps/plugin-clipboard-manager";
import DiffView from "../../components/DiffView";
import GitWorkspace, { type BranchAction } from "./GitWorkspace";
import { beginActivity, endActivity, trackActivity } from "../../lib/activity";
import {
  type GitBranch,
  type GitCommit,
  type GitCommitDetail,
  type GitEntry,
  type GitStatus,
  STATUS_LABEL,
  entryLabel,
  gitApplyPatch,
  gitBranches,
  gitBranchRename,
  gitBranchDelete,
  gitCommit,
  gitCommitDetail,
  gitCommitDiff,
  gitDiff,
  gitDiscard,
  gitFileLog,
  gitInit,
  gitLog,
  gitStage,
  gitStatus,
  gitSwitch,
  hunkPatch,
  isStaged,
  isUnstaged,
  parseDiff,
  shortDate,
} from "../../lib/git";
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

interface Selection {
  path: string;
  staged: boolean;
}

interface RunState {
  id: string;
  lines: string[];
  running: boolean;
  exit: number | null;
}

function HunkButton({ children, onClick, disabled, title }: { children: string; onClick: () => void; disabled?: boolean; title?: string }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className="rounded border border-slate-300 bg-white px-1.5 py-0 text-[10px] text-slate-600 hover:bg-slate-100 disabled:opacity-40"
    >
      {children}
    </button>
  );
}

function CommitList({
  commits,
  selected,
  onSelect,
  empty,
}: {
  commits: GitCommit[];
  selected: string | null;
  onSelect: (hash: string) => void;
  empty: string;
}) {
  if (commits.length === 0) return <p className="text-xs text-slate-400">{empty}</p>;
  return (
    <ul className="space-y-0.5 text-xs">
      {commits.map((entry) => {
        const active = selected === entry.hash;
        return (
          <li key={entry.hash}>
            <button
              onClick={() => onSelect(entry.hash)}
              className={`flex w-full gap-2 rounded px-1.5 py-1 text-left ${
                active ? "bg-slate-800 text-white" : "hover:bg-slate-100"
              }`}
              title={`${entry.short} · ${entry.author} · ${shortDate(entry.date)}`}
            >
              <span className={`shrink-0 font-mono ${active ? "text-slate-300" : "text-slate-400"}`}>
                {entry.short}
              </span>
              <span className="min-w-0 flex-1 truncate">{entry.subject}</span>
              <span className={`shrink-0 ${active ? "text-slate-300" : "text-slate-400"}`}>
                {entry.date.slice(0, 10)}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

import { useProjectActivity } from "../../lib/projectActivity";

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
  const projectActive = useProjectActivity();
  const [log, setLog] = useState<GitCommit[]>([]);
  const [branches, setBranches] = useState<GitBranch[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Selection | null>(null);
  const [diff, setDiff] = useState<string>("");
  // Datei-Historie der Auswahl + der dort gewählte Commit (Diff dieser Datei).
  const [fileHistory, setFileHistory] = useState<GitCommit[]>([]);
  const [historyCommit, setHistoryCommit] = useState<string | null>(null);
  const [historyDiff, setHistoryDiff] = useState<string>("");
  // Commit aus dem Log: Details im Inspektor, Diff in der Mitte.
  const [selectedCommit, setSelectedCommit] = useState<string | null>(null);
  const [commitDetail, setCommitDetail] = useState<GitCommitDetail | null>(null);
  const [commitFile, setCommitFile] = useState<string | null>(null);
  const [commitDiff, setCommitDiff] = useState<string>("");
  const [showBranches, setShowBranches] = useState(false);
  const [busy, setBusy] = useState(false);
  const [discardArmed, setDiscardArmed] = useState<string | null>(null);
  const [run, setRun] = useState<RunState | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const inspector = useInspector("git");
  const activityRef = useRef<string | null>(null);
  const messageRef = useRef<HTMLInputElement>(null);
  const mutationRef = useRef(false);
  const remoteRunRef = useRef<string | null>(null);
  const listenersReadyRef = useRef<Promise<unknown> | null>(null);

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
      const next = await gitStatus(project);
      setStatus(next);
      if (next.error) setError(next.error);
      if (next.repo) {
        setLog(await gitLog(project, 30));
        setBranches(await gitBranches(project));
      }
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

  // Diff + Historie der Auswahl nachladen (auch nach Watcher-Meldungen).
  useEffect(() => {
    if (!selected) {
      setDiff("");
      setFileHistory([]);
      return;
    }
    void gitDiff(project, selected.path, selected.staged)
      .then(setDiff)
      .catch((e) => setDiff(String(e)));
    void gitFileLog(project, selected.path, 100)
      .then(setFileHistory)
      .catch(() => setFileHistory([]));
  }, [project, selected, refresh]);

  useEffect(() => {
    if (!selected || !historyCommit) {
      setHistoryDiff("");
      return;
    }
    void gitCommitDiff(project, historyCommit, selected.path)
      .then(setHistoryDiff)
      .catch((e) => setHistoryDiff(String(e)));
  }, [project, selected, historyCommit]);

  useEffect(() => {
    if (!selectedCommit) {
      setCommitDetail(null);
      setCommitDiff("");
      return;
    }
    void gitCommitDetail(project, selectedCommit)
      .then(setCommitDetail)
      .catch((e) => setError(String(e)));
  }, [project, selectedCommit]);

  useEffect(() => {
    if (!selectedCommit) return;
    void gitCommitDiff(project, selectedCommit, commitFile)
      .then(setCommitDiff)
      .catch((e) => setCommitDiff(String(e)));
  }, [project, selectedCommit, commitFile]);

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
        if (event.payload.run_id !== remoteRunRef.current) return;
        remoteRunRef.current = null;
        mutationRef.current = false;
        setBusy(false);
        setRun((previous) =>
          previous && previous.id === event.payload.run_id
            ? { ...previous, running: false, exit: event.payload.error ? -1 : event.payload.exit_code,
                lines: event.payload.error ? [...previous.lines, event.payload.error] : previous.lines }
            : previous,
        );
        if (activityRef.current) {
          endActivity(
            activityRef.current,
            event.payload.error || event.payload.exit_code !== 0 ? "error" : "ok",
            event.payload.error ?? undefined,
          );
          activityRef.current = null;
        }
        void load();
      },
    );
    listenersReadyRef.current = Promise.all([out, exit]);
    void listenersReadyRef.current.catch(() => {}); // Report on action attempt, never run without output listeners.
    return () => {
      void out.then((dispose) => dispose()).catch(() => {});
      void exit.then((dispose) => dispose()).catch(() => {});
    };
  }, [load]);

  const remote = useCallback(
    async (verb: "fetch" | "pull" | "push") => {
      if (mutationRef.current) return;
      mutationRef.current = true;
      setBusy(true);
      setError(null);
      const id = `git:${verb}:${crypto.randomUUID()}`;
      remoteRunRef.current = id;
      setRun({ id, lines: [], running: true, exit: null });
      activityRef.current = beginActivity("action", `git ${verb}`, status?.branch ?? undefined);
      try {
        await listenersReadyRef.current;
        await invoke("project_action_run", { project, runId: id, commandLine: `git ${verb}` });
      } catch (e) {
        setRun({ id, lines: [String(e)], running: false, exit: -1 });
        if (activityRef.current) endActivity(activityRef.current, "error", String(e));
        activityRef.current = null;
        remoteRunRef.current = null;
        mutationRef.current = false;
        setBusy(false);
      }
    },
    [project, status?.branch],
  );

  const openCommitPanel = useCallback(() => {
    messageRef.current?.scrollIntoView({ block: "center" });
    messageRef.current?.focus();
  }, []);

  // Toolbar-Knöpfe (I3): pull/push/commit kommen als Ereignis.
  useEffect(() => {
    const handler = (event: Event) => {
      const verb = (event as CustomEvent<string>).detail;
      if (!projectActive.current) return;
      if (verb === "commit") openCommitPanel();
      else if (verb === "fetch" || verb === "pull" || verb === "push") void remote(verb);
    };
    window.addEventListener("speccify:git", handler);
    return () => window.removeEventListener("speccify:git", handler);
  }, [remote, openCommitPanel]);

  const guard = async (work: () => Promise<unknown>) => {
    if (mutationRef.current) return false;
    mutationRef.current = true;
    setBusy(true);
    setError(null);
    try {
      await work();
      await load();
      return true;
    } catch (e) {
      setError(String(e));
      return false;
    } finally {
      mutationRef.current = false;
      setBusy(false);
    }
  };

  const stage = (paths: string[], value: boolean) => guard(() => gitStage(project, paths, value));

  const stageHunk = (index: number, reverse: boolean) =>
    guard(async () => {
      const patch = hunkPatch(parseDiff(diff), index);
      if (!patch) return;
      await gitApplyPatch(project, patch, reverse);
      if (selected) setDiff(await gitDiff(project, selected.path, selected.staged));
    });

  const discard = (path: string) =>
    guard(async () => {
      await gitDiscard(project, [path]);
      setDiscardArmed(null);
      setSelected(null);
      window.dispatchEvent(new CustomEvent("speccify:worktree-changed"));
    });

  const commit = (message: string) => guard(async () => {
      const summary = await trackActivity("action", "git commit", () => gitCommit(project, message));
      setRun({ id: "git:commit", lines: [summary], running: false, exit: 0 });
      setSelected(null);
      setSelectedCommit(null);
      window.dispatchEvent(new CustomEvent("speccify:worktree-changed"));
  });

  const branchAction = (action: BranchAction, branch: string, name: string) =>
    guard(async () => {
      const summary = await trackActivity("action", `git branch ${action}`, () =>
        action === "rename" ? gitBranchRename(project, branch, name)
        : action === "delete" ? gitBranchDelete(project, branch)
        : gitSwitch(project, action === "create" ? name : branch, action === "create"));
      setRun({ id: `git:branch ${action}`, lines: [summary], running: false, exit: 0 });
      setSelected(null);
      setSelectedCommit(null);
      window.dispatchEvent(new CustomEvent("speccify:worktree-changed"));
    });

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
            setSelectedCommit(null);
            setHistoryCommit(null);
            setDiscardArmed(null);
            inspector.reveal();
          }}
          className="min-w-0 flex-1 truncate py-1 text-left text-[12.5px]"
          title={`${entry.path} — ${entryLabel(entry, stagedList)}`}
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
            onClick: () => void guard(() => trackActivity("action", "git init", () => gitInit(project))),
          }}
        >
          Dieses Projekt ist noch kein Git-Repository. Mit einem Repository sieht der Agent
          seine Änderungen, und Commits nennen die Spec, zu der sie gehören.
        </NavEmpty>
      ) : (
        <>
          <div className="mb-2 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2">
            <div className="flex items-center justify-between gap-2">
              <button
                onClick={() => { setShowBranches(true); openCommitPanel(); }}
                className="truncate font-mono text-xs font-semibold text-slate-800 hover:underline"
                title="Branch-Verwaltung öffnen"
              >
                {status?.branch ?? "(kein Branch)"}
              </button>
              <span className="shrink-0 font-mono text-[10px] text-slate-500">
                {status?.upstream ? `↑${status.ahead} ↓${status.behind}` : "kein Upstream"}
              </span>
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1">
              <button
                onClick={openCommitPanel}
                className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-medium text-white hover:bg-slate-700"
                title="Commit-Nachricht schreiben oder den Agenten committen lassen"
              >
                Commit…
              </button>
              {(["fetch", "pull", "push"] as const).map((verb) => (
                <button
                  key={verb}
                  onClick={() => void remote(verb)}
                  disabled={busy}
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
                    disabled={busy}
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
                    disabled={busy}
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


  const details = current && selected ? (
    <InspectorPortal tab="git" fallback={inlineInspector}>
      <InspectorPanel
        title={current.path.split("/").pop() ?? current.path}
        subtitle={current.path}
        meta={[
          { label: "Zustand", value: entryLabel(current, selected.staged) },
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
            {!selected.staged ? (
              discardArmed === current.path ? (
                <>
                  <InspectorButton tone="danger" disabled={busy} onClick={() => void discard(current.path)}>
                    Ja, verwerfen
                  </InspectorButton>
                  <InspectorButton onClick={() => setDiscardArmed(null)}>Abbrechen</InspectorButton>
                </>
              ) : (
                <InspectorButton
                  title={current.untracked ? "Datei löschen (git clean)" : "Änderungen im Arbeitsbaum zurücksetzen (git restore)"}
                  onClick={() => setDiscardArmed(current.path)}
                >
                  Verwerfen…
                </InspectorButton>
              )
            ) : null}
          </>
        }
        tabs={[
          {
            id: "changes",
            label: "Änderungen",
            content: (
              <p className="text-xs text-slate-500">
                {current.untracked
                  ? "Neue Datei — komplett stagen oder verwerfen."
                  : selected.staged
                    ? "Der Diff in der Mitte zeigt den Index. „Hunk zurücknehmen“ holt einzelne Blöcke wieder heraus."
                    : "Der Diff in der Mitte zeigt den Arbeitsbaum gegen den Index. „Hunk stagen“ übernimmt einzelne Blöcke."}
                {historyCommit ? (
                  <button
                    onClick={() => setHistoryCommit(null)}
                    className="ml-1 text-sky-700 hover:underline"
                  >
                    Zurück zum aktuellen Diff.
                  </button>
                ) : null}
              </p>
            ),
          },
          {
            id: "history",
            label: `Historie${fileHistory.length ? ` (${fileHistory.length})` : ""}`,
            content: (
              <CommitList
                commits={fileHistory}
                selected={historyCommit}
                onSelect={(hash) => setHistoryCommit((previous) => (previous === hash ? null : hash))}
                empty={current.untracked ? "Noch nie committet." : "Keine Historie."}
              />
            ),
          },
        ]}
      />
    </InspectorPortal>
  ) : null;

  const commitPanelDetail =
    selectedCommit && commitDetail ? (
      <InspectorPortal tab="git" fallback={inlineInspector}>
        <InspectorPanel
          title={commitDetail.subject}
          subtitle={`${commitDetail.short} · ${commitDetail.author} · ${shortDate(commitDetail.date)}`}
          meta={[
            { label: "Hash", value: <span className="font-mono">{commitDetail.hash}</span> },
            { label: "Dateien", value: `${commitDetail.files.length}` },
          ]}
          actions={
            <>
              <InspectorButton onClick={() => void writeText(commitDetail.hash)}>Hash kopieren</InspectorButton>
              <InspectorButton
                title="Diff des Commits als Markdown-Prompt in die Zwischenablage"
                onClick={() => void writeText(fencedPrompt(`git show ${commitDetail.short}`, commitDiff))}
              >
                Diff als Prompt
              </InspectorButton>
              <InspectorButton onClick={() => setSelectedCommit(null)}>Schließen</InspectorButton>
            </>
          }
          tabs={[
            {
              id: "files",
              label: `Dateien (${commitDetail.files.length})`,
              content: (
                <ul className="space-y-0.5 text-xs">
                  <li>
                    <button
                      onClick={() => setCommitFile(null)}
                      className={`w-full rounded px-1.5 py-1 text-left ${commitFile === null ? "bg-slate-800 text-white" : "hover:bg-slate-100"}`}
                    >
                      Alle Dateien
                    </button>
                  </li>
                  {commitDetail.files.map((file) => (
                    <li key={file.path}>
                      <button
                        onClick={() => setCommitFile(file.path)}
                        className={`flex w-full gap-2 rounded px-1.5 py-1 text-left ${commitFile === file.path ? "bg-slate-800 text-white" : "hover:bg-slate-100"}`}
                        title={STATUS_LABEL[file.status] ?? file.status}
                      >
                        <span className={`w-3 shrink-0 text-center font-mono ${commitFile === file.path ? "text-slate-300" : "text-slate-400"}`}>
                          {file.status}
                        </span>
                        <span className="min-w-0 flex-1 truncate">{file.path}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              ),
            },
            {
              id: "message",
              label: "Nachricht",
              content: (
                <pre className="whitespace-pre-wrap font-mono text-[11px] text-slate-700">
                  {commitDetail.subject}
                  {commitDetail.body ? `\n\n${commitDetail.body}` : ""}
                </pre>
              ),
            },
          ]}
        />
      </InspectorPortal>
    ) : null;

  const diffTitle = selected
    ? historyCommit
      ? `Commit ${historyCommit.slice(0, 7)} · ${selected.path}`
      : `${selected.staged ? "Index" : "Arbeitsbaum"} · ${selected.path}`
    : selectedCommit && commitDetail
      ? `Commit ${commitDetail.short}${commitFile ? ` · ${commitFile}` : " · alle Dateien"}`
      : null;
  const shownDiff = selected ? (historyCommit ? historyDiff : diff) : selectedCommit ? commitDiff : "";
  const hunkActions =
    selected && current && !historyCommit && !current.untracked && !current.conflicted
      ? (index: number) => (
          <HunkButton
            onClick={() => void stageHunk(index, selected.staged)}
            disabled={busy}
            title={selected.staged ? "Diesen Block aus dem Index nehmen" : "Nur diesen Block stagen"}
          >
            {selected.staged ? "Hunk zurücknehmen" : "Hunk stagen"}
          </HunkButton>
        )
      : undefined;

  return (
    <div className="flex h-full min-h-0 gap-4">
      {navigator}
      <div className="flex min-w-0 flex-1 flex-col gap-3 overflow-y-auto">
        {status?.repo ? <GitWorkspace key={project} project={project} status={status} branches={branches}
          stagedCount={staged.length} busy={busy} showBranches={showBranches} setShowBranches={setShowBranches}
          messageRef={messageRef} onCommit={commit} onBranch={branchAction} onAgent={() => askAgentToCommit(staged.length)} /> : null}
        {details}
        {commitPanelDetail}
        {busy ? <p role="status" className="text-xs text-slate-500">Git-Aktion läuft…</p> : null}
        {notice ? <p role="status" className="text-xs text-sky-800">{notice}</p> : null}
        {error ? <div role="alert" className="rounded bg-red-50 px-3 py-2 text-xs text-red-700">{error}
          <button className="ml-2 underline" onClick={() => setError(null)}>Schließen</button></div> : null}
        {status?.repo && !selected && !selectedCommit && !run ? (
          <p className="text-sm text-slate-400">
            Datei links wählen für den Diff, Commit unten für Details. Oben den Index committen oder Branches verwalten.
          </p>
        ) : null}
        {run ? (
          <div className="rounded-lg border border-slate-200 bg-slate-900 p-3 font-mono text-[11px] text-slate-200">
            <div className="mb-1 flex items-center justify-between text-slate-400">
              <span>git {run.id.split(":")[1]}</span>
              <span className="flex items-center gap-2">
                {run.running ? "läuft…" : run.exit === 0 ? "✓ fertig" : `✕ Exit ${run.exit ?? "?"}`}
                {!run.running ? (
                  <button onClick={() => setRun(null)} className="text-slate-500 hover:text-white" title="Ausgabe schließen">
                    ×
                  </button>
                ) : null}
              </span>
            </div>
            <pre className="max-h-48 overflow-auto whitespace-pre-wrap">{run.lines.join("\n") || " "}</pre>
          </div>
        ) : null}
        {diffTitle ? (
          <div className="rounded-lg border border-slate-200 bg-white">
            <div className="border-b border-slate-200 px-3 py-1.5 font-mono text-[11px] text-slate-500">
              {diffTitle}
            </div>
            <DiffView text={shownDiff} hunkActions={hunkActions} />
          </div>
        ) : null}
        {status?.repo ? (
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Letzte Commits
            </h3>
            <CommitList
              commits={log}
              selected={selectedCommit}
              onSelect={(hash) => {
                setSelected(null);
                setHistoryCommit(null);
                setCommitFile(null);
                setSelectedCommit((previous) => (previous === hash ? null : hash));
                inspector.reveal();
              }}
              empty="Noch kein Commit."
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}
