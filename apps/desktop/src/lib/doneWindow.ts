import { invoke } from "@tauri-apps/api/core";
import { useCallback, useEffect, useState } from "react";

/**
 * Spec 061: the Done column shows only what reached Done within a window of
 * days, and at most `limit` cards at once ("Mehr anzeigen" reveals more);
 * everything older is collapsed. Both are board settings stored in the board
 * root's `.agent/settings.json` (`board.doneDays`, `board.doneLimit`), so they
 * are per project or workspace and shared through Git. `0` means "all".
 */
export const DONE_WINDOW_DEFAULT = 14;
export const DONE_LIMIT_DEFAULT = 10;
export const DONE_WINDOW_OPTIONS: Array<{ days: number; label: string }> = [
  { days: 7, label: "7 Tage" },
  { days: 14, label: "14 Tage" },
  { days: 30, label: "30 Tage" },
  { days: 90, label: "90 Tage" },
  { days: 0, label: "Alle Tage" },
];
export const DONE_LIMIT_OPTIONS: Array<{ limit: number; label: string }> = [
  { limit: 5, label: "5 Karten" },
  { limit: 10, label: "10 Karten" },
  { limit: 20, label: "20 Karten" },
  { limit: 50, label: "50 Karten" },
  { limit: 0, label: "Alle Karten" },
];

export function normaliseDoneSetting(value: unknown, fallback: number): number {
  const number = typeof value === "number" ? value : Number(value);
  return Number.isInteger(number) && number >= 0 ? number : fallback;
}

export interface DoneBoardSettings {
  days: number;
  limit: number;
  setDays: (days: number) => void;
  setLimit: (limit: number) => void;
  error: string | null;
}

/** Reads and writes the board's Done settings; `root` is the project or workspace root. */
export function useDoneBoard(root: string | null | undefined): DoneBoardSettings {
  const [days, setDaysState] = useState(DONE_WINDOW_DEFAULT);
  const [limit, setLimitState] = useState(DONE_LIMIT_DEFAULT);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!root) return;
    let stale = false;
    setDaysState(DONE_WINDOW_DEFAULT);
    setLimitState(DONE_LIMIT_DEFAULT);
    invoke<Record<string, unknown>>("project_settings_get", { project: root })
      .then(settings => {
        if (stale) return;
        const board = (settings.board ?? {}) as Record<string, unknown>;
        if ("doneDays" in board) setDaysState(normaliseDoneSetting(board.doneDays, DONE_WINDOW_DEFAULT));
        if ("doneLimit" in board) setLimitState(normaliseDoneSetting(board.doneLimit, DONE_LIMIT_DEFAULT));
      })
      .catch(() => { /* ohne Settings gelten die Defaults */ });
    return () => { stale = true; };
  }, [root]);
  const persist = useCallback((key: string, value: number, fallback: number, apply: (v: number) => void, previous: number) => {
    apply(value);
    setError(null);
    if (!root) return;
    // The default is not written: a board without the key behaves like every other.
    invoke("project_settings_set", { project: root, key, value: value === fallback ? null : value })
      .catch(e => { apply(previous); setError(String(e)); });
  }, [root]);
  const setDays = useCallback((next: number) => persist("board.doneDays", next, DONE_WINDOW_DEFAULT, setDaysState, days), [persist, days]);
  const setLimit = useCallback((next: number) => persist("board.doneLimit", next, DONE_LIMIT_DEFAULT, setLimitState, limit), [persist, limit]);
  return { days, limit, setDays, setLimit, error };
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

/**
 * Shows `limit` items, plus `limit` more per "Mehr anzeigen". `limit` 0 shows
 * all. The count resets whenever the underlying list changes identity key.
 */
export function usePaged<T>(items: T[], limit: number, resetKey: string): { shown: T[]; hidden: number; more: () => void } {
  const [pages, setPages] = useState(1);
  useEffect(() => { setPages(1); }, [resetKey, limit]);
  const visible = limit <= 0 ? items.length : Math.min(items.length, pages * limit);
  return {
    shown: items.slice(0, visible),
    hidden: items.length - visible,
    more: () => setPages(pages + 1),
  };
}
