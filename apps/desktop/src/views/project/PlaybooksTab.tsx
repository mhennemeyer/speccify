// Playbooks-Tab (Plan projektfenster.md, D30): stehende Anleitungen aus
// .agent/playbooks/ — im Gegensatz zu Plänen ohne Lifecycle: sie werden
// nicht abgearbeitet, sondern immer wieder benutzt (Release, Deploy,
// Onboarding). Liste links, rechts Ansicht oder Editor (description +
// Body); „Als Prompt kopieren" gibt den Ablauf dem Agenten ins Terminal.

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import Markdown, { stripFrontmatter } from "../../components/Markdown";
import { copyPrompt } from "../../lib/prompt";
import { LoadingBoundary, useAsync } from "../../components/ui";
import { assemblePlan, splitPlan } from "./PlansTab";

interface PlaybookEntry {
  file: string;
  title: string;
  description: string | null;
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
  onCancel,
}: {
  project: string;
  file: string;
  original: string;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const parts = splitPlan(original);
  const [description, setDescription] = useState(
    frontmatterValue(parts.frontmatter, "description"),
  );
  const [body, setBody] = useState(parts.body);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const content = assemblePlan(original, { description }, body);
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
        <label className="text-xs font-medium text-slate-500">description</label>
        <input
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Wofür ist dieser Ablauf da?"
          spellCheck={false}
          className="rounded border border-slate-300 px-2 py-1 font-mono text-sm"
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

function NewPlaybook({ project, onCreated }: { project: string; onCreated: (file: string) => void }) {
  const [name, setName] = useState("");
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = async () => {
    setError(null);
    try {
      const file = await invoke<string>("project_playbook_create", { project, name });
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
}: {
  project: string;
  refresh?: number;
}) {
  const list = useAsync(
    () => invoke<PlaybookEntry[]>("project_playbooks", { project }),
    `playbooks:${project}`,
  );
  const [selected, setSelected] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const body = useAsync(
    () =>
      selected
        ? invoke<string>("project_read_file", { project, file: selected })
        : Promise.resolve(""),
    `playbook-body:${project}:${selected ?? ""}`,
  );

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
        <div className="w-72 shrink-0 space-y-1 overflow-y-auto pr-1">
          {playbooks.map((entry) => (
            <button
              key={entry.file}
              onClick={() => {
                setSelected(entry.file);
                setEditing(false);
              }}
              className={`block w-full rounded px-2 py-1.5 text-left text-sm ${
                selected === entry.file
                  ? "bg-slate-800 text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
              title={entry.description ?? undefined}
            >
              <span className="block truncate">{entry.title}</span>
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
            onCreated={(file) => {
              setSelected(file);
              setEditing(true);
              void list.reload();
            }}
          />
          {playbooks.length === 0 ? (
            <p className="px-2 pt-2 text-xs text-slate-400">
              Stehende Abläufe unter <code>.agent/playbooks/</code> — anders als
              Pläne werden sie nicht abgearbeitet, sondern immer wieder benutzt.
            </p>
          ) : null}
        </div>
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white p-5">
          {selectedPlaybook ? (
            editing ? (
              <PlaybookEditor
                project={project}
                file={selectedPlaybook.file}
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
                <div className="mb-3 flex items-start justify-between gap-3">
                  {selectedPlaybook.description ? (
                    <p className="rounded bg-slate-100 px-3 py-2 text-xs text-slate-600">
                      {selectedPlaybook.description}
                    </p>
                  ) : (
                    <span />
                  )}
                  <div className="flex shrink-0 gap-2">
                    <button
                      onClick={() => void copyPrompt(selectedPlaybook.file, body.data ?? "")}
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
                    <button
                      onClick={() => void remove(selectedPlaybook.file)}
                      className="rounded border border-red-200 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50"
                    >
                      Löschen
                    </button>
                  </div>
                </div>
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
