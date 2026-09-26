// Segment-Schalter für die Oberflächensprache (Spec 073) — im Dashboard
// (Settings) und im Einstellungen-Sheet der Projekt-/Workspace-Fenster.
// Die Sprachnamen stehen bewusst in ihrer eigenen Sprache.

import { t, useLanguage, type LanguagePref } from "../i18n";

const OPTIONS: Array<[LanguagePref, string]> = [
  ["system", "System"],
  ["de", "Deutsch"],
  ["en", "English"],
];

export default function LanguagePicker() {
  const [pref, , setPref] = useLanguage();
  return (
    <div role="radiogroup" aria-label={t("Sprache")} className="inline-flex gap-0.5 rounded-full bg-slate-100 p-0.5">
      {OPTIONS.map(([id, label]) => (
        <button
          key={id}
          type="button"
          role="radio"
          aria-checked={pref === id}
          data-language={id}
          onClick={() => void setPref(id)}
          className={`rounded-full px-3 py-1 text-xs font-medium ${
            pref === id
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
