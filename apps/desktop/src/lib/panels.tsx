// Seitenleisten-Anbindung (W7 — Xcode-/iKanban-Muster). Die Shell stellt
// pro Tab zwei DOM-Slots bereit: einen im **Navigator** (links, unter der
// Icon-Tab-Leiste: die Liste des Tabs) und einen im **Inspektor** (rechts:
// das Detail der Auswahl). Ein Tab rendert per Portal hinein und behält
// dabei seinen eigenen State (Auswahl, Fetches, Callbacks). Ist die
// jeweilige Seitenleiste zu, gibt es keinen Slot — dann rendert der Tab
// über `fallback` inline (Default: an Ort und Stelle).

import { Fragment, createContext, useContext, useState } from "react";
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

/** Tab in einem anderen Bereich anzeigen (Handler in ProjectShell). */
export function showTab(tab: string): void {
  window.dispatchEvent(new CustomEvent("speccify:show-tab", { detail: tab }));
}

/** Leerzustand einer Navigator-Liste: sagt, was fehlt, und bietet den
 *  nächsten Schritt an (BO 2026-09-06: nie eine leere Seitenleiste). */
export function NavEmpty({
  title,
  children,
  action,
}: {
  title: string;
  children?: ReactNode;
  action?: { label: string; onClick: () => void };
}) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 p-3">
      <p className="text-sm font-medium text-slate-700">{title}</p>
      {children ? <div className="mt-1 text-xs leading-5 text-slate-500">{children}</div> : null}
      {action ? (
        <button
          onClick={action.onClick}
          className="mt-2 rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
        >
          {action.label}
        </button>
      ) : null}
    </div>
  );
}

export interface InspectorTab {
  id: string;
  label: string;
  content: ReactNode;
}

/** Einheitlicher Inspektor-Inhalt: Kopf (Titel, Untertitel, Aktionen),
 *  Metadaten als Tabelle, darunter Tabs oder freier Inhalt. Wird per
 *  InspectorPortal in die Seitenleiste gerendert — oder inline, wenn sie
 *  zu ist; die Tabs gibt es in beiden Fällen. */
export function InspectorPanel({
  title,
  subtitle,
  actions,
  meta = [],
  tabs,
  children,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  meta?: Array<{ label: string; value: ReactNode }>;
  tabs?: InspectorTab[];
  children?: ReactNode;
}) {
  const firstTab = tabs?.[0]?.id ?? "";
  const [tab, setTab] = useState(firstTab);
  const current = tabs?.find((entry) => entry.id === tab) ?? tabs?.[0];
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <div className="mb-2">
        <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
        {subtitle ? (
          <p className="mt-0.5 truncate font-mono text-[11px] text-slate-400">{subtitle}</p>
        ) : null}
      </div>
      {actions ? <div className="mb-3 flex flex-wrap gap-1.5">{actions}</div> : null}
      {meta.length > 0 ? (
        <dl className="mb-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
          {meta.map((entry) => (
            <Fragment key={entry.label}>
              <dt className="text-slate-400">{entry.label}</dt>
              <dd className="min-w-0 break-words text-slate-700">{entry.value}</dd>
            </Fragment>
          ))}
        </dl>
      ) : null}
      {tabs && tabs.length > 0 ? (
        <>
          <div role="tablist" className="mb-3 flex gap-1 border-b border-slate-200 text-xs">
            {tabs.map((entry) => (
              <button
                key={entry.id}
                role="tab"
                aria-selected={current?.id === entry.id}
                onClick={() => setTab(entry.id)}
                className={`-mb-px px-3 py-1.5 font-medium ${
                  current?.id === entry.id
                    ? "border-b-2 border-slate-800 text-slate-800"
                    : "text-slate-400 hover:text-slate-700"
                }`}
              >
                {entry.label}
              </button>
            ))}
          </div>
          {current?.content}
        </>
      ) : (
        children
      )}
    </div>
  );
}

/** Kleiner Aktionsknopf für den Inspektor-Kopf. */
export function InspectorButton({
  onClick,
  children,
  title,
  disabled,
  tone = "default",
}: {
  onClick: () => void;
  children: ReactNode;
  title?: string;
  disabled?: boolean;
  tone?: "default" | "primary" | "danger";
}) {
  const cls =
    tone === "primary"
      ? "bg-emerald-600 text-white hover:bg-emerald-700"
      : tone === "danger"
        ? "border border-red-200 text-red-600 hover:bg-red-50"
        : "border border-slate-300 text-slate-600 hover:bg-slate-100";
  return (
    <button
      onClick={onClick}
      title={title}
      disabled={disabled}
      className={`rounded px-2.5 py-1 text-xs font-medium disabled:opacity-40 ${cls}`}
    >
      {children}
    </button>
  );
}

/** Fallback für InspectorPortal, wenn der Inspektor zu ist: als Kasten
 *  über dem Inhalt statt in der Seitenleiste. */
export function inlineInspector(children: ReactNode): ReactNode {
  return (
    <div className="mb-3 flex max-h-[40%] flex-col overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
      {children}
    </div>
  );
}
