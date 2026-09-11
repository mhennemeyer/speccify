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
  onResumeAgent,
  toolbar,
  toolbarChoices,
  onToolbar,
  onResetLayout,
  onClose,
}: {
  theme: ThemePref;
  onTheme: (next: ThemePref) => void;
  layout: ProjectLayout;
  onDock: (dock: TerminalDock) => void;
  onResumeAgent?: (value: boolean) => void;
  /** Toolbar (I3): aktive Knopf-Ids in Reihenfolge + alle wählbaren. */
  toolbar: string[];
  toolbarChoices: Array<{ id: string; label: string; hint: string }>;
  onToolbar: (ids: string[]) => void;
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

        <section className="mb-4">
          <h3 className="mb-1 text-xs font-semibold text-slate-500">Agent-Sitzung</h3>
          {onResumeAgent ? <label className="flex items-start gap-2 text-xs text-slate-600">
            <input
              type="checkbox"
              checked={layout.resumeAgent}
              onChange={(event) => onResumeAgent(event.target.checked)}
              className="mt-0.5"
            />
            <span>
              Nach einem Neustart der App die letzte Sitzung automatisch fortsetzen
              (<code>claude --continue</code> bzw. <code>codex resume --last</code>). Der
              Agent behält so seinen Kontext — auch bei Dev-Neustarts von Speccify.
            </span>
          </label> : <p className="text-xs text-slate-500">Im Workspace startest Du eine gemeinsame Sitzung im Parent-Ordner ausdrücklich. Beim App-Neustart wird keine Sitzung automatisch gestartet.</p>}
        </section>

        <section className="mb-4">
          <h3 className="mb-1 text-xs font-semibold text-slate-500">Toolbar</h3>
          <p className="mb-2 text-xs text-slate-500">
            Knöpfe in der Mitte der Toolbar — eingebaute und Aktionen aus{" "}
            <code>actions.json</code>; Reihenfolge per Pfeil. Pro Projekt gemerkt.
          </p>
          <ul className="max-h-48 space-y-0.5 overflow-y-auto rounded border border-slate-200 p-1.5">
            {[
              ...toolbar
                .map((id) => toolbarChoices.find((choice) => choice.id === id))
                .filter((choice): choice is { id: string; label: string; hint: string } => Boolean(choice)),
              ...toolbarChoices.filter((choice) => !toolbar.includes(choice.id)),
            ].map((choice) => {
              const position = toolbar.indexOf(choice.id);
              const enabled = position >= 0;
              const move = (delta: number) => {
                const next = [...toolbar];
                const target = position + delta;
                if (target < 0 || target >= next.length) return;
                [next[position], next[target]] = [next[target], next[position]];
                onToolbar(next);
              };
              return (
                <li key={choice.id} className="flex items-center gap-2 rounded px-1 py-0.5 text-xs hover:bg-slate-50">
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={(event) =>
                      onToolbar(
                        event.target.checked
                          ? [...toolbar, choice.id]
                          : toolbar.filter((id) => id !== choice.id),
                      )
                    }
                  />
                  <span className="min-w-0 flex-1 truncate text-slate-700" title={choice.hint}>
                    {choice.label}
                    {choice.id.startsWith("action:") ? (
                      <span className="ml-1 font-mono text-[10px] text-slate-400">{choice.hint}</span>
                    ) : null}
                  </span>
                  {enabled ? (
                    <span className="flex gap-0.5">
                      <button
                        onClick={() => move(-1)}
                        disabled={position === 0}
                        className="rounded px-1 text-slate-400 hover:text-slate-800 disabled:opacity-30"
                        title="nach links"
                      >
                        ↑
                      </button>
                      <button
                        onClick={() => move(1)}
                        disabled={position === toolbar.length - 1}
                        className="rounded px-1 text-slate-400 hover:text-slate-800 disabled:opacity-30"
                        title="nach rechts"
                      >
                        ↓
                      </button>
                    </span>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </section>

        <section>
          <h3 className="mb-1 text-xs font-semibold text-slate-500">Layout</h3>
          <p className="mb-2 text-xs text-slate-500">
            Breiten, Sichtbarkeiten und Toolbar werden pro Projekt gemerkt.
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
