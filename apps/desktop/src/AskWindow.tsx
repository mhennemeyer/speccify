// Frage-Popup (BO-Finding 2026-09-13): jede Agent-Interaktion (ask_bo / show_ui)
// bekommt ein eigenes kleines Fenster `ask-<n>`, das sich nach der Antwort
// bzw. dem Schließen der Anzeige von selbst schließt. So landet die Frage
// nicht im Dashboard, während man im Projektfenster arbeitet.

import { useEffect, useMemo } from "react";
import { getCurrentWebviewWindow } from "@tauri-apps/api/webviewWindow";
import AskBoPanel from "./components/AskBoPanel";
import { useAskBo } from "./lib/askBo";
import { useTheme } from "./lib/theme";

export default function AskWindow() {
  useTheme();
  const id = getCurrentWebviewWindow().label.replace(/^ask-/, "ask-");
  const askBo = useAskBo();
  const mine = useMemo(() => askBo.interactions.filter((interaction) => interaction.id === id), [askBo.interactions, id]);
  const done = mine.length > 0 && mine[0].answered !== undefined;

  useEffect(() => {
    if (!done) return;
    // Antwort kurz sichtbar lassen, dann Fenster schließen.
    const timer = setTimeout(() => {
      void getCurrentWebviewWindow().close().catch(() => {});
    }, 600);
    return () => clearTimeout(timer);
  }, [done]);

  return (
    <div className="keep-dark flex h-screen flex-col bg-slate-800 text-slate-100">
      <div data-tauri-drag-region className="flex h-9 shrink-0 items-center justify-center text-[11px] text-slate-400">
        {mine[0]?.title || mine[0]?.prompt || "Agent fragt"}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto" data-ask-window={id}>
        {mine.length > 0 ? (
          <AskBoPanel interactions={mine} onAnswer={askBo.answer} htmlInline />
        ) : (
          <p className="p-4 text-sm text-slate-400">Frage wird geladen…</p>
        )}
      </div>
    </div>
  );
}
