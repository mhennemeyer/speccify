// Specs-Board (Plan spec-workflow.md, S3; davor projektfenster.md P5/W3):
// eine Spec je Ordner `.agent/specs/<slug>/SPEC.md`, drei Spalten mit
// Drag&Drop, Anlegen/Editieren (byte-stabil, App-Aktionen
// loggen History), Tasks als Checkboxen direkt umschaltbar, KPI-Kopfzeile
// aus den agent_run-Events, Done-Spalte nach Ober-Spec gruppiert. Live
// über den W2-Watcher — kein Aktualisieren-Knopf.

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import Markdown from "../../components/Markdown";
import { LoadingBoundary, useAsync } from "../../components/ui";
import { copyPrompt } from "../../lib/prompt";
import {
  InspectorButton,
  InspectorPanel,
  InspectorPortal,
  NavEmpty,
  NavigatorPortal,
  useInspector,
} from "../../lib/panels";

export interface SpecEntry {
  file: string;
  id: string;
  title: string;
  station: string;
  assignee: string | null;
  /** Spec 029: `Name <email>` der Person, die die Spec übernommen hat. */
  owner: string | null;
  /** Spec 029: Code-Branch der Arbeit. */
  branch: string | null;
  created: string | null;
  ready: boolean;
  needs_human: boolean;
  order: number | null;
  parent: string | null;
  open_question: string | null;
  /** Spec 030: Adressat der offenen Frage (`an: <email>`). */
  open_question_to: string | null;
  tasks_done: number;
  tasks_total: number;
  tasks: Task[];
  archived: boolean;
  /** Laufende Nummer aus dem Ordnernamen (`012-slug`). */
  number: number | null;
  body: string;
}

interface SpecQuestion {
  number: number;
  open: boolean;
  asked_at: string | null;
  text: string;
  answer: string | null;
  answered_at: string | null;
}

interface HistoryEvent {
  timestamp: string;
  spec_id: string;
  event_type: string;
  actor: string;
  summary: string;
  tokens_in?: number;
  tokens_out?: number;
  tokens_cache_read?: number;
  tokens_cache_write?: number;
  duration_ms?: number;
}

interface RunEntry {
  spec_id: string;
  timestamp: string;
  summary: string;
  tokens_in: number;
  tokens_out: number;
  duration_ms: number;
}

interface KpiSummary {
  run_count: number;
  tokens_in: number;
  tokens_out: number;
  duration_ms: number;
  recent: RunEntry[];
}

const STATIONS = ["Backlog", "Doing", "Done"] as const;
const STATION_TONES: Record<string, string> = { Backlog: "slate", Doing: "blue", Done: "green" };
const STATION_LABELS: Record<string, string> = {
  Backlog: "Backlog",
  Doing: "Doing",
  Done: "Done",
};

const HISTORY_ICONS: Record<string, string> = {
  spec_created: "✚",
  ticket_created: "✚",
  spec_edited: "✎",
  ticket_edited: "✎",
  station_changed: "⇄",
  agent_run: "▶",
};

/** Die `## Questions`-Sektion erscheint strukturiert über dem Body —
 *  aus der Markdown-Anzeige herausfiltern (sonst doppelt). */
function stripQuestions(body: string): string {
  const lines = body.split("\n");
  const out: string[] = [];
  let inQuestions = false;
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.toLowerCase() === "## questions") {
      inQuestions = true;
      continue;
    }
    if (inQuestions && trimmed.startsWith("## ")) inQuestions = false;
    if (!inQuestions) out.push(line);
  }
  return out.join("\n").trim();
}

/** Spec 029: Anzeige von `Name <email>`. */
function ownerName(owner: string): string {
  return owner.replace(/\s*<[^>]*>\s*$/, "").trim() || owner;
}
function ownerEmail(owner: string): string {
  const match = owner.match(/<([^>]+)>\s*$/);
  return (match ? match[1] : owner).trim().toLowerCase();
}
function initials(owner: string): string {
  const parts = ownerName(owner).split(/\s+/).filter(Boolean);
  return parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "").join("") || "?";
}

export interface BranchObservation {
  file: string;
  spec_id: string;
  branch: string;
  local: boolean;
  remote: boolean;
  last_author: string | null;
  last_email: string | null;
  last_date: string | null;
  stale_days: number | null;
  current: boolean;
}
export interface BranchReport {
  current: string | null;
  me: { name: string; email: string } | null;
  fetched: boolean;
  specs: BranchObservation[];
}

/** Abweichungen zwischen erklärter Spec und beobachtetem Git — nur Text, keine Korrektur. */
function branchHints(spec: SpecEntry, report: BranchReport | null): string[] {
  if (!spec.branch || spec.station !== "Doing" || !report) return [];
  const seen = report.specs.find((entry) => entry.file === spec.file);
  const hints: string[] = [];
  if (report.current && report.current !== spec.branch) {
    hints.push(`Du stehst auf ${report.current}, die Spec gehört zu ${spec.branch}.`);
  }
  if (seen) {
    if (!seen.remote && !seen.local) hints.push(`Branch ${spec.branch} existiert weder lokal noch auf origin.`);
    else if (!seen.remote) hints.push(`Branch ${spec.branch} ist noch nicht auf origin.`);
    if (seen.last_email && report.me && seen.last_email.toLowerCase() !== report.me.email.toLowerCase()) {
      hints.push(`Zuletzt hat ${seen.last_author ?? seen.last_email} auf diesen Branch gepusht${seen.last_date ? ` (${seen.last_date.slice(0, 10)})` : ""}.`);
    }
    if (seen.stale_days !== null && seen.stale_days >= 3) hints.push(`Seit ${seen.stale_days} Tagen keine Bewegung auf ${spec.branch}.`);
  }
  return hints;
}

/** Spec 030: fremde Register-Commits je Spec seit dem letzten „gesehen“. */
interface SpecChanges {
  spec_id: string;
  file: string;
  commits: { hash: string; author: string; email: string; date: string; subject: string }[];
  latest: string;
}
interface ChangesReport {
  head: string | null;
  me: string | null;
  specs: SpecChanges[];
}
function seenKey(project: string) {
  return `speccify.register.seen:${project}`;
}
function loadSeen(project: string): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(seenKey(project)) ?? "{}") as Record<string, string>;
  } catch {
    return {};
  }
}

interface Task {
  index: number;
  text: string;
  done: boolean;
}

function abbreviate(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return String(value);
}

function formatDuration(ms: number): string {
  if (ms >= 60_000) return `${Math.round(ms / 60_000)}m`;
  if (ms >= 1_000) return `${Math.round(ms / 1_000)}s`;
  return `${ms}ms`;
}

/** Backlog: `order` (fehlend = Idee, ans Ende) → `created` → `id`. */
function backlogCompare(a: SpecEntry, b: SpecEntry) {
  const orderA = a.order ?? Number.MAX_SAFE_INTEGER;
  const orderB = b.order ?? Number.MAX_SAFE_INTEGER;
  if (orderA !== orderB) return orderA - orderB;
  return createdCompare(a, b);
}

function createdCompare(a: SpecEntry, b: SpecEntry) {
  const createdA = a.created ?? "";
  const createdB = b.created ?? "";
  if (createdA !== createdB) return createdA < createdB ? -1 : 1;
  return a.id < b.id ? -1 : 1;
}

function SpecBadges({ spec }: { spec: SpecEntry }) {
  return (
    <span className="inline-flex flex-wrap gap-1">
      {spec.ready ? (
        <span className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-800">
          bereit
        </span>
      ) : null}
      {spec.needs_human ? (
        <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-800">
          braucht BO
        </span>
      ) : null}
      {spec.open_question ? (
        <span className="rounded-full bg-orange-100 px-1.5 py-0.5 text-[10px] font-bold text-orange-700">
          ?
        </span>
      ) : null}
      {spec.station === "Backlog" && spec.order === null ? (
        <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
          Idee
        </span>
      ) : null}
    </span>
  );
}

function Progress({ spec, compact = false }: { spec: SpecEntry; compact?: boolean }) {
  if (spec.tasks_total === 0) return null;
  const percent = Math.round((spec.tasks_done / spec.tasks_total) * 100);
  return (
    <span className={`flex items-center gap-1.5 ${compact ? "text-[10px]" : "text-xs"} text-slate-500`}>
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-200">
        <span
          data-tone={percent === 100 ? "green" : "blue"}
          className="tone-fill block h-full"
          style={{ width: `${percent}%` }}
        />
      </span>
      <span className="font-mono">
        {spec.tasks_done}/{spec.tasks_total}
      </span>
    </span>
  );
}

function SpecCard({
  spec,
  selected,
  conflict = false,
  changes = null,
  forMe = false,
  onSeen,
  onSelect,
  onEdit,
}: {
  spec: SpecEntry;
  selected: boolean;
  /** Spec 028: im Register steht ein unentschiedener Konflikt. */
  conflict?: boolean;
  /** Spec 030: fremde Änderungen seit dem letzten Bestätigen. */
  changes?: SpecChanges | null;
  /** Spec 030: die offene Frage ist an mich adressiert. */
  forMe?: boolean;
  onSeen?: () => void;
  onSelect: () => void;
  /** Doppelklick öffnet den Editor (BO 2026-09-08). */
  onEdit: () => void;
}) {
  return (
    <div
      data-tone={STATION_TONES[spec.station] ?? "slate"}
      data-selected={selected}
      data-spec-card={spec.file}
      draggable={!spec.archived}
      onDragStart={(event) => {
        event.dataTransfer.setData("text/speccify-spec", spec.file);
        event.dataTransfer.effectAllowed = "move";
      }}
      className={`spec-card rounded-lg border p-2 ${spec.archived ? "opacity-70" : "cursor-grab active:cursor-grabbing"}`}
    >
      <button
        onClick={onSelect}
        onDoubleClick={onEdit}
        title="Doppelklick zum Bearbeiten"
        className="block w-full text-left"
      >
        <span className="text-sm font-medium text-slate-800">
          {spec.number !== null ? (
            <span className="mr-1.5 font-mono text-[11px] font-semibold text-slate-400">#{spec.number}</span>
          ) : null}
          {spec.title}
        </span>
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-slate-500">
          <span className="min-w-0 break-all font-mono" title={spec.id}>
            {spec.number !== null ? spec.id.replace(/^\d+-/, "") : spec.id}
          </span>
          {spec.parent ? <span>· {spec.parent}</span> : null}
          {spec.owner ? (
            <span className="rounded-full bg-sky-100 px-1.5 py-0.5 text-[10px] font-semibold text-sky-800" title={spec.owner} data-owner={ownerEmail(spec.owner)}>
              {initials(spec.owner)}
            </span>
          ) : null}
          {spec.branch ? <span className="font-mono text-[10px] text-slate-500" title={`Branch ${spec.branch}`}>⎇ {spec.branch}</span> : null}
          <Progress spec={spec} compact />
          <SpecBadges spec={spec} />
          {conflict ? (
            <span className="rounded bg-amber-100 px-1.5 py-0.5 font-semibold text-amber-800" title="Register-Konflikt: oben entscheiden">
              Konflikt
            </span>
          ) : null}
          {forMe ? (
            <span className="rounded bg-orange-100 px-1.5 py-0.5 font-semibold text-orange-800" title={`Frage ${spec.open_question ?? ""} ist an Dich adressiert`}>
              Frage an Dich
            </span>
          ) : null}
          {spec.archived ? <span>Altbestand · nur lesen</span> : null}
        </div>
      </button>
      {changes ? (
        <button
          type="button"
          onClick={(event) => { event.stopPropagation(); onSeen?.(); }}
          data-spec-new={spec.id}
          title={`Neu vom Team — Klick bestätigt:\n${changes.commits.map((commit) => `${commit.date.slice(0, 16).replace("T", " ")} ${commit.author}: ${commit.subject}`).join("\n")}`}
          className="mt-1 rounded bg-sky-600 px-1.5 py-0.5 text-[10px] font-semibold text-white hover:bg-sky-700"
        >
          neu · {changes.commits.length} von {[...new Set(changes.commits.map((commit) => commit.author))].join(", ")}
        </button>
      ) : null}
    </div>
  );
}

interface SheetState {
  file: string | null; // null = neue Spec
  title: string;
  station: string;
  order: string;
  ready: boolean;
  needsHuman: boolean;
  parent: string;
  body: string;
}

function emptySheet(station: string): SheetState {
  return {
    file: null,
    title: "",
    station,
    order: "",
    ready: false,
    needsHuman: false,
    parent: "",
    body: "",
  };
}

function sheetFor(spec: SpecEntry): SheetState {
  return {
    file: spec.file,
    title: spec.title,
    station: spec.station,
    order: spec.order === null ? "" : String(spec.order),
    ready: spec.ready,
    needsHuman: spec.needs_human,
    parent: spec.parent ?? "",
    body: spec.body,
  };
}

function SpecSheet({
  sheet,
  parents,
  onChange,
  onSave,
  onDelete,
  onClose,
  busy,
  error,
}: {
  sheet: SheetState;
  parents: string[];
  onChange: (next: SheetState) => void;
  onSave: () => void;
  onDelete: () => void;
  onClose: () => void;
  busy: boolean;
  error: string | null;
}) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-6">
      <div className="flex max-h-full w-[720px] flex-col gap-3 overflow-y-auto rounded-xl bg-white p-5 shadow-xl">
        <h3 className="text-sm font-semibold text-slate-800">
          {sheet.file ? "Spec bearbeiten" : "Neue Spec"}
        </h3>
        <input
          value={sheet.title}
          onChange={(event) => onChange({ ...sheet, title: event.target.value })}
          placeholder="Titel — was gebaut wird, in einem Satz"
          spellCheck={false}
          autoFocus
          className="rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <select
            value={sheet.station}
            onChange={(event) => onChange({ ...sheet, station: event.target.value })}
            className="rounded border border-slate-300 px-2 py-1.5"
          >
            {STATIONS.map((station) => (
              <option key={station} value={station}>
                {STATION_LABELS[station]}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-1.5 text-xs text-slate-600">
            order
            <input
              value={sheet.order}
              onChange={(event) =>
                onChange({ ...sheet, order: event.target.value.replace(/[^\d-]/g, "") })
              }
              placeholder="Idee"
              className="w-16 rounded border border-slate-300 px-2 py-1 font-mono"
            />
          </label>
          <label className="flex items-center gap-1.5 text-xs text-slate-600">
            parent
            <input
              value={sheet.parent}
              onChange={(event) => onChange({ ...sheet, parent: event.target.value })}
              list="speccify-spec-parents"
              placeholder="Ober-Spec (optional)"
              spellCheck={false}
              className="w-44 rounded border border-slate-300 px-2 py-1 font-mono"
            />
            <datalist id="speccify-spec-parents">
              {parents.map((parent) => (
                <option key={parent} value={parent} />
              ))}
            </datalist>
          </label>
          <label className="flex items-center gap-1.5 text-xs text-slate-600">
            <input
              type="checkbox"
              checked={sheet.ready}
              onChange={(event) => onChange({ ...sheet, ready: event.target.checked })}
            />
            bereit
          </label>
          <label className="flex items-center gap-1.5 text-xs text-slate-600">
            <input
              type="checkbox"
              checked={sheet.needsHuman}
              onChange={(event) => onChange({ ...sheet, needsHuman: event.target.checked })}
            />
            braucht BO
          </label>
        </div>
        <textarea
          value={sheet.body}
          onChange={(event) => onChange({ ...sheet, body: event.target.value })}
          spellCheck={false}
          rows={16}
          placeholder={
            sheet.file
              ? ""
              : "Leer lassen = Vorlage mit Why / What / Acceptance / Decisions / Tasks / Verification / Questions."
          }
          className="resize-none rounded border border-slate-300 p-3 font-mono text-xs leading-5"
        />
        {error ? <p className="text-xs text-red-600">{error}</p> : null}
        <div className="flex items-center justify-between">
          {sheet.file ? (
            <button
              onClick={onDelete}
              disabled={busy}
              className="rounded px-3 py-1.5 text-xs text-red-600 hover:bg-red-50"
              title="Löscht den ganzen Spec-Ordner samt History"
            >
              Löschen
            </button>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <button
              onClick={onClose}
              disabled={busy}
              className="rounded px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
            >
              Abbrechen
            </button>
            <button
              onClick={onSave}
              disabled={busy || sheet.title.trim() === ""}
              className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {busy ? "Speichert…" : "Speichern"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function QuestionsSection({
  questions,
  onAnswer,
  busy,
}: {
  questions: SpecQuestion[];
  onAnswer: (number: number, text: string) => void;
  busy: boolean;
}) {
  const [draft, setDraft] = useState("");
  const open = questions.filter((question) => question.open);
  const answered = questions.filter((question) => !question.open);
  if (questions.length === 0) return null;
  const current = open[0];
  return (
    <div className="mb-3 rounded-lg border border-orange-200 bg-orange-50 p-3">
      {current ? (
        <div>
          <p className="text-xs font-semibold text-orange-800">
            Q{current.number} · der Agent wartet auf eine Antwort
          </p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-orange-900">{current.text}</p>
          <div className="mt-2 flex gap-2">
            <textarea
              value={draft}
              disabled={busy}
              onChange={(event) => setDraft(event.target.value)}
              rows={2}
              placeholder="Antwort…"
              className="flex-1 rounded border border-orange-200 bg-white p-2 text-sm"
            />
            <button
              onClick={() => {
                onAnswer(current.number, draft);
                setDraft("");
              }}
              disabled={busy || draft.trim() === ""}
              className="self-end rounded bg-orange-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-orange-700 disabled:opacity-50"
            >
              Antworten
            </button>
          </div>
          {open.length > 1 ? (
            <p className="mt-1 text-[11px] text-orange-700">
              {open.length - 1} weitere offene Frage(n) danach.
            </p>
          ) : null}
        </div>
      ) : null}
      {answered.length > 0 ? (
        <details className="mt-2">
          <summary className="cursor-pointer text-[11px] font-semibold text-orange-700">
            Beantwortet ({answered.length})
          </summary>
          <ul className="mt-1 space-y-2 text-xs text-orange-900">
            {answered.map((question) => (
              <li key={question.number}>
                <p className="font-medium">
                  Q{question.number}: {question.text}
                </p>
                <p className="mt-0.5 whitespace-pre-wrap text-orange-800">
                  A: {question.answer}
                </p>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}

function SpecDetail({
  spec,
  history,
  questions,
  onAnswer,
  onToggleTask,
  busy,
  onEdit,
  onClose,
  inInspector,
  report = null,
  onTake,
  onRelease,
  onSwitchBranch,
}: {
  spec: SpecEntry;
  history: HistoryEvent[];
  questions: SpecQuestion[];
  onAnswer: (number: number, text: string) => void;
  onToggleTask: (index: number, done: boolean) => void;
  busy: boolean;
  onEdit: () => void;
  onClose: () => void;
  /** Im Inspektor (W7) füllt das Detail die Seitenleiste; inline ist es
   *  ein Panel unter dem Board (Fallback ohne Seitenleiste). */
  inInspector: boolean;
  /** Spec 029: Beobachtung der Branches und Übernehmen/Abgeben. */
  report?: BranchReport | null;
  onTake?: () => void;
  onRelease?: () => void;
  onSwitchBranch?: (branch: string, create: boolean) => void;
}) {
  const shown = history.slice(0, 100);
  const tasks = spec.tasks;
  const [switchArmed, setSwitchArmed] = useState(false);
  useEffect(() => setSwitchArmed(false), [spec.file]);
  const hints = branchHints(spec, report ?? null);
  const seen = report?.specs.find((entry) => entry.file === spec.file);
  const me = report?.me?.email.toLowerCase() ?? null;
  const ownedByMe = !!spec.owner && !!me && ownerEmail(spec.owner) === me;
  const canTake = !spec.archived && !!report?.me && !spec.owner && spec.station !== "Done";
  const canRelease = !spec.archived && ownedByMe && spec.station === "Doing";
  const canSwitch = !spec.archived && !!spec.branch && !!report && report.current !== spec.branch && !!onSwitchBranch;
  const ownership = (spec.owner || spec.branch || hints.length > 0 || canTake) ? (
    <div className="mb-3 rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-700" role="region" aria-label="Besitz und Branch">
      <p>
        <span className="font-semibold">Besitz:</span> {spec.owner ? `${ownerName(spec.owner)}${ownedByMe ? " (ich)" : ""}` : "niemand"}
        {spec.branch ? <> · <span className="font-semibold">Branch:</span> <code>{spec.branch}</code></> : null}
        {seen?.last_date ? <span className="text-slate-500"> · zuletzt {seen.last_date.slice(0, 10)} von {seen.last_author ?? "?"}</span> : null}
      </p>
      {hints.map((hint) => <p key={hint} className="mt-1 text-amber-700">⚠ {hint}</p>)}
      <div className="mt-2 flex flex-wrap gap-2">
        {canTake ? <InspectorButton onClick={() => onTake?.()} title="Station Doing, Besitzer = Deine Git-Identität, Branch-Vorschlag spec/<id>">Übernehmen</InspectorButton> : null}
        {canRelease ? <InspectorButton onClick={() => onRelease?.()} title="Zurück ins Backlog, Besitzer entfernen; Branch bleibt als Spur">Abgeben</InspectorButton> : null}
        {canSwitch && !switchArmed ? <InspectorButton onClick={() => setSwitchArmed(true)}>Zu {spec.branch} wechseln…</InspectorButton> : null}
        {canSwitch && switchArmed ? (
          <>
            <InspectorButton onClick={() => { setSwitchArmed(false); onSwitchBranch?.(spec.branch!, !(seen?.local ?? false)); }}>
              {seen?.local ? "Jetzt wechseln" : "Branch anlegen und wechseln"}
            </InspectorButton>
            <InspectorButton onClick={() => setSwitchArmed(false)}>Doch nicht</InspectorButton>
          </>
        ) : null}
      </div>
    </div>
  ) : null;
  const overview = (
    <>
      {spec.archived ? <p className="mb-2 text-xs text-slate-500">Altbestand · nur lesen. Datei und Historie bleiben am ursprünglichen Ort erhalten.</p> : null}
      {ownership}
      <QuestionsSection questions={questions} onAnswer={onAnswer} busy={busy || spec.archived} />
      {stripQuestions(spec.body) ? (
        <Markdown text={stripQuestions(spec.body)} />
      ) : (
        <p className="text-xs text-slate-400">Kein Text.</p>
      )}
    </>
  );
  const flags = [
    spec.ready ? "bereit" : null,
    spec.needs_human ? "braucht BO" : null,
    spec.open_question ? `Frage ${spec.open_question}` : null,
    spec.archived ? "Altbestand · nur lesen" : null,
  ].filter(Boolean);
  const panel = (
    <InspectorPanel
      title={spec.number !== null ? `#${spec.number} ${spec.title}` : spec.title}
      subtitle={`${spec.id} · ${spec.file}`}
      meta={[
        { label: "Station", value: spec.station },
        ...(spec.owner ? [{ label: "Besitz", value: ownerName(spec.owner) }] : []),
        ...(spec.branch ? [{ label: "Branch", value: spec.branch }] : []),
        { label: "Ober-Spec", value: spec.parent ?? "—" },
        {
          label: "Tasks",
          value: spec.tasks_total > 0 ? <Progress spec={spec} /> : "— keine Checkboxen",
        },
        ...(flags.length > 0 ? [{ label: "Flags", value: flags.join(", ") }] : []),
      ]}
      actions={
        <>
          <InspectorButton
            title="Pfad + Inhalt als Markdown-Prompt in die Zwischenablage"
            onClick={() => void copyPrompt(spec.file, spec.body)}
          >
            Als Prompt kopieren
          </InspectorButton>
          {!spec.archived ? <InspectorButton onClick={onEdit}>Bearbeiten</InspectorButton> : null}
          <InspectorButton onClick={onClose}>Schließen</InspectorButton>
        </>
      }
      tabs={[
        { id: "overview", label: "Übersicht", content: overview },
        {
          id: "tasks",
          label: `Tasks${spec.tasks_total ? ` ${spec.tasks_done}/${spec.tasks_total}` : ""}`,
          content:
            tasks.length === 0 ? (
              <p className="text-xs text-slate-400">
                Keine Tasks — Checkboxen unter <code>## Tasks</code> in der Spec anlegen.
              </p>
            ) : (
              <ul className="space-y-1">
                {tasks.map((task) => (
                  <li key={task.index}>
                    <label className="flex cursor-pointer items-start gap-2 text-sm text-slate-700">
                      <input
                        type="checkbox"
                        checked={task.done}
                        disabled={busy || spec.archived}
                        onChange={(event) => onToggleTask(task.index, event.target.checked)}
                        className="mt-0.5"
                      />
                      <span className={task.done ? "text-slate-400 line-through" : ""}>{task.text}</span>
                    </label>
                  </li>
                ))}
              </ul>
            ),
        },
        {
          id: "history",
          label: `Historie${history.length ? ` (${history.length})` : ""}`,
          content: (
            <div>
              {shown.length === 0 ? (
                <p className="text-xs text-slate-400">Noch keine History.</p>
              ) : (
                <ul className="space-y-0.5 font-mono text-[11px] text-slate-600">
                  {shown.map((event, index) => (
                    <li key={index} className="truncate" title={event.summary}>
                      <span className="mr-1">{HISTORY_ICONS[event.event_type] ?? "•"}</span>
                      <span className="text-slate-400">{event.timestamp.slice(0, 16)}</span>{" "}
                      <span className="text-slate-500">{event.actor}</span> · {event.summary}
                    </li>
                  ))}
                  {history.length > shown.length ? (
                    <li className="text-slate-400">… {history.length - shown.length} ältere Events</li>
                  ) : null}
                </ul>
              )}
            </div>
          ),
        },
      ]}
    />
  );
  if (inInspector) return panel;
  return (
    <div className="mt-3 flex max-h-[45%] flex-col overflow-hidden rounded-lg border border-slate-200 bg-white">
      {panel}
    </div>
  );
}

export default function BoardTab({ project, refresh, detailFile, detailOnly = false, onMutated, createRequest = 0, conflictIds = [] }: {
  project: string; refresh?: number; detailFile?: string; detailOnly?: boolean; onMutated?: () => void; createRequest?: number;
  /** Spec 028: Spec-IDs mit offenem Register-Konflikt. */
  conflictIds?: string[];
}) {
  const { data, loading, error, reload } = useAsync(
    () => invoke<SpecEntry[]>("project_board", { project }),
    `board:${project}`,
  );
  const kpis = useAsync(
    () => invoke<KpiSummary>("project_board_kpis", { project }),
    `board-kpis:${project}`,
  );
  const [selected, setSelectedState] = useState<string | null>(null);
  useEffect(() => { if (detailFile) setSelectedState(detailFile); }, [detailFile, data]);
  // W7: das Spec-Detail wohnt im Inspektor; eine neue Auswahl holt den
  // Inspektor-Tab nach vorn (ohne die Seitenleiste ungefragt zu öffnen).
  const inspector = useInspector("board");
  const setSelected = (file: string | null) => {
    setSelectedState(file);
    if (file) inspector.reveal();
  };
  const [sheet, setSheet] = useState<SheetState | null>(null);
  useEffect(() => { if (createRequest) setSheet(emptySheet("Backlog")); }, [createRequest]);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showRuns, setShowRuns] = useState(false);
  // Bewusst nicht persistiert: ein Blickfilter, kein Modus.
  const [needsMe, setNeedsMe] = useState(false);
  // Spec 029: „meine“ = Besitzer ist meine Git-Identität; „nach Person“ listet Doing gruppiert.
  const [mine, setMine] = useState(false);
  const [byPerson, setByPerson] = useState(false);
  const [parentFilter, setParentFilter] = useState("");
  const [search, setSearch] = useState("");
  const branches = useAsync(
    () => invoke<BranchReport>("project_spec_branches", { project }).catch(() => null),
    `spec-branches:${project}`,
  );
  const report = branches.data ?? null;
  const myEmail = report?.me?.email.toLowerCase() ?? null;
  // Spec 030: fremde Commits im Register seit „gesehen“; Merker je Spec lokal.
  const [seen, setSeen] = useState<Record<string, string>>(() => loadSeen(project));
  const changes = useAsync(
    () => invoke<ChangesReport>("project_register_changes", { project, since: null }).catch(() => null),
    `register-changes:${project}`,
  );
  useEffect(() => {
    const unlisten = listen<{ project: string }>("register-changed", (event) => {
      if (event.payload.project === project) { void changes.reload(); void branches.reload(); }
    });
    return () => { void unlisten.then((dispose) => dispose()); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project]);
  const changesFor = (spec: SpecEntry): SpecChanges | null => {
    const entry = changes.data?.specs.find((item) => item.spec_id === spec.id);
    return entry && seen[spec.id] !== entry.latest ? entry : null;
  };
  const markSeen = (spec: SpecEntry) => {
    const entry = changes.data?.specs.find((item) => item.spec_id === spec.id);
    if (!entry) return;
    const next = { ...seen, [spec.id]: entry.latest };
    setSeen(next);
    try { localStorage.setItem(seenKey(project), JSON.stringify(next)); } catch { /* ohne Merker bleibt die Markierung */ }
  };
  const forMe = (spec: SpecEntry) => !!spec.open_question_to && !!myEmail && spec.open_question_to.toLowerCase() === myEmail;
  const questionsForMe = (data ?? []).filter((spec) => !spec.archived && forMe(spec)).length;
  const isMine = (spec: SpecEntry) => !!spec.owner && !!myEmail && ownerEmail(spec.owner) === myEmail;

  const allSpecs = data ?? [];
  const live = allSpecs.filter((spec) => !spec.archived);
  const needsAttention = (spec: SpecEntry) => spec.open_question !== null || spec.needs_human || forMe(spec);
  const parents = [...new Set(allSpecs.map((spec) => spec.parent).filter((p): p is string => Boolean(p)))].sort();
  const query = search.trim().toLocaleLowerCase();
  const specs = allSpecs.filter(
    (spec) =>
      (!needsMe || needsAttention(spec)) &&
      (!mine || isMine(spec)) &&
      (!parentFilter || spec.parent === parentFilter || spec.id === parentFilter) &&
      (!query || `${spec.number ?? ""} ${spec.title} ${spec.id} ${spec.file}`.toLocaleLowerCase().includes(query)),
  );
  const listed = [...specs].sort((a, b) =>
    (a.number ?? Number.MAX_SAFE_INTEGER) - (b.number ?? Number.MAX_SAFE_INTEGER) ||
    a.id.localeCompare(b.id) || a.file.localeCompare(b.file));
  // Preserve unknown historical station names without making them drop targets.
  const stations = [...new Set<string>([...STATIONS, ...specs.map(spec => spec.station)])];
  const selectedSpec = allSpecs.find((spec) => spec.file === selected) ?? null;
  const questions = useAsync(
    () =>
      selectedSpec
        ? invoke<SpecQuestion[]>("project_ticket_questions", { project, file: selectedSpec.file })
        : Promise.resolve([] as SpecQuestion[]),
    `spec-questions:${project}:${selectedSpec?.file ?? ""}`,
  );
  const history = useAsync(
    () =>
      selectedSpec
        ? invoke<HistoryEvent[]>("project_ticket_history", { project, ticketId: selectedSpec.id, file: selectedSpec.file })
        : Promise.resolve([] as HistoryEvent[]),
    `spec-history:${project}:${selectedSpec?.file ?? ""}`,
  );

  useEffect(() => {
    // Hidden by a filter or removed by the watcher: never leave stale details.
    if (selected && !specs.some(spec => spec.file === selected)) setSelectedState(null);
  }, [selected, data, search, parentFilter, needsMe, mine]);

  useEffect(() => {
    if (!selected) return;
    const card = [...document.querySelectorAll<HTMLElement>("[data-spec-card]")]
      .find(element => element.dataset.specCard === selected);
    card?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [selected]);

  useEffect(() => {
    if (refresh) { void branches.reload(); void changes.reload(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh]);
  useEffect(() => {
    if (refresh) {
      void reload();
      void kpis.reload();
      void history.reload();
      void questions.reload();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh]);

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setActionError(null);
    try {
      await action();
      await Promise.all([reload(), kpis.reload(), history.reload(), questions.reload()]);
      onMutated?.();
      return true;
    } catch (e) {
      setActionError(String(e));
      if (String(e).includes("SPEC_CHANGED:")) await reload();
      return false;
    } finally {
      setBusy(false);
    }
  };

  const move = (file: string, station: string) =>
    void run(() => invoke("project_board_move", { project, file, station }));

  const saveSheet = async () => {
    if (!sheet) return;
    const ok = await run(async () => {
      if (sheet.file === null) {
        const file = await invoke<string>("project_ticket_create", {
          project,
          title: sheet.title,
          station: sheet.station,
          body: sheet.body,
          needsHuman: sheet.needsHuman,
          parent: sheet.parent.trim() === "" ? null : sheet.parent.trim(),
          order: sheet.order === "" ? null : Number(sheet.order),
        });
        setSelected(file);
      } else {
        await invoke("project_ticket_save", {
          project,
          file: sheet.file,
          patch: {
            title: sheet.title,
            station: sheet.station,
            ready: sheet.ready,
            needs_human: sheet.needsHuman,
            order: sheet.order === "" ? null : Number(sheet.order),
            body: sheet.body,
          },
        });
      }
    });
    if (ok) setSheet(null);
  };

  const deleteSheet = async () => {
    if (!sheet?.file) return;
    if (!window.confirm("Spec samt Ordner und History wirklich löschen?")) return;
    const file = sheet.file;
    const ok = await run(() => invoke("project_ticket_delete", { project, file }));
    if (ok) {
      setSheet(null);
      setSelected(null);
    }
  };

  // Laufende Nummern (BO 2026-09-10): neue Specs bekommen sie automatisch,
  // ältere per Knopf — Ordner werden umbenannt, parent-Verweise ziehen mit.
  const unnumbered = live.filter((spec) => spec.number === null).length;
  const numberSpecs = async () => {
    if (!window.confirm(`${unnumbered} Spec(s) nummerieren? Die Ordner werden umbenannt (slug → NNN-slug).`)) return;
    const ok = await run(() => invoke<string[]>("project_specs_number", { project }));
    if (ok) setSelected(null);
  };

  const kpi = kpis.data;

  return (
    <LoadingBoundary loading={loading} error={error} label="Specs lesen…">
      <div className="flex h-full min-h-0 flex-col">
        {!detailOnly && <>
        <NavigatorPortal tab="board" fallback={() => null}>
          {allSpecs.length === 0 ? (
            <NavEmpty
              title="Noch keine Spec"
              action={{ label: "+ Spec", onClick: () => setSheet(emptySheet("Backlog")) }}
            >
              Eine Spec ist eine Arbeitseinheit — ein Feature, ein Umbau, eine Untersuchung —
              als <code>.agent/specs/&lt;slug&gt;/SPEC.md</code> mit Tasks als Checkboxen.
              Backlog → Doing ist Deine Freigabe; der Agent arbeitet die Tasks ab
              (<em>/spec-next</em> im Terminal).
            </NavEmpty>
          ) : (
            <div className="space-y-1" aria-label="Spec-Liste">
              <p className="px-2 py-1 text-[11px] text-slate-500">Specs · {listed.length}/{allSpecs.length}</p>
              {listed.map(spec => (
                <button key={spec.file} data-spec-file={spec.file}
                  aria-current={selected === spec.file ? "true" : undefined}
                  title={`${spec.title}\n${spec.file}`}
                  onClick={() => setSelected(spec.file)}
                  className="file-row block w-full rounded px-2 py-2 text-left text-slate-700 hover:bg-slate-100">
                  <span className="block break-words text-sm font-medium">
                    {spec.number !== null ? <span className="mr-1 font-mono text-xs">#{spec.number}</span> : null}
                    {spec.title}
                  </span>
                  <span className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px]">
                    <span className="tone-ink font-medium" data-tone={STATION_TONES[spec.station] ?? "slate"}>{spec.station}</span>
                    <span>{spec.tasks_done}/{spec.tasks_total}</span>
                    <SpecBadges spec={spec} />
                    {spec.archived ? <span>Altbestand · nur lesen</span> : null}
                  </span>
                </button>
              ))}
              {listed.length === 0 ? <p className="p-2 text-xs text-slate-500">Keine passenden Specs. Filter zurücksetzen oder Suche ändern.</p> : null}
            </div>
          )}
        </NavigatorPortal>
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <input aria-label="Specs suchen" placeholder="Specs suchen · Titel, Nummer, Pfad…" value={search}
            onChange={event => setSearch(event.target.value)}
            className="min-w-40 flex-1 rounded border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-800" />
          <select aria-label="Ober-Spec filtern" value={parentFilter} onChange={event => setParentFilter(event.target.value)}
            className="max-w-48 rounded border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-700">
            <option value="">Alle Themen</option>
            {parents.map(parent => <option key={parent} value={parent}>{parent}</option>)}
          </select>
          {search || parentFilter || needsMe || mine ? <button className="text-xs text-slate-600 underline"
            onClick={() => { setSearch(""); setParentFilter(""); setNeedsMe(false); setMine(false); }}>Filter zurücksetzen</button> : null}
        </div>
        <div className="mb-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {kpi && kpi.run_count > 0 ? (
              <button
                onClick={() => setShowRuns((previous) => !previous)}
                title="Agent-Läufe aus der Spec-History"
                className="rounded-full bg-slate-100 px-2.5 py-1 font-mono text-[11px] text-slate-600 hover:bg-slate-200"
              >
                {kpi.run_count} {kpi.run_count === 1 ? "Lauf" : "Läufe"} · ↑
                {abbreviate(kpi.tokens_in)} ↓{abbreviate(kpi.tokens_out)} ·{" "}
                {formatDuration(kpi.duration_ms)}
              </button>
            ) : null}
            <button
              onClick={() => setNeedsMe((previous) => !previous)}
              className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${
                needsMe
                  ? "bg-orange-600 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              braucht mich
            </button>
            <button
              onClick={() => setMine((previous) => !previous)}
              disabled={!myEmail}
              title={myEmail ? `Specs, die ${myEmail} übernommen hat` : "Keine Git-Identität im Projekt"}
              className={`rounded-full px-2.5 py-1 text-[11px] font-medium disabled:opacity-40 ${
                mine ? "bg-sky-700 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              meine
            </button>
            {questionsForMe > 0 ? (
              <span className="rounded-full bg-orange-100 px-2.5 py-1 text-[11px] font-semibold text-orange-800" data-questions-for-me={questionsForMe}>
                {questionsForMe} {questionsForMe === 1 ? "Frage" : "Fragen"} an Dich
              </span>
            ) : null}
            <button
              onClick={() => setByPerson((previous) => !previous)}
              className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${
                byPerson ? "bg-slate-700 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              Doing nach Person
            </button>
            {unnumbered > 0 ? (
              <button
                onClick={() => void numberSpecs()}
                disabled={busy}
                title="Specs ohne laufende Nummer umbenennen: slug → NNN-slug"
                className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600 hover:bg-slate-200 disabled:opacity-40"
              >
                {unnumbered} ohne Nummer · nummerieren
              </button>
            ) : null}
            {actionError && !sheet ? (
              <p className="text-xs text-red-600">{actionError}</p>
            ) : null}
          </div>
          <button
            onClick={() => setSheet(emptySheet("Backlog"))}
            className="rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
          >
            + Spec
          </button>
        </div>
        {byPerson ? (
          <div className="mb-2 max-h-48 overflow-y-auto rounded-lg border border-slate-200 bg-white p-3" role="region" aria-label="Doing nach Person">
            {(() => {
              const doing = live.filter((spec) => spec.station === "Doing");
              const groups = new Map<string, SpecEntry[]>();
              for (const spec of doing) {
                const key = spec.owner ?? "";
                groups.set(key, [...(groups.get(key) ?? []), spec]);
              }
              if (doing.length === 0) return <p className="text-xs text-slate-400">Nichts in Doing.</p>;
              return [...groups.entries()].sort(([a], [b]) => (a === "" ? 1 : b === "" ? -1 : a.localeCompare(b))).map(([owner, group]) => (
                <div key={owner || "—"} className="mb-2 last:mb-0">
                  <p className="text-[11px] font-semibold text-slate-700">{owner ? ownerName(owner) : "ohne Besitzer"}{owner && myEmail && ownerEmail(owner) === myEmail ? " (ich)" : ""}</p>
                  <ul className="mt-0.5 space-y-0.5 text-[11px] text-slate-600">
                    {group.map((spec) => {
                      const seen = report?.specs.find((entry) => entry.file === spec.file);
                      return (
                        <li key={spec.file} className="flex flex-wrap gap-x-2">
                          <button className="underline-offset-2 hover:underline" onClick={() => setSelected(spec.file)}>
                            {spec.number !== null ? `#${spec.number} ` : ""}{spec.title}
                          </button>
                          {spec.branch ? <span className="font-mono text-slate-500">⎇ {spec.branch}</span> : <span className="text-slate-400">kein Branch</span>}
                          {seen?.last_date ? <span className="text-slate-400">· zuletzt {seen.last_date.slice(0, 10)} von {seen.last_author ?? "?"}</span> : null}
                          {branchHints(spec, report).length > 0 ? <span className="text-amber-700">· {branchHints(spec, report).length} Hinweis{branchHints(spec, report).length === 1 ? "" : "e"}</span> : null}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ));
            })()}
          </div>
        ) : null}
        {showRuns && kpi ? (
          <div className="mb-2 max-h-40 overflow-y-auto rounded-lg border border-slate-200 bg-white p-3">
            <ul className="space-y-0.5 font-mono text-[11px] text-slate-600">
              {kpi.recent.map((entry, index) => (
                <li key={index} className="truncate" title={entry.summary}>
                  <span className="text-slate-400">{entry.timestamp.slice(0, 16)}</span>{" "}
                  <span className="font-semibold">{entry.spec_id}</span> · ↑
                  {abbreviate(entry.tokens_in)} ↓{abbreviate(entry.tokens_out)} ·{" "}
                  {formatDuration(entry.duration_ms)} · {entry.summary}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <div className="flex min-h-0 flex-1 gap-3 overflow-x-auto">
          {stations.map((station) => {
            const inStation = specs.filter((spec) => spec.station === station);
            inStation.sort(station === "Backlog" ? backlogCompare : createdCompare);
            const card = (spec: SpecEntry) => (
              <SpecCard
                key={spec.file}
                spec={spec}
                conflict={conflictIds.includes(spec.id)}
                changes={changesFor(spec)}
                forMe={forMe(spec)}
                onSeen={() => markSeen(spec)}
                selected={selected === spec.file}
                onSelect={() => setSelected(selected === spec.file ? null : spec.file)}
                onEdit={() => {
                  if (spec.archived) return;
                  setSelected(spec.file);
                  setSheet(sheetFor(spec));
                }}
              />
            );
            return (
              <div
                key={station}
                data-tone={STATION_TONES[station] ?? "slate"}
                data-station={station}
                onDragOver={(event) => {
                  if (!STATIONS.some(known => known === station)) return;
                  if (event.dataTransfer.types.includes("text/speccify-spec")) {
                    event.preventDefault();
                    event.dataTransfer.dropEffect = "move";
                  }
                }}
                onDrop={(event) => {
                  if (!STATIONS.some(known => known === station)) return;
                  const file = event.dataTransfer.getData("text/speccify-spec");
                  if (file) {
                    event.preventDefault();
                    const spec = specs.find((entry) => entry.file === file);
                    if (spec && !spec.archived && spec.station !== station) move(file, station);
                  }
                }}
                className="spec-lane flex min-h-0 min-w-48 flex-1 flex-col rounded-lg p-2"
              >
                <h2 className="tone-ink mb-2 px-1 text-xs font-semibold uppercase tracking-wide">
                  {STATION_LABELS[station] ?? station} ({inStation.length})
                </h2>
                <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
                  {station === "Done" && !parentFilter
                    ? groupDone(inStation).map(([parent, group]) => (
                        <details key={parent} className="rounded-lg bg-slate-200/60 p-1.5" open>
                          <summary className="cursor-pointer px-1 text-[11px] font-semibold text-slate-500">
                            {parent} ({group.length})
                          </summary>
                          <div className="mt-1.5 space-y-2">{group.map(card)}</div>
                        </details>
                      ))
                    : inStation.map(card)}
                </div>
              </div>
            );
          })}
        </div>
        </>}
        {detailOnly && actionError && !sheet && <p role="alert" className="p-3 text-xs text-red-600">{actionError}</p>}
        {selectedSpec ? (
          <InspectorPortal tab="board">
            <SpecDetail
              spec={selectedSpec}
              history={history.data ?? []}
              questions={questions.data ?? []}
              onAnswer={(number, text) =>
                void run(() =>
                  invoke("project_ticket_answer", {
                    project,
                    file: selectedSpec.file,
                    number,
                    text,
                  }),
                )
              }
              onToggleTask={(index, done) =>
                void run(() =>
                  invoke("project_spec_toggle_task", { project, file: selectedSpec.file, index, done, expectedBody: selectedSpec.body }),
                )
              }
              busy={busy}
              onEdit={() => setSheet(sheetFor(selectedSpec))}
              onClose={() => setSelected(null)}
              inInspector={inspector.slot !== null}
              report={report}
              onTake={() => void run(async () => { await invoke("project_spec_take", { project, file: selectedSpec.file }); await branches.reload(); })}
              onRelease={() => void run(() => invoke("project_spec_release", { project, file: selectedSpec.file }))}
              onSwitchBranch={(branch, create) => void run(async () => { await invoke("project_git_switch", { project, branch, create }); await branches.reload(); })}
            />
          </InspectorPortal>
        ) : null}
        {sheet ? (
          <SpecSheet
            sheet={sheet}
            parents={parents}
            onChange={setSheet}
            onSave={() => void saveSheet()}
            onDelete={() => void deleteSheet()}
            onClose={() => setSheet(null)}
            busy={busy}
            error={actionError}
          />
        ) : null}
      </div>
    </LoadingBoundary>
  );
}

/** Done-Spalte nach Ober-Spec gruppiert (fehlend = „Ohne Thema"), sortiert. */
function groupDone(specs: SpecEntry[]): Array<[string, SpecEntry[]]> {
  const groups = new Map<string, SpecEntry[]>();
  for (const spec of specs) {
    const key = spec.parent ?? "Ohne Thema";
    const group = groups.get(key) ?? [];
    group.push(spec);
    groups.set(key, group);
  }
  return [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));
}
