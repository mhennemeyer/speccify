// Segment-Schalter für das Erscheinungsbild — im Dashboard (Settings) und
// im Projektfenster (Einstellungen-Sheet) derselbe.

import type { ThemePref } from "../lib/theme";

const OPTIONS: Array<[ThemePref, string]> = [
  ["system", "System"],
  ["light", "Hell"],
  ["dark", "Dunkel"],
];

export default function ThemePicker({
  value,
  onChange,
}: {
  value: ThemePref;
  onChange: (next: ThemePref) => void;
}) {
  return (
    <div role="radiogroup" className="inline-flex gap-0.5 rounded-full bg-slate-100 p-0.5">
      {OPTIONS.map(([id, label]) => (
        <button
          key={id}
          type="button"
          role="radio"
          aria-checked={value === id}
          onClick={() => onChange(id)}
          className={`rounded-full px-3 py-1 text-xs font-medium ${
            value === id
              ? "bg-slate-800 text-white"
              : "text-slate-600 hover:bg-slate-200 hover:text-slate-800"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
