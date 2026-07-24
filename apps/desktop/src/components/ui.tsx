// Gemeinsame UI-Bausteine: Spinner, Loading-Wrapper, Buttons mit Busy-Feedback.

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

export function Spinner({ large = false }: { large?: boolean }) {
  const size = large ? "h-8 w-8 border-[3px]" : "h-4 w-4 border-2";
  return (
    <span
      className={`inline-block ${size} animate-spin rounded-full border-slate-300 border-t-slate-800 align-middle`}
    />
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      {message}
    </div>
  );
}

/** Wrapper: zeigt sofort einen Spinner, bis der echte Inhalt da ist. */
export function LoadingBoundary({
  loading,
  error,
  label,
  children,
}: {
  loading: boolean;
  error: string | null;
  label?: string;
  children: ReactNode;
}) {
  if (error) return <ErrorBox message={error} />;
  if (loading)
    return (
      <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-6 text-slate-500">
        <Spinner large />
        {label ?? "lädt…"}
      </div>
    );
  return <>{children}</>;
}

/** Button für async-Aktionen: disabled + Spinner, solange die Aktion läuft. */
export function ActionButton({
  onClick,
  children,
  className = "bg-slate-100 text-slate-700 hover:bg-slate-200",
  title,
}: {
  onClick: () => Promise<unknown>;
  children: ReactNode;
  className?: string;
  title?: string;
}) {
  const [busy, setBusy] = useState(false);
  const handle = async () => {
    setBusy(true);
    try {
      await onClick();
    } finally {
      setBusy(false);
    }
  };
  return (
    <button
      onClick={handle}
      disabled={busy}
      title={title}
      className={`rounded px-3 py-1 text-sm disabled:opacity-60 ${className}`}
    >
      {busy ? <Spinner /> : children}
    </button>
  );
}

// Stale-while-revalidate: letzte Daten pro Key, damit ein erneuter Mount
// (Tab-Wechsel, Neustart der View) sofort Inhalt zeigt statt Spinner.
const asyncCache = new Map<string, unknown>();

/** Standardisierter Fetch-State: sofortiges loading beim Erstladen,
 *  gecachte Daten sofort + stille Hintergrund-Aktualisierung danach. */
export function useAsync<T>(fn: () => Promise<T>, cacheKey?: string) {
  const cached = cacheKey ? (asyncCache.get(cacheKey) as T | undefined) : undefined;
  const [data, setData] = useState<T | null>(cached ?? null);
  const [loading, setLoading] = useState(cached === undefined);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const hasDataRef = useRef(cached !== undefined);

  const reload = useCallback(async () => {
    if (hasDataRef.current) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);
    try {
      const result = await fnRef.current();
      setData(result);
      hasDataRef.current = true;
      if (cacheKey) asyncCache.set(cacheKey, result);
    } catch (e) {
      setError(String(e));
      if (!hasDataRef.current) setData(null);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [cacheKey]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { data, loading, refreshing, error, reload };
}
