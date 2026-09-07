// Playbooks-Tab (Plan projektfenster.md, D30): stehende Anleitungen aus
// .agent/playbooks/ — im Gegensatz zu Plänen ohne Lifecycle: sie werden
// nicht abgearbeitet, sondern immer wieder benutzt (Release, Deploy,
// Onboarding). Liste links, rechts Ansicht oder Editor (description +
// Body); „Als Prompt kopieren" gibt den Ablauf dem Agenten ins Terminal.

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import Markdown, { stripFrontmatter } from "../../components/Markdown";
import { copyPrompt } from "../../lib/prompt";
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
}: {
  project: string;
  file: string;
  original: string;
  onSaved: () => void;
}) {
  const key = draftKey(project, file);
  const draft = readDraft(key);
  const restored = draft !== null && draft !== original;
  const parts = splitPlan(restored ? draft : original);
  const [description, setDescription] = useState(
    frontmatterValue(parts.frontmatter, "description"),
  );
  const [body, setBody] = useState(parts.body);
  const content = assemblePlan(original, { description }, body);
  const autosave = useAutosave({
    key,
    content,
    original,
    save: (text) =>
      trackActivity(
        "write",
        "Playbook speichern",
        () => invoke("project_write_file", { project, file, content: text }),
        file,
      ),
  });

  const finish = async () => {
    await autosave.flush();
    onSaved();
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      {restored ? (
        <p className="rounded bg-amber-50 px-3 py-1.5 text-xs text-amber-800">
          Ungespeicherter Entwurf wiederhergestellt — er wird gleich in die Datei geschrieben.
        </p>
      ) : null}
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
  const inspector = useInspector("playbooks");
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
        <NavigatorPortal tab="playbooks">
        <div className="space-y-1">
          {playbooks.map((entry) => (
            <button
              key={entry.file}
              onClick={() => {
                setSelected(entry.file);
                setEditing(false);
                inspector.reveal();
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
              <PlaybookEditor
                project={project}
                file={selectedPlaybook.file}
                original={body.data ?? ""}
                onSaved={() => {
                  setEditing(false);
                  void body.reload();
                  void list.reload();
                }}
              />
            ) : (
              <div className="min-h-0 flex-1 overflow-y-auto">
                <InspectorPortal tab="playbooks" fallback={inlineInspector}>
                  <InspectorPanel
                    title={selectedPlaybook.title}
                    subtitle={selectedPlaybook.file}
                    meta={[
                      { label: "Beschreibung", value: selectedPlaybook.description ?? "—" },
                      { label: "Art", value: "Stehende Anleitung — kein Lifecycle" },
                    ]}
                    actions={
                      <>
                        <InspectorButton
                          title="Pfad + Inhalt als Markdown-Prompt in die Zwischenablage"
                          disabled={body.data === null}
                          onClick={() => void copyPrompt(selectedPlaybook.file, body.data ?? "")}
                        >
                          Als Prompt kopieren
                        </InspectorButton>
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
