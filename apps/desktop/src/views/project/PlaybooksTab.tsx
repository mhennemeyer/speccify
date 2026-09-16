// Playbooks-Tab (Plan projektfenster.md, D30): stehende Anleitungen aus
// .agent/playbooks/ — im Gegensatz zu Plänen ohne Lifecycle: sie werden
// nicht abgearbeitet, sondern immer wieder benutzt (Release, Deploy,
// Onboarding). Liste links, rechts Ansicht oder Editor (description +
// Body); „Als Prompt kopieren" gibt den Ablauf dem Agenten ins Terminal.

import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import Markdown, { stripFrontmatter } from "../../components/Markdown";
import { HandoverButton } from "../../components/HandoverSheet";
import { playbookStatus, playbookNotice, PLAYBOOK_STATUS_LABELS, type PlaybookStatus } from "../../lib/playbooks";
import {
  InspectorButton,
  InspectorPanel,
  InspectorPortal,
  NavEmpty,
  NavigatorPortal,
  inlineInspector,
  useInspector,
} from "../../lib/panels";
import { trackActivity } from "../../lib/activity";
import { autosaveLabel, draftKey, readDraft, useAutosave } from "../../lib/autosave";
import { LoadingBoundary, useAsync } from "../../components/ui";
import {
  assembleFrontmatter as assemblePlan,
  splitFrontmatter as splitPlan,
} from "../../lib/frontmatter";

interface PlaybookEntry {
  file: string;
  title: string;
  description: string | null;
  status?: PlaybookStatus;
}

function usePlaybookBody(project: string, file: string | null) {
  const generation = useRef(0);
  const [snapshot, setSnapshot] = useState<{ file: string | null; data: string | null; loading: boolean; error: string | null }>({ file: null, data: null, loading: false, error: null });
  const reload = useCallback(async () => {
    const request = ++generation.current;
    setSnapshot(old => ({ file, data: old.file === file ? old.data : null, loading: !!file, error: null }));
    try {
      const data = file ? await invoke<string>("project_read_file", { project, file }) : null;
      if (generation.current === request) setSnapshot({ file, data, loading: false, error: null });
    } catch (error) {
      if (generation.current === request) setSnapshot({ file, data: null, loading: false, error: String(error) });
    }
  }, [project, file]);
  useEffect(() => { void reload(); return () => { generation.current++; }; }, [reload]);
  return { ...snapshot, data: snapshot.file === file ? snapshot.data : null, loading: snapshot.loading || snapshot.file !== file, reload };
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

function PlaybookEditor({
  project,
  file,
  original,
  onSaved,
}: {
  project: string;
  file: string;
  original: string;
  onSaved: () => void;
}) {
  const key = draftKey(project, file);
  // Einmalig beim Öffnen (siehe PlanEditor) — sonst rutscht der Editor.
  const [initial] = useState(() => {
    const draft = readDraft(key);
    const restored = draft !== null && draft !== original;
    return { restored, original, parts: splitPlan(restored ? draft : original) };
  });
  const { restored, parts } = initial;
  const [description, setDescription] = useState(
    frontmatterValue(parts.frontmatter, "description"),
  );
  const [body, setBody] = useState(parts.body);
  const content = assemblePlan(initial.original, { description }, body);
  const expected = useRef(initial.original);
  const queue = useRef<Promise<void>>(Promise.resolve());
  const autosave = useAutosave({
    key,
    content,
    original: initial.original,
    save: (text) => {
      const saving = queue.current.then(async () => {
        if (text === expected.current) return;
        await trackActivity("write", "Playbook speichern", () => invoke("project_write_file", {
          project, file, content: text, expectedContent: expected.current,
        }), file);
        expected.current = text;
      });
      queue.current = saving.catch(() => {});
      return saving;
    },
  });

  const finish = async () => {
    await autosave.flush();
    if (expected.current === content) onSaved();
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <p className="text-xs text-slate-500">Playbook-Status: {PLAYBOOK_STATUS_LABELS[playbookStatus(initial.original)]} · Speichern ändert den Status nicht.</p>
      {restored ? (
        <p className="rounded bg-amber-50 px-3 py-1.5 text-xs text-amber-800">
          Ungespeicherte Bearbeitung wiederhergestellt — sie wird gleich in die Datei geschrieben.
        </p>
      ) : null}
      <div className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2">
        <label className="text-xs font-medium text-slate-500">description</label>
        <input
          aria-label="Playbook-Beschreibung"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Wofür ist dieser Ablauf da?"
          spellCheck={false}
          className="rounded border border-slate-300 px-2 py-1 font-mono text-sm"
        />
      </div>
      <textarea
        aria-label="Playbook-Inhalt"
        value={body}
        onChange={(event) => setBody(event.target.value)}
        spellCheck={false}
        className="min-h-0 flex-1 resize-none rounded border border-slate-300 p-3 font-mono text-xs leading-5"
      />
      {autosave.error ? <p className="text-xs text-red-600">{autosave.error}</p> : null}
      <div className="flex items-center justify-between gap-2">
        <span
          className={`text-xs ${autosave.status === "error" ? "text-red-600" : "text-slate-500"}`}
        >
          {autosaveLabel(autosave.status)}
        </span>
        <div className="flex gap-2">
        <button
          onClick={() => void autosave.flush()}
          disabled={autosave.status === "saved" || autosave.status === "saving"}
          className="rounded px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-40"
        >
          Jetzt speichern
        </button>
        <button
          onClick={() => void finish()}
          className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700"
        >
          Fertig
        </button>
        </div>
      </div>
    </div>
  );
}

function NewPlaybook({ project, onCreated, request = 0 }: { project: string; onCreated: (file: string) => void; request?: number }) {
  const [name, setName] = useState("");
  const [open, setOpen] = useState(false);
  useEffect(() => { if (request) setOpen(true); }, [request]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<"active" | "draft">("active");

  const create = async () => {
    setError(null);
    try {
      const file = await invoke<string>("project_playbook_create", { project, name, status });
      setName("");
      setOpen(false);
      onCreated(file);
    } catch (e) {
      setError(String(e));
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full rounded border border-dashed border-slate-300 px-2 py-1.5 text-left text-sm text-slate-500 hover:border-slate-400 hover:text-slate-700"
      >
        + Playbook
      </button>
    );
  }
  return (
    <div className="space-y-1">
      <label className="block text-xs">Playbook-Status
        <select aria-label="Neues Playbook: Status" value={status} onChange={event => setStatus(event.target.value as "active" | "draft")} className="ml-2 rounded border border-slate-300 bg-white p-1">
          <option value="active">Aktiv</option><option value="draft">Draft</option>
        </select>
      </label>
      <input
        autoFocus
        value={name}
        onChange={(event) => setName(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && name.trim() !== "") void create();
          if (event.key === "Escape") setOpen(false);
        }}
        placeholder="Name, z. B. Release"
        spellCheck={false}
        className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
      />
      {error ? <p className="text-xs text-red-600">{error}</p> : null}
    </div>
  );
}

export default function PlaybooksTab({
  project,
  refresh,
  workspace = false,
  selection,
}: {
  project: string;
  refresh?: number;
  workspace?: boolean;
  selection?: import("../../lib/workspaceKnowledge").KnowledgeSelection;
}) {
  const list = useAsync(
    () => invoke<PlaybookEntry[]>("project_playbooks", { project }),
    `playbooks:${project}`,
  );
  const [selected, setSelected] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  useEffect(() => { if (selection && !selection.manage && selection.file !== selected) { setSelected(selection.file); setEditing(false); } }, [selection?.request]);
  const [filter, setFilter] = useState("all");
  const [statusError, setStatusError] = useState<string | null>(null);
  const inspector = useInspector("playbooks");
  const body = usePlaybookBody(project, selected);

  useEffect(() => {
    // Live-Reload — aber nie mitten ins Editieren hinein.
    if (refresh && !editing) {
      void list.reload();
      void body.reload();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh]);

  const playbooks = list.data ?? [];
  const selectedPlaybook = playbooks.find((entry) => entry.file === selected) ?? null;
  const status = body.data == null ? selectedPlaybook?.status ?? "active" : playbookStatus(body.data);
  const changeStatus = async (next: "active" | "draft") => {
    if (!selectedPlaybook || body.data == null) return;
    setStatusError(null);
    try {
      const content = assemblePlan(body.data, { status: next }, splitPlan(body.data).body);
      await invoke("project_write_file", { project, file: selectedPlaybook.file, content, expectedContent: body.data });
      await body.reload(); await list.reload();
    } catch (error) { setStatusError(String(error)); }
  };

  const remove = async (file: string) => {
    if (!window.confirm("Playbook wirklich löschen?")) return;
    await invoke("project_playbook_delete", { project, file });
    setSelected(null);
    setEditing(false);
    void list.reload();
  };

  return (
    <LoadingBoundary loading={list.loading} error={list.error} label="Playbooks lesen…">
      <div className="flex h-full min-h-0 gap-4">
        <NavigatorPortal tab="playbooks">
        <div className="space-y-1">
          {!workspace && <label className="block text-xs text-slate-500">Status
            <select aria-label="Playbooks nach Status filtern" value={filter} onChange={event => setFilter(event.target.value)} className="ml-2 rounded border border-slate-300 bg-white p-1">
              <option value="all">Alle</option><option value="active">Aktiv</option><option value="draft">Draft</option><option value="invalid">Status prüfen</option>
            </select>
          </label>}
          {(workspace ? [] : playbooks).filter(entry => filter === "all" || (entry.status ?? "active") === filter).map((entry) => (
            <button
              key={entry.file}
              onClick={() => {
                setSelected(entry.file);
                setEditing(false);
                inspector.reveal();
              }}
              onDoubleClick={() => {
                setSelected(entry.file);
                setEditing(true);
              }}
              className={`block w-full rounded px-2 py-1.5 text-left text-sm ${
                selected === entry.file
                  ? "bg-slate-800 text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
              title={entry.description ?? undefined}
            >
              <span className="block truncate">{entry.title}</span>
              <span className="ml-2 text-[10px]" data-playbook-status={entry.status ?? "active"}>{PLAYBOOK_STATUS_LABELS[entry.status ?? "active"]}</span>
              {entry.description ? (
                <span
                  className={`block truncate text-[11px] ${
                    selected === entry.file ? "text-slate-300" : "text-slate-400"
                  }`}
                >
                  {entry.description}
                </span>
              ) : null}
            </button>
          ))}
          <NewPlaybook
            project={project}
            request={selection?.manage ? selection.request : 0}
            onCreated={(file) => {
              setSelected(file);
              setEditing(true);
              void list.reload();
            }}
          />
          {playbooks.length === 0 ? (
            <div className="pt-2">
              <NavEmpty title="Noch keine Playbooks">
                Stehende Abläufe unter <code>.agent/playbooks/</code> — Release, Deploy,
                Onboarding. Anders als Pläne werden sie nicht abgearbeitet, sondern
                immer wieder benutzt. Mit „+ Playbook" anlegen, dann im Editor
                beschreiben oder den Agenten den Ablauf aufschreiben lassen.
              </NavEmpty>
            </div>
          ) : null}
        </div>
        </NavigatorPortal>
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white p-5">
          {selectedPlaybook ? (
            editing ? (
              body.data === null ? <p>{body.error ?? "Playbook lesen…"}</p> :
              <PlaybookEditor
                key={selectedPlaybook.file}
                project={project}
                file={selectedPlaybook.file}
                original={body.data}
                onSaved={() => {
                  setEditing(false);
                  void body.reload();
                  void list.reload();
                }}
              />
            ) : (
              <div
                className="min-h-0 flex-1 overflow-y-auto"
                onDoubleClick={() => setEditing(true)}
                title="Doppelklick zum Bearbeiten"
              >
                {status !== "active" && <p role="status" className="mb-3 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">{playbookNotice(status)}</p>}
                {statusError && <p role="alert" className="text-sm text-red-600">{statusError}</p>}
                <InspectorPortal tab="playbooks" fallback={inlineInspector}>
                  <InspectorPanel
                    title={selectedPlaybook.title}
                    subtitle={selectedPlaybook.file}
                    meta={[
                      { label: "Beschreibung", value: selectedPlaybook.description ?? "—" },
                      { label: "Art", value: "Stehende Anleitung — kein Lifecycle" },
                      { label: "Status", value: PLAYBOOK_STATUS_LABELS[status] },
                    ]}
                    actions={
                      <>
                        <HandoverButton project={project} item={{ type: "playbook", path: selectedPlaybook.file, title: selectedPlaybook.title }} known={body.data} />
                        {status !== "active" && <InspectorButton disabled={body.loading || body.data == null} onClick={() => void changeStatus("active")}>Aktivieren</InspectorButton>}
                        {status !== "draft" && <InspectorButton disabled={body.loading || body.data == null} onClick={() => void changeStatus("draft")}>Als Draft markieren</InspectorButton>}
                        <InspectorButton
                          disabled={body.loading || body.data === null}
                          onClick={() => setEditing(true)}
                        >
                          Bearbeiten
                        </InspectorButton>
                        <InspectorButton
                          tone="danger"
                          onClick={() => void remove(selectedPlaybook.file)}
                        >
                          Löschen
                        </InspectorButton>
                      </>
                    }
                  />
                </InspectorPortal>
                <LoadingBoundary loading={body.loading} error={body.error} label="Playbook lesen…">
                  <Markdown text={stripFrontmatter(body.data ?? "")} />
                </LoadingBoundary>
              </div>
            )
          ) : (
            <p className="text-sm text-slate-400">Playbook links auswählen oder anlegen.</p>
          )}
        </div>
      </div>
    </LoadingBoundary>
  );
}
