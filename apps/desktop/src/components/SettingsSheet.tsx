// Einstellungen des Projektfensters (W7c): Erscheinungsbild (global),
// Terminal-Position und Layout-Reset (pro Projekt). Das Agent-Kommando
// bleibt im Agent-Tab und am Terminal-Start.

import ThemePicker from "./ThemePicker";
import type { ThemePref } from "../lib/theme";
import type { ProjectLayout, TerminalDock } from "../lib/layout";

export default function SettingsSheet({
  theme,
  onTheme,
  layout,
  onDock,
  onResetLayout,
  onClose,
}: {
  theme: ThemePref;
  onTheme: (next: ThemePref) => void;
  layout: ProjectLayout;
  onDock: (dock: TerminalDock) => void;
  onResetLayout: () => void;
  onClose: () => void;
}) {
  return (
    // Popover unter dem Zahnrad, ohne Abdunkeln — ein dunkler Schleier
    // liest sich wie ein Moduswechsel (BO-Finding 2026-09-04).
    <div className="fixed inset-0 z-40" onClick={onClose}>
      <div
        role="dialog"
        aria-label="Einstellungen"
        onClick={(event) => event.stopPropagation()}
        className="absolute right-2 top-9 w-[400px] rounded-xl border border-slate-200 bg-white p-5 shadow-xl"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-800">Einstellungen</h2>
          <button onClick={onClose} className="text-xs text-slate-400 hover:text-slate-700">
            Schließen
          </button>
        </div>

        <section className="mb-4">
          <h3 className="mb-1 text-xs font-semibold text-slate-500">Erscheinungsbild</h3>
          <p className="mb-2 text-xs text-slate-500">Gilt für alle Fenster.</p>
          <ThemePicker value={theme} onChange={onTheme} />
        </section>

        <section className="mb-4">
          <h3 className="mb-1 text-xs font-semibold text-slate-500">Agent-Terminal</h3>
          <div role="radiogroup" className="inline-flex gap-0.5 rounded-full bg-slate-100 p-0.5">
            {(
              [
                ["bottom", "Unten"],
                ["right", "Rechts"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="radio"
                aria-checked={layout.terminalDock === id}
                onClick={() => onDock(id)}
                className={`rounded-full px-3 py-1 text-xs font-medium ${
                  layout.terminalDock === id
                    ? "bg-slate-800 text-white"
                    : "text-slate-600 hover:bg-slate-200 hover:text-slate-800"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </section>

        <section>
          <h3 className="mb-1 text-xs font-semibold text-slate-500">Layout</h3>
          <p className="mb-2 text-xs text-slate-500">
            Breiten und Sichtbarkeiten der Bereiche werden pro Projekt gemerkt.
          </p>
          <button
            onClick={onResetLayout}
            className="rounded border border-slate-300 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100"
          >
            Layout zurücksetzen
          </button>
        </section>
      </div>
    </div>
  );
}
