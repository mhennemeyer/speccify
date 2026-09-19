import type { ReactNode } from "react";
import { usePaged } from "../lib/doneWindow";

/**
 * Spec 061: renders the first `limit` items and a link-styled "Mehr anzeigen"
 * that reveals `limit` more per click. `render` receives the visible slice so
 * callers can group it as they like.
 */
export default function MoreList<T>({ items, limit, resetKey, render }: {
  items: T[]; limit: number; resetKey: string; render: (shown: T[]) => ReactNode;
}) {
  const { shown, hidden, more } = usePaged(items, limit, resetKey);
  return <>
    {render(shown)}
    {hidden > 0 && (
      <button type="button" data-done-more onClick={more}
        className="block px-1 py-1 text-[11px] text-slate-600 underline underline-offset-2 hover:text-slate-900">
        Mehr anzeigen ({hidden} weitere)
      </button>
    )}
  </>;
}
