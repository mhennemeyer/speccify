// Board-Tab (Plan projektfenster.md, D19 + P5/W3): das Projekt-Board aus
// `.agent/board/*.md` — Speccifys Board-Format. Drei Spalten mit Drag&Drop,
// Ticket anlegen/editieren/löschen (byte-stabil, App-Aktionen loggen
// History), KPI-Kopfzeile aus den agent_run-Events, Done-Spalte nach Plan
// gruppiert. Live über den W2-Watcher — kein Aktualisieren-Knopf mehr.

import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import Markdown, { stripFrontmatter } from "../../components/Markdown";
import { LoadingBoundary, useAsync } from "../../components/ui";
import { copyPrompt } from "../../lib/prompt";
import { InspectorPortal, NavigatorPortal, NavRow, useInspector } from "../../lib/panels";
import type { PlanEntry } from "./PlansTab";

export interface TicketEntry {
  file: string;
  id: string;
  title: string;
  station: string;
  assignee: string | null;
  created: string | null;
  ready: boolean;
  needs_human: boolean;
  order: number | null;
  plan: string | null;
  open_question: string | null;
  body: string;
}

interface TicketQuestion {
  number: number;
  open: boolean;
  asked_at: string | null;
  text: string;
  answer: string | null;
  answered_at: string | null;
}

interface HistoryEvent {
  timestamp: string;
  ticket_id: string;
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
  ticket_id: string;
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
const STATION_LABELS: Record<string, string> = {
  Backlog: "Backlog",
  Doing: "In Progress",
  Done: "Done",
};

const HISTORY_ICONS: Record<string, string> = {
  ticket_created: "✚",
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

/** Backlog: `order` (fehlend = ans Ende) → `created` → `id`. */
function backlogCompare(a: TicketEntry, b: TicketEntry) {
  const orderA = a.order ?? Number.MAX_SAFE_INTEGER;
  const orderB = b.order ?? Number.MAX_SAFE_INTEGER;
  if (orderA !== orderB) return orderA - orderB;
  return createdCompare(a, b);
}

function createdCompare(a: TicketEntry, b: TicketEntry) {
  const createdA = a.created ?? "";
  const createdB = b.created ?? "";
  if (createdA !== createdB) return createdA < createdB ? -1 : 1;
  return a.id < b.id ? -1 : 1;
}

function TicketBadges({ ticket }: { ticket: TicketEntry }) {
  return (
    <span className="space-x-1">
      {ticket.ready ? (
        <span className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-800">
          ready
        </span>
      ) : null}
      {ticket.needs_human ? (
        <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-800">
          braucht BO
        </span>
      ) : null}
      {ticket.open_question ? (
        <span className="rounded-full bg-orange-100 px-1.5 py-0.5 text-[10px] font-bold text-orange-700">
          ?
        </span>
      ) : null}
    </span>
  );
}

function TicketCard({
  ticket,
  selected,
  onSelect,
}: {
  ticket: TicketEntry;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <div
      draggable
      onDragStart={(event) => {
        event.dataTransfer.setData("text/speccify-ticket", ticket.file);
        event.dataTransfer.effectAllowed = "move";
      }}
      className={`cursor-grab rounded-lg border p-2 active:cursor-grabbing ${
        selected ? "border-slate-800 bg-white shadow-sm" : "border-slate-200 bg-white"
      }`}
    >
      <button onClick={onSelect} className="block w-full text-left">
        <span className="text-sm font-medium text-slate-800">{ticket.title}</span>
        <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-500">
          <span className="font-mono">{ticket.id}</span>
          {ticket.assignee ? <span>· {ticket.assignee}</span> : null}
          <TicketBadges ticket={ticket} />
        </div>
      </button>
    </div>
  );
}

interface SheetState {
  file: string | null; // null = neues Ticket
  title: string;
  station: string;
  order: string;
  ready: boolean;
  needsHuman: boolean;
  plan: string;
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
    plan: "",
    body: "",
  };
}

function sheetFor(ticket: TicketEntry): SheetState {
  return {
    file: ticket.file,
    title: ticket.title,
    station: ticket.station,
    order: ticket.order === null ? "" : String(ticket.order),
    ready: ticket.ready,
    needsHuman: ticket.needs_human,
    plan: ticket.plan ?? "",
    body: ticket.body,
  };
}

function TicketSheet({
  sheet,
  onChange,
  onSave,
  onDelete,
  onClose,
  busy,
  error,
}: {
  sheet: SheetState;
  onChange: (next: SheetState) => void;
  onSave: () => void;
  onDelete: () => void;
  onClose: () => void;
  busy: boolean;
  error: string | null;
}) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-6">
      <div className="flex max-h-full w-[640px] flex-col gap-3 overflow-y-auto rounded-xl bg-white p-5 shadow-xl">
        <h3 className="text-sm font-semibold text-slate-800">
          {sheet.file ? "Ticket bearbeiten" : "Neues Ticket"}
        </h3>
        <input
          value={sheet.title}
          onChange={(event) => onChange({ ...sheet, title: event.target.value })}
          placeholder="Titel"
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
              className="w-16 rounded border border-slate-300 px-2 py-1 font-mono"
            />
          </label>
          {sheet.file === null ? (
            <label className="flex items-center gap-1.5 text-xs text-slate-600">
              plan
              <input
                value={sheet.plan}
                onChange={(event) => onChange({ ...sheet, plan: event.target.value })}
                spellCheck={false}
                className="w-40 rounded border border-slate-300 px-2 py-1 font-mono"
              />
            </label>
          ) : null}
          <label className="flex items-center gap-1.5 text-xs text-slate-600">
            <input
              type="checkbox"
              checked={sheet.ready}
              onChange={(event) => onChange({ ...sheet, ready: event.target.checked })}
            />
            ready
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
          rows={12}
          className="resize-none rounded border border-slate-300 p-3 font-mono text-xs leading-5"
        />
        {error ? <p className="text-xs text-red-600">{error}</p> : null}
        <div className="flex items-center justify-between">
          {sheet.file ? (
            <button
              onClick={onDelete}
              disabled={busy}
              className="rounded px-3 py-1.5 text-xs text-red-600 hover:bg-red-50"
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
  questions: TicketQuestion[];
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
            Answered ({answered.length})
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

function TicketDetail({
  ticket,
  history,
  questions,
  onAnswer,
  busy,
  onEdit,
  onClose,
  inInspector,
}: {
  ticket: TicketEntry;
  history: HistoryEvent[];
  questions: TicketQuestion[];
  onAnswer: (number: number, text: string) => void;
  busy: boolean;
  onEdit: () => void;
  onClose: () => void;
  /** Im Inspektor (W7) füllt das Detail die Seitenleiste; inline ist es
   *  ein Panel unter dem Board (Fallback ohne Seitenleiste). */
  inInspector: boolean;
}) {
  const shown = history.slice(0, 100);
  // W7d: im Inspektor zwei Tabs — Übersicht (Fragen + Text) und Historie —
  // statt einer langen Scroll-Seite.
  const [tab, setTab] = useState<"overview" | "history">("overview");
  const showOverview = !inInspector || tab === "overview";
  const showHistory = !inInspector || tab === "history";
  return (
    <div
      className={
        inInspector
          ? "min-h-0 flex-1 overflow-y-auto p-4"
          : "mt-3 max-h-[45%] overflow-y-auto rounded-lg border border-slate-200 bg-white p-4"
      }
    >
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-800">
          {ticket.title}{" "}
          <span className="ml-1 font-mono text-xs font-normal text-slate-400">{ticket.id}</span>
        </h3>
        <div className="flex gap-2">
          <button
            onClick={() => void copyPrompt(ticket.file, ticket.body)}
            className="rounded border border-slate-300 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-100"
            title="Pfad + Inhalt als Markdown-Prompt in die Zwischenablage"
          >
            Als Prompt kopieren
          </button>
          <button
            onClick={onEdit}
            className="rounded border border-slate-300 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-100"
          >
            Bearbeiten
          </button>
          <button onClick={onClose} className="text-xs text-slate-400 hover:text-slate-700">
            Schließen
          </button>
        </div>
      </div>
      {inInspector ? (
        <div role="tablist" className="mb-3 flex gap-1 border-b border-slate-200 text-xs">
          {(
            [
              ["overview", "Übersicht"],
              ["history", `Historie${history.length ? ` (${history.length})` : ""}`],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              role="tab"
              aria-selected={tab === id}
              onClick={() => setTab(id)}
              className={`-mb-px px-3 py-1.5 font-medium ${
                tab === id
                  ? "border-b-2 border-slate-800 text-slate-800"
                  : "text-slate-400 hover:text-slate-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      ) : null}
      {showOverview ? (
        <>
          <QuestionsSection questions={questions} onAnswer={onAnswer} busy={busy} />
          {stripQuestions(ticket.body) ? (
            <Markdown text={stripQuestions(ticket.body)} />
          ) : (
            <p className="text-xs text-slate-400">Kein Beschreibungstext.</p>
          )}
        </>
      ) : null}
      {showHistory && inInspector && shown.length === 0 ? (
        <p className="text-xs text-slate-400">Noch keine History.</p>
      ) : null}
      {showHistory && shown.length > 0 ? (
        <div className={inInspector ? "" : "mt-3 border-t border-slate-100 pt-2"}>
          <h4 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            History
          </h4>
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
        </div>
      ) : null}
    </div>
  );
}

function ActivePlanPanel({ project, planRefresh }: { project: string; planRefresh?: number }) {
  const plans = useAsync(
    () => invoke<PlanEntry[]>("project_plans", { project }),
    `plans:${project}`,
  );
  const active = (plans.data ?? []).find(
    (plan) => !plan.archived && plan.lifecycle === "active",
  );
  const body = useAsync(
    () =>
      active
        ? invoke<string>("project_read_file", { project, file: active.file })
        : Promise.resolve(""),
    `plan-body:${project}:${active?.file ?? ""}`,
  );
  useEffect(() => {
    if (planRefresh) {
      void plans.reload();
      void body.reload();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planRefresh]);
  if (!active) return null;
  return (
    <details className="mb-2 rounded-lg border border-slate-200 bg-white px-3 py-2" open>
      <summary className="cursor-pointer text-xs font-semibold text-slate-600">
        Aktiver Plan: {active.title}
        {active.escalation ? (
          <span className="ml-2 rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-medium text-red-700">
            Eskalation
          </span>
        ) : null}
      </summary>
      <div className="mt-2 max-h-48 overflow-y-auto border-t border-slate-100 pt-2">
        <Markdown text={stripFrontmatter(body.data ?? "")} />
      </div>
    </details>
  );
}

export default function BoardTab({
  project,
  refresh,
  planRefresh,
}: {
  project: string;
  refresh?: number;
  planRefresh?: number;
}) {
  const { data, loading, error, reload } = useAsync(
    () => invoke<TicketEntry[]>("project_board", { project }),
    `board:${project}`,
  );
  const kpis = useAsync(
    () => invoke<KpiSummary>("project_board_kpis", { project }),
    `board-kpis:${project}`,
  );
  const [selected, setSelectedState] = useState<string | null>(null);
  // W7: das Ticket-Detail wohnt im Inspektor; eine neue Auswahl holt den
  // Inspektor-Tab nach vorn (ohne die Seitenleiste ungefragt zu öffnen).
  const inspector = useInspector("board");
  const setSelected = (file: string | null) => {
    setSelectedState(file);
    if (file) inspector.reveal();
  };
  const [sheet, setSheet] = useState<SheetState | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showRuns, setShowRuns] = useState(false);
  // Bewusst nicht persistiert (iKanban-Entscheid): ein Blickfilter, kein Modus.
  const [needsMe, setNeedsMe] = useState(false);

  const allTickets = data ?? [];
  const needsAttention = (ticket: TicketEntry) =>
    ticket.open_question !== null || ticket.needs_human;
  // W7b: Plan-Filter im Navigator (iKanban: Listen in der Seitenleiste).
  const [planFilter, setPlanFilter] = useState<string | null>(null);
  const plansOnBoard = [...new Set(allTickets.map((ticket) => ticket.plan ?? ""))].sort();
  const tickets = allTickets.filter(
    (ticket) =>
      (!needsMe || needsAttention(ticket)) &&
      (planFilter === null || (ticket.plan ?? "") === planFilter),
  );
  const selectedTicket = allTickets.find((ticket) => ticket.file === selected) ?? null;
  const questions = useAsync(
    () =>
      selectedTicket
        ? invoke<TicketQuestion[]>("project_ticket_questions", {
            project,
            file: selectedTicket.file,
          })
        : Promise.resolve([] as TicketQuestion[]),
    `ticket-questions:${project}:${selectedTicket?.file ?? ""}`,
  );
  const history = useAsync(
    () =>
      selectedTicket
        ? invoke<HistoryEvent[]>("project_ticket_history", {
            project,
            ticketId: selectedTicket.id,
          })
        : Promise.resolve([] as HistoryEvent[]),
    `ticket-history:${project}:${selectedTicket?.id ?? ""}`,
  );

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
      return true;
    } catch (e) {
      setActionError(String(e));
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
        await invoke("project_ticket_create", {
          project,
          title: sheet.title,
          station: sheet.station,
          body: sheet.body,
          needsHuman: sheet.needsHuman,
          plan: sheet.plan.trim() === "" ? null : sheet.plan.trim(),
          order: sheet.order === "" ? null : Number(sheet.order),
        });
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
    if (!window.confirm("Ticket wirklich löschen?")) return;
    const file = sheet.file;
    const ok = await run(() => invoke("project_ticket_delete", { project, file }));
    if (ok) {
      setSheet(null);
      setSelected(null);
    }
  };

  const kpi = kpis.data;

  return (
    <LoadingBoundary loading={loading} error={error} label="Board lesen…">
      <div className="flex h-full min-h-0 flex-col">
        <NavigatorPortal tab="board" fallback={() => null}>
          <div className="space-y-0.5">
            <NavRow
              selected={planFilter === null}
              onClick={() => setPlanFilter(null)}
              trailing={<span className="font-mono text-[11px] opacity-70">{allTickets.length}</span>}
            >
              Alle Tickets
            </NavRow>
            {plansOnBoard.map((plan) => (
              <NavRow
                key={plan || "(ohne)"}
                selected={planFilter === plan}
                onClick={() => setPlanFilter(plan)}
                trailing={
                  <span className="font-mono text-[11px] opacity-70">
                    {allTickets.filter((ticket) => (ticket.plan ?? "") === plan).length}
                  </span>
                }
              >
                {plan || "Ohne Plan"}
              </NavRow>
            ))}
          </div>
        </NavigatorPortal>
        <ActivePlanPanel project={project} planRefresh={planRefresh} />
        <div className="mb-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {kpi && kpi.run_count > 0 ? (
              <button
                onClick={() => setShowRuns((previous) => !previous)}
                title="Agent-Läufe aus der Ticket-History"
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
            {actionError && !sheet ? (
              <p className="text-xs text-red-600">{actionError}</p>
            ) : null}
          </div>
          <button
            onClick={() => setSheet(emptySheet("Backlog"))}
            className="rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
          >
            + Ticket
          </button>
        </div>
        {showRuns && kpi ? (
          <div className="mb-2 max-h-40 overflow-y-auto rounded-lg border border-slate-200 bg-white p-3">
            <ul className="space-y-0.5 font-mono text-[11px] text-slate-600">
              {kpi.recent.map((entry, index) => (
                <li key={index} className="truncate" title={entry.summary}>
                  <span className="text-slate-400">{entry.timestamp.slice(0, 16)}</span>{" "}
                  <span className="font-semibold">{entry.ticket_id}</span> · ↑
                  {abbreviate(entry.tokens_in)} ↓{abbreviate(entry.tokens_out)} ·{" "}
                  {formatDuration(entry.duration_ms)} · {entry.summary}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <div className="flex min-h-0 flex-1 gap-3">
          {STATIONS.map((station) => {
            const inStation = tickets.filter((ticket) => ticket.station === station);
            inStation.sort(station === "Backlog" ? backlogCompare : createdCompare);
            return (
              <div
                key={station}
                onDragOver={(event) => {
                  if (event.dataTransfer.types.includes("text/speccify-ticket")) {
                    event.preventDefault();
                    event.dataTransfer.dropEffect = "move";
                  }
                }}
                onDrop={(event) => {
                  const file = event.dataTransfer.getData("text/speccify-ticket");
                  if (file) {
                    event.preventDefault();
                    const ticket = tickets.find((entry) => entry.file === file);
                    if (ticket && ticket.station !== station) move(file, station);
                  }
                }}
                className="flex min-h-0 flex-1 flex-col rounded-lg bg-slate-100 p-2"
              >
                <h2 className="mb-2 px-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {STATION_LABELS[station]} ({inStation.length})
                </h2>
                <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
                  {station === "Done"
                    ? groupDone(inStation).map(([plan, group]) => (
                        <details key={plan} className="rounded-lg bg-slate-200/60 p-1.5">
                          <summary className="cursor-pointer px-1 text-[11px] font-semibold text-slate-500">
                            {plan} ({group.length})
                          </summary>
                          <div className="mt-1.5 space-y-2">
                            {group.map((ticket) => (
                              <TicketCard
                                key={ticket.file}
                                ticket={ticket}
                                selected={selected === ticket.file}
                                onSelect={() =>
                                  setSelected(selected === ticket.file ? null : ticket.file)
                                }
                              />
                            ))}
                          </div>
                        </details>
                      ))
                    : inStation.map((ticket) => (
                        <TicketCard
                          key={ticket.file}
                          ticket={ticket}
                          selected={selected === ticket.file}
                          onSelect={() =>
                            setSelected(selected === ticket.file ? null : ticket.file)
                          }
                        />
                      ))}
                </div>
              </div>
            );
          })}
        </div>
        {selectedTicket ? (
          <InspectorPortal tab="board">
            <TicketDetail
              ticket={selectedTicket}
              history={history.data ?? []}
              questions={questions.data ?? []}
              onAnswer={(number, text) =>
                void run(() =>
                  invoke("project_ticket_answer", {
                    project,
                    file: selectedTicket.file,
                    number,
                    text,
                  }),
                )
              }
              busy={busy}
              onEdit={() => setSheet(sheetFor(selectedTicket))}
              onClose={() => setSelected(null)}
              inInspector={inspector.slot !== null}
            />
          </InspectorPortal>
        ) : null}
        {sheet ? (
          <TicketSheet
            sheet={sheet}
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

/** Done-Spalte nach `plan` gruppiert (fehlend = „Ohne Plan"), Gruppen sortiert. */
function groupDone(tickets: TicketEntry[]): Array<[string, TicketEntry[]]> {
  const groups = new Map<string, TicketEntry[]>();
  for (const ticket of tickets) {
    const key = ticket.plan ?? "Ohne Plan";
    const group = groups.get(key) ?? [];
    group.push(ticket);
    groups.set(key, group);
  }
  return [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));
}
