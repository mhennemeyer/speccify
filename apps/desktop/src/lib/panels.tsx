// Seitenleisten-Anbindung (W7 — Xcode-/iKanban-Muster). Die Shell stellt
// pro Tab zwei DOM-Slots bereit: einen im **Navigator** (links, unter der
// Icon-Tab-Leiste: die Liste des Tabs) und einen im **Inspektor** (rechts:
// das Detail der Auswahl). Ein Tab rendert per Portal hinein und behält
// dabei seinen eigenen State (Auswahl, Fetches, Callbacks). Ist die
// jeweilige Seitenleiste zu, gibt es keinen Slot — dann rendert der Tab
// über `fallback` inline (Default: an Ort und Stelle).

import { createContext, useContext } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";

export type Slots = Record<string, HTMLElement | null>;

export interface PanelsApi {
  navigator: Slots;
  inspector: Slots;
  /** Rechte Seitenleiste auf den Inspektor-Tab schalten (z. B. bei neuer Auswahl). */
  reveal: () => void;
}

export const PanelsContext = createContext<PanelsApi>({
  navigator: {},
  inspector: {},
  reveal: () => {},
});

export function useInspector(tab: string): { slot: HTMLElement | null; reveal: () => void } {
  const api = useContext(PanelsContext);
  return { slot: api.inspector[tab] ?? null, reveal: api.reveal };
}

export function useNavigator(tab: string): HTMLElement | null {
  return useContext(PanelsContext).navigator[tab] ?? null;
}

function Portal({
  slot,
  children,
  fallback,
}: {
  slot: HTMLElement | null;
  children: ReactNode;
  fallback?: (children: ReactNode) => ReactNode;
}) {
  if (slot) return createPortal(children, slot);
  return <>{fallback ? fallback(children) : children}</>;
}

/** Rendert `children` in den Inspektor-Slot des Tabs oder — ohne Slot —
 *  über `fallback`. */
export function InspectorPortal({
  tab,
  children,
  fallback,
}: {
  tab: string;
  children: ReactNode;
  fallback?: (children: ReactNode) => ReactNode;
}) {
  const { slot } = useInspector(tab);
  return <Portal slot={slot} fallback={fallback}>{children}</Portal>;
}

/** Rendert die Liste eines Tabs in den Navigator-Slot oder — ohne Slot —
 *  inline als schmale Spalte links vom Inhalt (das alte Layout). */
export function NavigatorPortal({
  tab,
  children,
  fallback = inlineList,
}: {
  tab: string;
  children: ReactNode;
  fallback?: (children: ReactNode) => ReactNode;
}) {
  const slot = useNavigator(tab);
  return <Portal slot={slot} fallback={fallback}>{children}</Portal>;
}

function inlineList(children: ReactNode) {
  return <div className="w-72 shrink-0 overflow-y-auto pr-1">{children}</div>;
}

/** Einheitlicher Listeneintrag für Navigator-Listen. */
export function NavRow({
  selected,
  onClick,
  title,
  children,
  subtitle,
  trailing,
}: {
  selected: boolean;
  onClick: () => void;
  title?: string;
  children: ReactNode;
  subtitle?: ReactNode;
  trailing?: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left ${
        selected ? "bg-slate-800 text-white" : "text-slate-700 hover:bg-slate-100"
      }`}
    >
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm">{children}</span>
        {subtitle ? (
          <span
            className={`block truncate text-[11px] ${selected ? "text-slate-300" : "text-slate-400"}`}
          >
            {subtitle}
          </span>
        ) : null}
      </span>
      {trailing ? <span className="shrink-0">{trailing}</span> : null}
    </button>
  );
}
