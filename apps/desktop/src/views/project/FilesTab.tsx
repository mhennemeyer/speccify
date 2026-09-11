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
import FileTypeIcon from "../../components/FileTypeIcon";
import DiffView from "../../components/DiffView";
import {
  type BlameLine,
  type GitCommit,
  gitBlame,
  gitCommitDiff,
  gitFileLog,
  shortDate,
} from "../../lib/git";

interface SearchHit {
  path: string;
  line: number;
  column: number;
  text: string;
}
import { fencedPrompt } from "../../lib/prompt";
import { trackActivity } from "../../lib/activity";
import { useProjectActivity } from "../../lib/projectActivity";
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

function RenameForm({
  from,
  onSubmit,
  onCancel,
}: {
  from: string;
  onSubmit: (to: string) => void;
  onCancel: () => void;
}) {
  const [value, setValue] = useState(from);
  return (
    <div className="flex w-full gap-1">
      <input
        autoFocus
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") onSubmit(value);
          if (event.key === "Escape") onCancel();
        }}
        spellCheck={false}
        className="min-w-0 flex-1 rounded border border-slate-300 bg-white px-2 py-1 font-mono text-xs"
      />
      <button
        onClick={() => onSubmit(value)}
        className="rounded bg-slate-800 px-2 py-1 text-[11px] text-white hover:bg-slate-700"
      >
        Umbenennen
      </button>
      <button onClick={onCancel} className="rounded px-2 py-1 text-[11px] text-slate-500 hover:bg-slate-100">
        Abbrechen
      </button>
    </div>
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
  const projectActive = useProjectActivity();
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
  // I3: Zeile anspringen (Suche, Terminal-Link), Blame, Suche, Anlegen/Umbenennen/Löschen.
  const [reveal, setReveal] = useState<{ path: string; line: number; nonce: number } | null>(null);
  const [blameOn, setBlameOn] = useState(false);
  const [blame, setBlame] = useState<BlameLine[] | null>(null);
  const [mode, setMode] = useState<"tree" | "search">("tree");
  const [query, setQuery] = useState("");
  const [searchRegex, setSearchRegex] = useState(false);
  const [searchCase, setSearchCase] = useState(false);
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [creating, setCreating] = useState<{ isDir: boolean; path: string } | null>(null);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [deleteArmed, setDeleteArmed] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const inspector = useInspector("files");

  // Suche: 250 ms nach der letzten Eingabe, .gitignore gilt wie im Baum.
  useEffect(() => {
    if (mode !== "search") return;
    if (!query.trim()) {
      setHits([]);
      setSearchError(null);
      return;
    }
    const timer = setTimeout(() => {
      void invoke<SearchHit[]>("project_search", {
        project,
        query,
        regex: searchRegex,
        caseSensitive: searchCase,
        limit: 500,
      })
        .then((found) => {
          setHits(found);
          setSearchError(null);
        })
        .catch((e) => setSearchError(String(e)));
    }, 250);
    return () => clearTimeout(timer);
  }, [project, mode, query, searchRegex, searchCase, refresh]);

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

  // Zuletzt geöffnete Dateien je Projekt (I3): Tabs überleben den Neustart —
  // Entwürfe kommen ohnehin aus dem Draft-Speicher zurück.
  const recentKey = `speccify.files.open:${project}`;
  // Erst nach dem Wiederherstellen wird gemerkt — sonst überschriebe der
  // leere Anfangszustand die Liste, bevor sie gelesen ist.
  const restoredRef = useRef<"pending" | "running" | "done">("pending");
  useEffect(() => {
    if (restoredRef.current !== "pending") return;
    restoredRef.current = "running";
    let stored: { paths: string[]; active: string | null } | null = null;
    try {
      const raw = localStorage.getItem(recentKey);
      stored = raw ? (JSON.parse(raw) as { paths: string[]; active: string | null }) : null;
    } catch {
      stored = null;
    }
    if (!stored || stored.paths.length === 0) {
      restoredRef.current = "done";
      return;
    }
    void (async () => {
      for (const path of stored.paths.slice(0, 20)) await openFile(path);
      if (stored.active) setActive(stored.active);
      restoredRef.current = "done";
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project]);
  useEffect(() => {
    if (restoredRef.current !== "done") return;
    try {
      localStorage.setItem(
        recentKey,
        JSON.stringify({ paths: open.map((file) => file.path), active }),
      );
    } catch {
      // localStorage nicht verfügbar — dann eben nicht gemerkt.
    }
  }, [recentKey, open, active]);

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
      const raw = (event as CustomEvent<string>).detail;
      if (!projectActive.current) return;
      if (!raw) return;
      // `pfad:zeile` (Terminal-Link, Suche) → Datei öffnen und Zeile anspringen.
      const at = /^(.*?):(\d+)$/.exec(raw);
      const path = at ? at[1] : raw;
      const line = at ? Number(at[2]) : undefined;
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
      void openFile(path, line);
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

  const openFile = async (path: string, line?: number) => {
    inspector.reveal();
    if (line) setReveal({ path, line, nonce: Date.now() });
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

  // Blame der aktiven Datei — nachladen, wenn der gespeicherte Stand wechselt.
  useEffect(() => {
    if (!blameOn || !active) {
      setBlame(null);
      return;
    }
    void gitBlame(project, active)
      .then(setBlame)
      .catch(() => setBlame([]));
  }, [project, active, blameOn, current?.saved]);

  const reloadParent = (path: string) => {
    const dir = path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : "";
    void loadDir(dir);
    if (dir) setExpanded((previous) => new Set(previous).add(dir));
  };

  const createEntry = async () => {
    if (!creating || !creating.path.trim()) return;
    setFileError(null);
    try {
      const created = await invoke<string>("project_file_create", {
        project,
        path: creating.path.trim(),
        isDir: creating.isDir,
      });
      reloadParent(created);
      setCreating(null);
      if (!creating.isDir) void openFile(created);
      window.dispatchEvent(new CustomEvent("speccify:worktree-changed", { detail: created }));
    } catch (e) {
      setFileError(String(e));
    }
  };

  const renameEntry = async (from: string, to: string) => {
    if (!to.trim() || to.trim() === from) {
      setRenaming(null);
      return;
    }
    setFileError(null);
    try {
      const moved = await invoke<string>("project_file_rename", { project, from, to: to.trim() });
      setOpen((previous) =>
        previous.map((entry) => (entry.path === from ? { ...entry, path: moved } : entry)),
      );
      if (active === from) setActive(moved);
      reloadParent(from);
      reloadParent(moved);
      setRenaming(null);
      window.dispatchEvent(new CustomEvent("speccify:worktree-changed", { detail: moved }));
    } catch (e) {
      setFileError(String(e));
    }
  };

  const deleteEntry = async (path: string) => {
    setFileError(null);
    try {
      await invoke("project_file_delete", { project, path });
      clearDraft(draftKey(project, path));
      setOpen((previous) => previous.filter((entry) => entry.path !== path));
      if (active === path) {
        const rest = openRef.current.filter((entry) => entry.path !== path);
        setActive(rest.length > 0 ? rest[rest.length - 1].path : null);
      }
      setDeleteArmed(false);
      reloadParent(path);
      window.dispatchEvent(new CustomEvent("speccify:worktree-changed", { detail: path }));
    } catch (e) {
      setFileError(String(e));
    }
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
              <FileTypeIcon path={entry.path} folder open={isOpen} />
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
          aria-current={active === entry.path ? "true" : undefined}
          className="file-row flex w-full items-center gap-1.5 rounded px-2 py-0.5 text-left text-[13px] text-slate-700 hover:bg-slate-100"
          style={{ paddingLeft: 8 + depth * 14 }}
          title={entry.path}
        >
          <FileTypeIcon path={entry.path} />
          <span className="truncate">{entry.name}</span>
          {opened && opened.text !== opened.saved ? <span className="ml-auto text-amber-500">●</span> : null}
        </button>
      );
    });
  };

  const activeDir = active && active.includes("/") ? active.slice(0, active.lastIndexOf("/") + 1) : "";
  const grouped = new Map<string, SearchHit[]>();
  for (const hit of hits) {
    const list = grouped.get(hit.path) ?? [];
    list.push(hit);
    grouped.set(hit.path, list);
  }

  const navigator = (
    <NavigatorPortal tab="files">
      <div className="mb-2 flex items-center gap-1">
        <div className="flex gap-0.5 rounded bg-slate-100 p-0.5">
          {(
            [
              ["tree", "Dateien"],
              ["search", "Suchen"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              className={`rounded px-2 py-0.5 text-[11px] font-medium ${
                mode === id ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-800"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <span className="flex-1" />
        <button
          onClick={() => setCreating({ isDir: false, path: activeDir })}
          className="rounded px-1.5 py-0.5 text-[11px] text-slate-500 hover:bg-slate-100 hover:text-slate-800"
          title="Neue Datei (Pfad relativ zum Projekt)"
        >
          + Datei
        </button>
        <button
          onClick={() => setCreating({ isDir: true, path: activeDir })}
          className="rounded px-1.5 py-0.5 text-[11px] text-slate-500 hover:bg-slate-100 hover:text-slate-800"
          title="Neuer Ordner"
        >
          + Ordner
        </button>
      </div>
      {creating ? (
        <div className="mb-2 flex gap-1">
          <input
            autoFocus
            value={creating.path}
            onChange={(event) => setCreating({ ...creating, path: event.target.value })}
            onKeyDown={(event) => {
              if (event.key === "Enter") void createEntry();
              if (event.key === "Escape") setCreating(null);
            }}
            placeholder={creating.isDir ? "ordner/neu" : "ordner/datei.md"}
            spellCheck={false}
            className="min-w-0 flex-1 rounded border border-slate-300 bg-white px-2 py-1 font-mono text-xs"
          />
          <button
            onClick={() => void createEntry()}
            className="rounded bg-slate-800 px-2 py-1 text-[11px] text-white hover:bg-slate-700"
          >
            {creating.isDir ? "Ordner anlegen" : "Anlegen"}
          </button>
        </div>
      ) : null}
      {fileError ? <p className="mb-2 text-xs text-red-600">{fileError}</p> : null}
      {mode === "search" ? (
        <>
          <div className="mb-2 flex gap-1">
            <input
              autoFocus
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="In Dateien suchen…"
              spellCheck={false}
              className="min-w-0 flex-1 rounded border border-slate-300 bg-white px-2 py-1 text-xs"
            />
            <button
              onClick={() => setSearchCase((value) => !value)}
              className={`rounded border px-1.5 text-[11px] ${searchCase ? "border-slate-800 bg-slate-800 text-white" : "border-slate-300 text-slate-500"}`}
              title="Groß-/Kleinschreibung beachten"
            >
              Aa
            </button>
            <button
              onClick={() => setSearchRegex((value) => !value)}
              className={`rounded border px-1.5 font-mono text-[11px] ${searchRegex ? "border-slate-800 bg-slate-800 text-white" : "border-slate-300 text-slate-500"}`}
              title="Regulärer Ausdruck"
            >
              .*
            </button>
          </div>
          {searchError ? <p className="mb-2 text-xs text-red-600">{searchError}</p> : null}
          {query.trim() && hits.length === 0 && !searchError ? (
            <p className="text-xs text-slate-400">Keine Treffer.</p>
          ) : null}
          {hits.length > 0 ? (
            <p className="mb-1 text-[11px] text-slate-400">
              {hits.length}{hits.length >= 500 ? "+" : ""} Treffer in {grouped.size} Datei(en)
            </p>
          ) : null}
          {[...grouped.entries()].map(([path, list]) => (
            <details key={path} open className="mb-1">
              <summary className="cursor-pointer truncate px-1 text-xs font-medium text-slate-700" title={path}>
                {path} <span className="text-slate-400">({list.length})</span>
              </summary>
              <ul>
                {list.map((hit) => (
                  <li key={`${hit.path}:${hit.line}`}>
                    <button
                      onClick={() => {
                        setExpanded((previous) => {
                          const next = new Set(previous);
                          const parts = hit.path.split("/");
                          for (let i = 1; i < parts.length; i += 1) next.add(parts.slice(0, i).join("/"));
                          return next;
                        });
                        void openFile(hit.path, hit.line);
                      }}
                      className="flex w-full gap-2 rounded px-2 py-0.5 text-left font-mono text-[11px] text-slate-600 hover:bg-slate-100"
                      title={`${hit.path}:${hit.line}`}
                    >
                      <span className="w-8 shrink-0 text-right text-slate-400">{hit.line}</span>
                      <span className="min-w-0 flex-1 truncate">{hit.text.trim()}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </details>
          ))}
        </>
      ) : null}
      {mode === "tree" ? (
        <input
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder="Dateiname filtern…"
          spellCheck={false}
          className="mb-2 w-full rounded border border-slate-300 bg-white px-2 py-1 text-xs"
        />
      ) : null}
      {treeError ? <p className="mb-2 text-xs text-red-600">{treeError}</p> : null}
      {mode === "search" ? null : tree[""] && tree[""].length === 0 ? (
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
                  <label className="flex items-center gap-2 text-xs text-slate-600">
                    <input
                      type="checkbox"
                      checked={blameOn}
                      onChange={(event) => setBlameOn(event.target.checked)}
                    />
                    <span>
                      Blame am Rand{" "}
                      <span className="text-slate-400">(Commit und Autor je Zeile)</span>
                    </span>
                  </label>
                ) : null}
                {blameOn && blame && blame.length === 0 ? (
                  <p className="text-xs text-slate-400">Kein Blame — Datei nicht committet oder kein Repository.</p>
                ) : null}
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {renaming === current.path ? (
                    <RenameForm
                      from={current.path}
                      onSubmit={(to) => void renameEntry(current.path, to)}
                      onCancel={() => setRenaming(null)}
                    />
                  ) : (
                    <InspectorButton onClick={() => setRenaming(current.path)}>
                      Umbenennen…
                    </InspectorButton>
                  )}
                  {deleteArmed ? (
                    <>
                      <InspectorButton tone="danger" onClick={() => void deleteEntry(current.path)}>
                        In den Papierkorb
                      </InspectorButton>
                      <InspectorButton onClick={() => setDeleteArmed(false)}>Abbrechen</InspectorButton>
                    </>
                  ) : (
                    <InspectorButton
                      title="Datei in den Papierkorb legen (zweiter Klick bestätigt)"
                      onClick={() => setDeleteArmed(true)}
                    >
                      Löschen…
                    </InspectorButton>
                  )}
                </div>
                {fileError ? <p className="text-xs text-red-600">{fileError}</p> : null}
                <p className="text-xs text-slate-400">
                  ⌘S speichert; Entwürfe werden automatisch gesichert. Git-Zustand und Diff im
                  Git-Tab.
                </p>
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
                reveal={reveal && reveal.path === current.path ? reveal : null}
                blame={blameOn ? blame : null}
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
