// Toolbar des Projektfensters (W7c). Drei Zonen wie in Xcode: links der
// Titel, in der Mitte konfigurierbare Knöpfe (`items` — heute leer, später
// Aktionen mit `toolbar: true` aus actions.json und ein Aktivitäts-Fenster),
// rechts feste Schalter (`trailing`: Bereiche, Einstellungen).

import type { ReactNode } from "react";
import { TRAFFIC_LIGHT_INSET } from "../lib/platform";

export interface ToolbarItem {
  id: string;
  title: string;
  icon: ReactNode;
  /** Kurzer Text neben dem Icon (Aktionen aus actions.json). */
  label?: string;
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
}

export function GitIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <circle cx="4.5" cy="3.5" r="1.6" />
      <circle cx="4.5" cy="12.5" r="1.6" />
      <circle cx="11.5" cy="6" r="1.6" />
      <path d="M4.5 5.1v5.8M11.5 7.6c0 2.2-2.5 2.6-4.7 2.9" />
    </svg>
  );
}

export function TerminalIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <rect x="1.5" y="2.5" width="13" height="11" rx="1.5" />
      <path d="M4.5 6l2.5 2-2.5 2M8.5 10.5h3" />
    </svg>
  );
}

export function PlayIcon() {
  return (
    <Icon>
      <path d="M4.5 3v10l8-5z" />
    </Icon>
  );
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

function Icon({ children }: { children: ReactNode }) {
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
      {children}
    </svg>
  );
}

/** Zahnrad — mit Zähnen, nicht mit Strahlen (sonst liest man eine Sonne). */
export function GearIcon() {
  return (
    <Icon>
      <path d="M6.9 1.8h2.2l.4 1.6a5 5 0 0 1 1.3.75l1.55-.55 1.1 1.9-1.2 1.1a5 5 0 0 1 0 1.5l1.2 1.1-1.1 1.9-1.55-.55a5 5 0 0 1-1.3.75l-.4 1.6H6.9l-.4-1.6a5 5 0 0 1-1.3-.75l-1.55.55-1.1-1.9 1.2-1.1a5 5 0 0 1 0-1.5l-1.2-1.1 1.1-1.9 1.55.55a5 5 0 0 1 1.3-.75z" />
      <circle cx="8" cy="8" r="1.8" />
    </Icon>
  );
}

export function SunIcon() {
  return (
    <Icon>
      <circle cx="8" cy="8" r="2.6" />
      <path d="M8 1.5v1.6M8 12.9v1.6M1.5 8h1.6M12.9 8h1.6M3.4 3.4l1.1 1.1M11.5 11.5l1.1 1.1M3.4 12.6l1.1-1.1M11.5 4.5l1.1-1.1" />
    </Icon>
  );
}

export function MoonIcon() {
  return (
    <Icon>
      <path d="M13.2 9.6A5.6 5.6 0 0 1 6.4 2.8a5.6 5.6 0 1 0 6.8 6.8z" />
    </Icon>
  );
}

export default function Toolbar({
  title,
  subtitle,
  items = [],
  center,
  trailing,
}: {
  title: string;
  subtitle?: string;
  items?: ToolbarItem[];
  /** Mitte, rechts neben den Knöpfen — die Aktivitätsanzeige. */
  center?: ReactNode;
  trailing?: ReactNode;
}) {
  return (
    // data-tauri-drag-region: die Toolbar ersetzt auf macOS die Titelleiste,
    // also zieht man das Fenster an ihr (Kinder-Elemente bleiben klickbar).
    <header
      data-tauri-drag-region="deep"
      className="flex items-center gap-3 border-b border-slate-200 bg-white px-3"
      style={{ paddingLeft: 12 + TRAFFIC_LIGHT_INSET, minHeight: 38 }}
    >
      <h1 className="truncate text-sm font-bold text-slate-700" title={subtitle}>
        {title}
      </h1>
      {subtitle ? (
        <p className="min-w-0 truncate font-mono text-[10px] text-slate-400" title={subtitle}>
          {subtitle}
        </p>
      ) : null}
      {/* Mitte: konfigurierbare Knöpfe */}
      <div
        data-tauri-drag-region="deep"
        className="flex min-w-0 flex-1 items-center justify-center gap-0.5"
      >
        {items.map((item) => (
          <ToolbarButton
            key={item.id}
            title={item.title}
            onClick={item.onClick}
            active={item.active}
            disabled={item.disabled}
          >
            <span className="flex items-center gap-1">
              {item.icon}
              {item.label ? <span className="text-[11px] font-medium">{item.label}</span> : null}
            </span>
          </ToolbarButton>
        ))}
        {items.length > 0 && center ? (
          <span className="mx-2 h-4 w-px bg-slate-200" aria-hidden="true" />
        ) : null}
        {center}
      </div>
      <div className="flex items-center gap-0.5">{trailing}</div>
    </header>
  );
}
