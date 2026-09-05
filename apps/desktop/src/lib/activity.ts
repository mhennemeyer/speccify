// Aktivitäts-Store (W7d): was gerade im Fenster passiert — laufende
// Aktionen, Einrichten, Speichern — für die Aktivitätsanzeige in der
// Toolbar-Mitte. In-memory, pro Fenster, gedeckelt; kein Persistieren.
// Quellen melden `begin(...)` und `end(id, outcome)`; die Anzeige
// abonniert per `useActivities()`.

import { useSyncExternalStore } from "react";

export type ActivityKind = "action" | "setup" | "write" | "agent" | "other";
export type ActivityOutcome = "ok" | "error" | "cancelled";

export interface Activity {
  id: string;
  kind: ActivityKind;
  label: string;
  detail?: string;
  startedAt: number;
  endedAt?: number;
  outcome?: ActivityOutcome;
}

const CAP = 200;
let activities: Activity[] = [];
const listeners = new Set<() => void>();
let counter = 0;

function emit() {
  for (const listener of listeners) listener();
}

export function beginActivity(kind: ActivityKind, label: string, detail?: string): string {
  const id = `act-${Date.now()}-${++counter}`;
  activities = [{ id, kind, label, detail, startedAt: Date.now() }, ...activities].slice(0, CAP);
  emit();
  return id;
}

export function endActivity(id: string, outcome: ActivityOutcome = "ok", detail?: string): void {
  activities = activities.map((entry) =>
    entry.id === id
      ? { ...entry, endedAt: Date.now(), outcome, detail: detail ?? entry.detail }
      : entry,
  );
  emit();
}

/** Komfort: eine Promise als Aktivität begleiten. */
export async function trackActivity<T>(
  kind: ActivityKind,
  label: string,
  work: () => Promise<T>,
  detail?: string,
): Promise<T> {
  const id = beginActivity(kind, label, detail);
  try {
    const result = await work();
    endActivity(id, "ok");
    return result;
  } catch (error) {
    endActivity(id, "error", String(error));
    throw error;
  }
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useActivities(): Activity[] {
  return useSyncExternalStore(subscribe, () => activities, () => activities);
}

export function runningActivities(list: Activity[]): Activity[] {
  return list.filter((entry) => entry.endedAt === undefined);
}
