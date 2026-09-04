// Toolbar des Projektfensters (W7c). Drei Zonen wie in Xcode: links der
// Titel, in der Mitte konfigurierbare Knöpfe (`items` — heute leer, später
// Aktionen mit `toolbar: true` aus actions.json und ein Aktivitäts-Fenster),
// rechts feste Schalter (`trailing`: Bereiche, Einstellungen).

import type { ReactNode } from "react";

export interface ToolbarItem {
  id: string;
  title: string;
  icon: ReactNode;
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
}

export function ToolbarButton({
  active = false,
  title,
  onClick,
  disabled = false,
  children,
}: {
  active?: boolean;
  title: string;
  onClick: () => void;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-label={title}
      aria-pressed={active}
      disabled={disabled}
      className={`rounded px-1.5 py-1 disabled:opacity-40 ${
        active
          ? "text-slate-800 hover:bg-slate-200"
          : "text-slate-400 hover:bg-slate-200 hover:text-slate-700"
      }`}
    >
      {children}
    </button>
  );
}

/** Xcode-artige Schalter für die drei Bereiche. */
export function PanelIcon({ part }: { part: "nav" | "right" | "bottom" }) {
  return (
    <svg width="16" height="14" viewBox="0 0 16 14" aria-hidden="true">
      <rect x="0.5" y="0.5" width="15" height="13" rx="2" fill="none" stroke="currentColor" />
      {part === "nav" ? <rect x="1" y="1" width="5" height="12" fill="currentColor" /> : null}
      {part === "right" ? <rect x="10" y="1" width="5" height="12" fill="currentColor" /> : null}
      {part === "bottom" ? <rect x="1" y="9" width="14" height="4" fill="currentColor" /> : null}
    </svg>
  );
}

export function GearIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="2.2" />
      <path d="M8 1.8v1.7M8 12.5v1.7M1.8 8h1.7M12.5 8h1.7M3.6 3.6l1.2 1.2M11.2 11.2l1.2 1.2M3.6 12.4l1.2-1.2M11.2 4.8l1.2-1.2" />
    </svg>
  );
}

export default function Toolbar({
  title,
  subtitle,
  items = [],
  trailing,
}: {
  title: string;
  subtitle?: string;
  items?: ToolbarItem[];
  trailing?: ReactNode;
}) {
  return (
    <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-3 py-1">
      <h1 className="truncate text-sm font-bold text-slate-700" title={subtitle}>
        {title}
      </h1>
      {subtitle ? (
        <p className="min-w-0 truncate font-mono text-[10px] text-slate-400" title={subtitle}>
          {subtitle}
        </p>
      ) : null}
      {/* Mitte: konfigurierbare Knöpfe */}
      <div className="flex min-w-0 flex-1 items-center justify-center gap-0.5">
        {items.map((item) => (
          <ToolbarButton
            key={item.id}
            title={item.title}
            onClick={item.onClick}
            active={item.active}
            disabled={item.disabled}
          >
            {item.icon}
          </ToolbarButton>
        ))}
      </div>
      <div className="flex items-center gap-0.5">{trailing}</div>
    </header>
  );
}
