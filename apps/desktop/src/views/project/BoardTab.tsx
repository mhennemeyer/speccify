// Board-Tab (Plan projektfenster.md, D19): das iKanbanAI-Board aus
// `.agent/board/*.md` — drei Spalten, iKanban-Sortierung, Verschieben
// schreibt nur die station:-Zeile um. Beide Apps zeigen dasselbe Board.

import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import Markdown from "../../components/Markdown";
import { LoadingBoundary, useAsync } from "../../components/ui";

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
  body: string;
}

const STATIONS = ["Backlog", "Doing", "Done"] as const;
const STATION_LABELS: Record<string, string> = {
  Backlog: "Backlog",
  Doing: "In Progress",
  Done: "Done",
};

/** iKanban R5a: Backlog `order` (fehlend = ans Ende) → `created` → `id`. */
function backlogCompare(a: TicketEntry, b: TicketEntry) {
  const orderA = a.order ?? Number.MAX_SAFE_INTEGER;
  const orderB = b.order ?? Number.MAX_SAFE_INTEGER;
  if (orderA !== orderB) return orderA - orderB;
  const createdA = a.created ?? "";
  const createdB = b.created ?? "";
  if (createdA !== createdB) return createdA < createdB ? -1 : 1;
  return a.id < b.id ? -1 : 1;
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
    </span>
  );
}

function TicketCard({
  ticket,
  selected,
  onSelect,
  onMove,
  moving,
}: {
  ticket: TicketEntry;
  selected: boolean;
  onSelect: () => void;
  onMove: (station: string) => void;
  moving: boolean;
}) {
  const index = STATIONS.indexOf(ticket.station as (typeof STATIONS)[number]);
  const previous = index > 0 ? STATIONS[index - 1] : null;
  const next = index >= 0 && index < STATIONS.length - 1 ? STATIONS[index + 1] : null;
  return (
    <div
      className={`rounded-lg border p-2 ${
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
      <div className="mt-1.5 flex justify-between text-[11px]">
        {previous ? (
          <button
            onClick={() => onMove(previous)}
            disabled={moving}
            className="text-slate-500 hover:text-slate-800 disabled:opacity-40"
          >
            ← {STATION_LABELS[previous]}
          </button>
        ) : (
          <span />
        )}
        {next ? (
          <button
            onClick={() => onMove(next)}
            disabled={moving}
            className="text-slate-500 hover:text-slate-800 disabled:opacity-40"
          >
            {STATION_LABELS[next]} →
          </button>
        ) : (
          <span />
        )}
      </div>
    </div>
  );
}

export default function BoardTab({ project }: { project: string }) {
  const { data, loading, refreshing, error, reload } = useAsync(
    () => invoke<TicketEntry[]>("project_board", { project }),
    `board:${project}`,
  );
  const [selected, setSelected] = useState<string | null>(null);
  const [moving, setMoving] = useState(false);
  const [moveError, setMoveError] = useState<string | null>(null);

  const tickets = data ?? [];
  const selectedTicket = tickets.find((ticket) => ticket.file === selected) ?? null;

  const move = async (ticket: TicketEntry, station: string) => {
    setMoving(true);
    setMoveError(null);
    try {
      await invoke("project_board_move", { project, file: ticket.file, station });
      await reload();
    } catch (e) {
      setMoveError(String(e));
    } finally {
      setMoving(false);
    }
  };

  return (
    <LoadingBoundary loading={loading} error={error} label="Board lesen…">
      {tickets.length === 0 ? (
        <p className="text-sm text-slate-500">
          Kein Board unter <code>.agent/board/</code> — iKanbanAI (oder der Agent) legt
          Tickets dort als Markdown-Dateien an.
        </p>
      ) : (
        <div className="flex h-full min-h-0 flex-col">
          <div className="mb-2 flex items-center justify-between">
            {moveError ? (
              <p className="text-xs text-red-600">{moveError}</p>
            ) : (
              <span />
            )}
            <button
              onClick={() => void reload()}
              className="rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-100"
            >
              {refreshing ? "Lädt…" : "Aktualisieren"}
            </button>
          </div>
          <div className="flex min-h-0 flex-1 gap-3">
            {STATIONS.map((station) => {
              const inStation = tickets.filter((ticket) => ticket.station === station);
              inStation.sort(station === "Backlog" ? backlogCompare : createdCompare);
              return (
                <div
                  key={station}
                  className="flex min-h-0 flex-1 flex-col rounded-lg bg-slate-100 p-2"
                >
                  <h2 className="mb-2 px-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {STATION_LABELS[station]} ({inStation.length})
                  </h2>
                  <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
                    {inStation.map((ticket) => (
                      <TicketCard
                        key={ticket.file}
                        ticket={ticket}
                        selected={selected === ticket.file}
                        onSelect={() =>
                          setSelected(selected === ticket.file ? null : ticket.file)
                        }
                        onMove={(target) => void move(ticket, target)}
                        moving={moving}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
          {selectedTicket ? (
            <div className="mt-3 max-h-[40%] overflow-y-auto rounded-lg border border-slate-200 bg-white p-4">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-800">
                  {selectedTicket.title}{" "}
                  <span className="ml-1 font-mono text-xs font-normal text-slate-400">
                    {selectedTicket.id}
                  </span>
                </h3>
                <button
                  onClick={() => setSelected(null)}
                  className="text-xs text-slate-400 hover:text-slate-700"
                >
                  Schließen
                </button>
              </div>
              {selectedTicket.body.trim() ? (
                <Markdown text={selectedTicket.body} />
              ) : (
                <p className="text-xs text-slate-400">Kein Beschreibungstext.</p>
              )}
            </div>
          ) : null}
        </div>
      )}
    </LoadingBoundary>
  );
}
