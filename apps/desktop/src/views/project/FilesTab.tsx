// Dateien-Tab (Plan ide-im-projektfenster.md, I1): Projektbaum im
// Navigator (lazy je Ordner, .gitignore gilt), offene Dateien als Tabs
// über einem CodeMirror-Editor in der Mitte, Datei-Infos und Aktionen im
// Inspektor. Speichern über project_write_file (Cmd/Ctrl-S), Reload bei
// Watcher-Meldungen — nie in eine ungespeicherte Änderung hinein.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { invoke } from "@tauri-apps/api/core";
import { writeText } from "@tauri-apps/plugin-clipboard-manager";
import CodeEditor from "../../components/CodeEditor";
import DiffView from "../../components/DiffView";
import { type GitCommit, gitCommitDiff, gitFileLog, shortDate } from "../../lib/git";
import { fencedPrompt } from "../../lib/prompt";
import { trackActivity } from "../../lib/activity";
import { clearDraft, draftKey, readDraft, writeDraft } from "../../lib/autosave";
import {
  InspectorButton,
  InspectorPanel,
  InspectorPortal,
  NavEmpty,
  NavigatorPortal,
  inlineInspector,
  useInspector,
} from "../../lib/panels";

interface TreeEntry {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
}

interface FileInfo {
  path: string;
  size: number;
  modified: string | null;
  lines: number | null;
  binary: boolean;
}

interface OpenFile {
  path: string;
  text: string;
  saved: string;
  revision: number;
  error: string | null;
  /** Aus dem Entwurfs-Speicher wiederhergestellt (noch nicht in der Datei). */
  restored?: boolean;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} kB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function FolderIcon({ open }: { open: boolean }) {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M2 4.5A1.5 1.5 0 0 1 3.5 3h3l1.5 1.5h4.5A1.5 1.5 0 0 1 14 6v6.5a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 2 12.5z" />
      {open ? <path d="M2 7.5h12" /> : null}
    </svg>
  );
}

function FileIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M4 2h5l3 3v9H4z" />
      <path d="M9 2v3h3" />
    </svg>
  );
}

export default function FilesTab({
  project,
  refresh,
  visible = true,
}: {
  project: string;
  refresh?: number;
  /** Beim Sichtbarwerden offene Ordner neu lesen (neue Dateien von außen). */
  visible?: boolean;
}) {
  // Baum: Verzeichnis → Kinder; "" = Wurzel. Nur geladene Ordner sind offen.
  const [tree, setTree] = useState<Record<string, TreeEntry[]>>({});
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set([""]));
  const [treeError, setTreeError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [open, setOpen] = useState<OpenFile[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [info, setInfo] = useState<FileInfo | null>(null);
  const [cursorLine, setCursorLine] = useState(1);
  // I3: Git-Historie der aktiven Datei im Inspektor, gewählter Commit → Diff.
  const [history, setHistory] = useState<GitCommit[]>([]);
  const [historyCommit, setHistoryCommit] = useState<string | null>(null);
  const [historyDiff, setHistoryDiff] = useState("");
  const inspector = useInspector("files");

  useEffect(() => {
    setHistoryCommit(null);
    if (!active) {
      setHistory([]);
      return;
    }
    void gitFileLog(project, active, 100)
      .then(setHistory)
      .catch(() => setHistory([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project, active, refresh]);

  useEffect(() => {
    if (!active || !historyCommit) {
      setHistoryDiff("");
      return;
    }
    void gitCommitDiff(project, historyCommit, active)
      .then(setHistoryDiff)
      .catch((e) => setHistoryDiff(String(e)));
  }, [project, active, historyCommit]);
  const openRef = useRef(open);
  openRef.current = open;

  const loadDir = useCallback(
    async (dir: string) => {
      try {
        const entries = await invoke<TreeEntry[]>("project_tree", { project, dir });
        setTree((previous) => ({ ...previous, [dir]: entries }));
        setTreeError(null);
      } catch (e) {
        setTreeError(String(e));
      }
    },
    [project],
  );

  useEffect(() => {
    void loadDir("");
  }, [loadDir]);

  useEffect(() => {
    if (!visible) return;
    for (const dir of expanded) void loadDir(dir);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible]);

  // Aus anderen Tabs (Git-Inspektor „Im Editor öffnen"): Datei öffnen und
  // die Elternordner im Baum aufklappen.
  useEffect(() => {
    const handler = (event: Event) => {
      const path = (event as CustomEvent<string>).detail;
      if (!path) return;
      const parts = path.split("/");
      setExpanded((previous) => {
        const next = new Set(previous);
        for (let i = 1; i < parts.length; i += 1) {
          const dir = parts.slice(0, i).join("/");
          next.add(dir);
          void loadDir(dir);
        }
        return next;
      });
      void openFile(path);
    };
    window.addEventListener("speccify:open-file", handler);
    return () => window.removeEventListener("speccify:open-file", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadDir]);

  // Watcher: offene Ordner neu lesen, ungeänderte offene Dateien nachladen.
  useEffect(() => {
    if (!refresh) return;
    for (const dir of expanded) void loadDir(dir);
    for (const file of openRef.current) {
      if (file.text !== file.saved) continue;
      void invoke<string>("project_read_file", { project, file: file.path })
        .then((text) => {
          if (text === file.saved) return;
          setOpen((previous) =>
            previous.map((entry) =>
              entry.path === file.path && entry.text === entry.saved
                ? { ...entry, text, saved: text, revision: entry.revision + 1 }
                : entry,
            ),
          );
        })
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh]);

  const current = open.find((file) => file.path === active) ?? null;

  useEffect(() => {
    if (!active) {
      setInfo(null);
      return;
    }
    void invoke<FileInfo>("project_file_info", { project, file: active })
      .then(setInfo)
      .catch(() => setInfo(null));
  }, [project, active, current?.saved]);

  const toggleDir = (dir: string) => {
    setExpanded((previous) => {
      const next = new Set(previous);
      if (next.has(dir)) next.delete(dir);
      else {
        next.add(dir);
        if (!tree[dir]) void loadDir(dir);
      }
      return next;
    });
  };

  const openFile = async (path: string) => {
    inspector.reveal();
    if (openRef.current.some((file) => file.path === path)) {
      setActive(path);
      return;
    }
    try {
      const text = await invoke<string>("project_read_file", { project, file: path });
      // Entwurf aus einer unterbrochenen Sitzung (Neustart vor ⌘S) hat Vorrang.
      const draft = readDraft(draftKey(project, path));
      const restored = draft !== null && draft !== text;
      setOpen((previous) => [
        ...previous,
        { path, text: restored ? draft : text, saved: text, revision: 0, error: null, restored },
      ]);
    } catch (e) {
      setOpen((previous) => [
        ...previous,
        { path, text: "", saved: "", revision: 0, error: String(e) },
      ]);
    }
    setActive(path);
  };

  const closeFile = (path: string) => {
    const file = openRef.current.find((entry) => entry.path === path);
    if (file && file.text !== file.saved && !window.confirm(`${path}: ungespeicherte Änderungen verwerfen?`)) {
      return;
    }
    clearDraft(draftKey(project, path));
    setOpen((previous) => previous.filter((entry) => entry.path !== path));
    if (active === path) {
      const rest = openRef.current.filter((entry) => entry.path !== path);
      setActive(rest.length > 0 ? rest[rest.length - 1].path : null);
    }
  };

  const save = async (path: string) => {
    const file = openRef.current.find((entry) => entry.path === path);
    if (!file || file.text === file.saved) return;
    const content = file.text;
    try {
      await trackActivity(
        "write",
        "Datei speichern",
        () => invoke("project_write_file", { project, file: path, content }),
        path,
      );
      clearDraft(draftKey(project, path));
      setOpen((previous) =>
        previous.map((entry) =>
          entry.path === path ? { ...entry, saved: content, error: null, restored: false } : entry,
        ),
      );
      window.dispatchEvent(new CustomEvent("speccify:worktree-changed", { detail: path }));
    } catch (e) {
      setOpen((previous) =>
        previous.map((entry) => (entry.path === path ? { ...entry, error: String(e) } : entry)),
      );
    }
  };

  const setText = (path: string, text: string) => {
    // Jeder Tastenanschlag als Entwurf — ein Neustart vor ⌘S kostet nichts mehr.
    const file = openRef.current.find((entry) => entry.path === path);
    if (file && text === file.saved) clearDraft(draftKey(project, path));
    else writeDraft(draftKey(project, path), text);
    setOpen((previous) =>
      previous.map((entry) => (entry.path === path ? { ...entry, text, restored: false } : entry)),
    );
  };

  const matches = (name: string) => filter === "" || name.toLowerCase().includes(filter.toLowerCase());

  const renderDir = (dir: string, depth: number): ReactNode => {
    const entries = tree[dir];
    if (!entries) return null;
    return entries.map((entry) => {
      const isOpen = expanded.has(entry.path);
      if (entry.is_dir) {
        return (
          <div key={entry.path}>
            <button
              onClick={() => toggleDir(entry.path)}
              className="flex w-full items-center gap-1.5 rounded px-2 py-0.5 text-left text-[13px] text-slate-700 hover:bg-slate-100"
              style={{ paddingLeft: 8 + depth * 14 }}
            >
              <span className="text-slate-400"><FolderIcon open={isOpen} /></span>
              <span className="truncate">{entry.name}</span>
            </button>
            {isOpen ? renderDir(entry.path, depth + 1) : null}
          </div>
        );
      }
      if (!matches(entry.name)) return null;
      const opened = open.find((file) => file.path === entry.path);
      return (
        <button
          key={entry.path}
          onClick={() => void openFile(entry.path)}
          className={`flex w-full items-center gap-1.5 rounded px-2 py-0.5 text-left text-[13px] ${
            active === entry.path ? "bg-slate-800 text-white" : "text-slate-700 hover:bg-slate-100"
          }`}
          style={{ paddingLeft: 8 + depth * 14 }}
          title={entry.path}
        >
          <span className={active === entry.path ? "text-slate-300" : "text-slate-400"}><FileIcon /></span>
          <span className="truncate">{entry.name}</span>
          {opened && opened.text !== opened.saved ? <span className="ml-auto text-amber-500">●</span> : null}
        </button>
      );
    });
  };

  const navigator = (
    <NavigatorPortal tab="files">
      <input
        value={filter}
        onChange={(event) => setFilter(event.target.value)}
        placeholder="Dateiname filtern…"
        spellCheck={false}
        className="mb-2 w-full rounded border border-slate-300 bg-white px-2 py-1 text-xs"
      />
      {treeError ? <p className="mb-2 text-xs text-red-600">{treeError}</p> : null}
      {tree[""] && tree[""].length === 0 ? (
        <NavEmpty title="Leeres Projekt">
          Hier liegen noch keine Dateien — oder alle sind per <code>.gitignore</code>
          ausgeblendet.
        </NavEmpty>
      ) : (
        <div className="space-y-0">{renderDir("", 0)}</div>
      )}
    </NavigatorPortal>
  );

  const dirty = current ? current.text !== current.saved : false;
  const details = current ? (
    <InspectorPortal tab="files" fallback={inlineInspector}>
      <InspectorPanel
        title={current.path.split("/").pop() ?? current.path}
        subtitle={current.path}
        meta={[
          { label: "Größe", value: info ? formatSize(info.size) : "—" },
          { label: "Zeilen", value: info?.lines ?? "—" },
          {
            label: "Geändert",
            value: info?.modified ? info.modified.replace("T", " ").slice(0, 16) : "—",
          },
          {
            label: "Zustand",
            value: current.restored
              ? "Entwurf wiederhergestellt — noch nicht gespeichert (⌘S)"
              : dirty
                ? "ungespeichert (Entwurf gesichert)"
                : "gespeichert",
          },
          { label: "Cursor", value: `Zeile ${cursorLine}` },
        ]}
        actions={
          <>
            <InspectorButton tone="primary" disabled={!dirty} onClick={() => void save(current.path)}>
              Speichern
            </InspectorButton>
            <InspectorButton
              disabled={!dirty}
              onClick={() => {
                clearDraft(draftKey(project, current.path));
                setOpen((previous) =>
                  previous.map((entry) =>
                    entry.path === current.path
                      ? { ...entry, text: entry.saved, revision: entry.revision + 1, restored: false }
                      : entry,
                  ),
                );
              }}
            >
              Verwerfen
            </InspectorButton>
            <InspectorButton
              title="Pfad:Zeile + Inhalt als Markdown-Prompt in die Zwischenablage"
              onClick={() => void writeText(fencedPrompt(`${current.path}:${cursorLine}`, current.text))}
            >
              Als Prompt kopieren
            </InspectorButton>
            <InspectorButton onClick={() => void writeText(`${current.path}:${cursorLine}`)}>
              Pfad kopieren
            </InspectorButton>
          </>
        }
        tabs={[
          {
            id: "file",
            label: "Datei",
            content: (
              <div className="space-y-1">
                {current.error ? <p className="text-xs text-red-600">{current.error}</p> : null}
                {info?.binary ? <p className="text-xs text-amber-700">Binärdatei — nicht editierbar.</p> : null}
                {!current.error && !info?.binary ? (
                  <p className="text-xs text-slate-400">
                    ⌘S speichert; Entwürfe werden automatisch gesichert. Git-Zustand und Diff
                    im Git-Tab.
                  </p>
                ) : null}
              </div>
            ),
          },
          {
            id: "history",
            label: `Historie${history.length ? ` (${history.length})` : ""}`,
            content: (
              <div>
                {history.length === 0 ? (
                  <p className="text-xs text-slate-400">
                    Keine Commits für diese Datei — neu, unversioniert oder kein Repository.
                  </p>
                ) : (
                  <ul className="space-y-0.5 text-xs">
                    {history.map((entry) => {
                      const activeCommit = historyCommit === entry.hash;
                      return (
                        <li key={entry.hash}>
                          <button
                            onClick={() =>
                              setHistoryCommit((previous) => (previous === entry.hash ? null : entry.hash))
                            }
                            className={`flex w-full gap-2 rounded px-1.5 py-1 text-left ${
                              activeCommit ? "bg-slate-800 text-white" : "hover:bg-slate-100"
                            }`}
                            title={`${entry.short} · ${entry.author} · ${shortDate(entry.date)}`}
                          >
                            <span className={`shrink-0 font-mono ${activeCommit ? "text-slate-300" : "text-slate-400"}`}>
                              {entry.short}
                            </span>
                            <span className="min-w-0 flex-1 truncate">{entry.subject}</span>
                            <span className={`shrink-0 ${activeCommit ? "text-slate-300" : "text-slate-400"}`}>
                              {entry.date.slice(0, 10)}
                            </span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
                {historyCommit ? (
                  <div className="mt-2 rounded border border-slate-200 bg-white">
                    <div className="flex items-center justify-between border-b border-slate-200 px-2 py-1 font-mono text-[10px] text-slate-500">
                      <span>Commit {historyCommit.slice(0, 7)} · diese Datei</span>
                      <button
                        onClick={() => void writeText(fencedPrompt(`git show ${historyCommit.slice(0, 7)} -- ${current.path}`, historyDiff))}
                        className="text-slate-400 hover:text-slate-800"
                        title="Diff als Markdown-Prompt in die Zwischenablage"
                      >
                        als Prompt
                      </button>
                    </div>
                    <DiffView text={historyDiff} compact />
                  </div>
                ) : null}
              </div>
            ),
          },
        ]}
      />
    </InspectorPortal>
  ) : null;

  const tabs = useMemo(() => open, [open]);

  return (
    <div className="flex h-full min-h-0 gap-4">
      {navigator}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white">
        {tabs.length > 0 ? (
          <div className="flex shrink-0 items-stretch overflow-x-auto border-b border-slate-200 bg-slate-50 text-xs">
            {tabs.map((file) => (
              <div
                key={file.path}
                className={`flex items-center gap-1.5 border-r border-slate-200 ${
                  active === file.path ? "bg-white text-slate-900" : "text-slate-500 hover:bg-slate-100"
                }`}
              >
                <button onClick={() => setActive(file.path)} className="py-1.5 pl-3" title={file.path}>
                  {file.path.split("/").pop()}
                  {file.text !== file.saved ? <span className="ml-1 text-amber-500">●</span> : null}
                </button>
                <button
                  onClick={() => closeFile(file.path)}
                  className="px-2 py-1.5 text-slate-400 hover:text-slate-800"
                  title="Schließen"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        ) : null}
        {details}
        {current ? (
          current.error ? (
            <p className="p-5 text-sm text-red-600">{current.error}</p>
          ) : (
            <div className="min-h-0 flex-1">
              <CodeEditor
                key={current.path}
                path={current.path}
                value={current.text}
                revision={current.revision}
                onChange={(text) => setText(current.path, text)}
                onSave={() => void save(current.path)}
                onCursor={setCursorLine}
              />
            </div>
          )
        ) : (
          <p className="p-5 text-sm text-slate-400">
            Datei links im Baum öffnen. Cmd/Ctrl-S speichert, der Inspektor zeigt Größe, Zeilen
            und Zustand.
          </p>
        )}
      </div>
    </div>
  );
}
