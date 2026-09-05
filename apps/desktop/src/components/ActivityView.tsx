// Aktivitätsanzeige in der Toolbar-Mitte (W7d): was gerade läuft — mit
// Spinner —, sonst das zuletzt Beendete für ein paar Sekunden. Klick
// öffnet die Liste (laufend + zuletzt). Daten aus lib/activity.ts.

import { useEffect, useState } from "react";
import { runningActivities, useActivities, type Activity } from "../lib/activity";

function duration(entry: Activity, now: number): string {
  const ms = (entry.endedAt ?? now) - entry.startedAt;
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60_000) return `${Math.round(ms / 1000)} s`;
  return `${Math.floor(ms / 60_000)} min ${Math.round((ms % 60_000) / 1000)} s`;
}

function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700"
    />
  );
}

function outcomeMark(entry: Activity) {
  if (entry.outcome === "error") return <span className="text-red-600">✕</span>;
  if (entry.outcome === "cancelled") return <span className="text-slate-400">◌</span>;
  return <span className="text-emerald-600">✓</span>;
}

export default function ActivityView() {
  const activities = useActivities();
  const running = runningActivities(activities);
  const [open, setOpen] = useState(false);
  const [now, setNow] = useState(Date.now());

  // Laufzeiten tickend anzeigen, solange etwas läuft.
  useEffect(() => {
    if (running.length === 0) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [running.length]);

  const latest = activities[0];
  const recentlyFinished =
    latest && latest.endedAt !== undefined && now - latest.endedAt < 8000 ? latest : null;

  if (running.length === 0 && !recentlyFinished && !open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        title="Aktivität"
        className="rounded px-2 py-0.5 text-[11px] text-slate-400 hover:bg-slate-100 hover:text-slate-600"
      >
        {activities.length === 0 ? "Ruhe" : `${activities.length} Aktivitäten`}
      </button>
    );
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((previous) => !previous)}
        className="flex max-w-[360px] items-center gap-2 rounded bg-slate-100 px-2.5 py-0.5 text-[11px] text-slate-700 hover:bg-slate-200"
        title="Aktivität — Klick für die Liste"
      >
        {running.length > 0 ? (
          <>
            <Spinner />
            <span className="truncate">
              {running[0].label}
              {running.length > 1 ? ` +${running.length - 1}` : ""}
            </span>
            <span className="font-mono text-slate-500">{duration(running[0], now)}</span>
          </>
        ) : recentlyFinished ? (
          <>
            {outcomeMark(recentlyFinished)}
            <span className="truncate">{recentlyFinished.label}</span>
            <span className="font-mono text-slate-500">{duration(recentlyFinished, now)}</span>
          </>
        ) : (
          <span>Aktivität</span>
        )}
      </button>
      {open ? (
        <div className="fixed inset-0 z-40" onClick={() => setOpen(false)}>
          <div
            role="dialog"
            aria-label="Aktivität"
            onClick={(event) => event.stopPropagation()}
            className="absolute left-1/2 top-9 w-[440px] -translate-x-1/2 rounded-xl border border-slate-200 bg-white p-3 shadow-xl"
          >
            <h3 className="mb-2 text-xs font-semibold text-slate-500">Aktivität in diesem Fenster</h3>
            {activities.length === 0 ? (
              <p className="text-xs text-slate-400">Noch nichts passiert.</p>
            ) : (
              <ul className="max-h-72 space-y-1 overflow-y-auto text-xs">
                {activities.slice(0, 50).map((entry) => (
                  <li key={entry.id} className="flex items-start gap-2">
                    <span className="mt-0.5 w-3 shrink-0 text-center">
                      {entry.endedAt === undefined ? <Spinner /> : outcomeMark(entry)}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-slate-800">{entry.label}</span>
                      {entry.detail ? (
                        <span className="block truncate font-mono text-[10px] text-slate-400">
                          {entry.detail}
                        </span>
                      ) : null}
                    </span>
                    <span className="shrink-0 font-mono text-[10px] text-slate-400">
                      {duration(entry, now)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
