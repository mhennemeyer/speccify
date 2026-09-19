import { invoke } from "@tauri-apps/api/core";
import { useCallback, useEffect, useState } from "react";

/**
 * Spec 061: the Done column shows only what reached Done within a window of
 * days; everything older is collapsed. The window is a board setting stored
 * in the board root's `.agent/settings.json` (`board.doneDays`), so it is per
 * project or workspace and shared through Git. `0` means "all".
 */
export const DONE_WINDOW_DEFAULT = 14;
export const DONE_WINDOW_OPTIONS: Array<{ days: number; label: string }> = [
  { days: 7, label: "Letzte 7 Tage" },
  { days: 14, label: "Letzte 14 Tage" },
  { days: 30, label: "Letzte 30 Tage" },
  { days: 90, label: "Letzte 90 Tage" },
  { days: 0, label: "Alle anzeigen" },
];

export function normaliseDoneWindow(value: unknown): number {
  const days = typeof value === "number" ? value : Number(value);
  return Number.isInteger(days) && days >= 0 ? days : DONE_WINDOW_DEFAULT;
}

/** Reads and writes the board's window; `root` is the project or workspace root. */
export function useDoneWindow(root: string | null | undefined): [number, (days: number) => void, string | null] {
  const [days, setDays] = useState(DONE_WINDOW_DEFAULT);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!root) return;
    let stale = false;
    setDays(DONE_WINDOW_DEFAULT);
    invoke<Record<string, unknown>>("project_settings_get", { project: root })
      .then(settings => {
        const board = settings.board as Record<string, unknown> | undefined;
        if (!stale && board && "doneDays" in board) setDays(normaliseDoneWindow(board.doneDays));
      })
      .catch(() => { /* ohne Settings gilt der Default */ });
    return () => { stale = true; };
  }, [root]);
  const update = useCallback((next: number) => {
    const previous = days;
    setDays(next);
    setError(null);
    if (!root) return;
    invoke("project_settings_set", { project: root, key: "board.doneDays", value: next === DONE_WINDOW_DEFAULT ? null : next })
      .catch(e => { setDays(previous); setError(String(e)); });
  }, [root, days]);
  return [days, update, error];
}

/** Splits Done specs into the recent window and the collapsed rest. */
export function splitDone<T>(items: T[], doneAt: (item: T) => string | null | undefined, days: number, now = Date.now()): { recent: T[]; older: T[] } {
  if (days <= 0) return { recent: items, older: [] };
  const cutoff = now - days * 86_400_000;
  const recent: T[] = [];
  const older: T[] = [];
  for (const item of items) {
    const stamp = Date.parse(doneAt(item) ?? "");
    // Unknown dates stay visible: hiding is the exception, not the default.
    (Number.isNaN(stamp) || stamp >= cutoff ? recent : older).push(item);
  }
  return { recent, older };
}
