// Inspektor-Anbindung (W7 „projektweite Auswahl: Board ↔ Inspector").
// Die Shell stellt pro Tab einen DOM-Slot in der rechten Seitenleiste
// bereit; ein Tab rendert sein Detail per Portal hinein und behält dabei
// seinen eigenen State (Auswahl, History, Callbacks). Ist die Seitenleiste
// zu, gibt es keinen Slot — der Tab zeigt das Detail dann inline.

import { createContext, useContext } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";

export interface InspectorApi {
  slots: Record<string, HTMLElement | null>;
  /** Rechte Seitenleiste auf den Inspektor-Tab schalten (z. B. bei neuer Auswahl). */
  reveal: () => void;
}

export const InspectorContext = createContext<InspectorApi>({ slots: {}, reveal: () => {} });

export function useInspector(tab: string): { slot: HTMLElement | null; reveal: () => void } {
  const api = useContext(InspectorContext);
  return { slot: api.slots[tab] ?? null, reveal: api.reveal };
}

/** Rendert `children` in den Inspektor-Slot des Tabs oder — ohne Slot —
 *  über `fallback` (Default: inline an Ort und Stelle). */
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
  if (slot) return createPortal(children, slot);
  return <>{fallback ? fallback(children) : children}</>;
}
