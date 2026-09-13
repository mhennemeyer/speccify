// Agent-Fragen (ask_bo / show_ui, Spec 038) für ein Fenster: Events plus
// aktives Nachladen offener Fragen (Events sind flüchtig). Das Dashboard
// hält noch seine eigene Fassung in App.tsx; das Projektfenster nutzt diesen Hook.

import { useCallback, useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import type { AskBoInteraction } from "../components/AskBoPanel";

export function useAskBo(onNew?: (interaction: AskBoInteraction) => void) {
  const [interactions, setInteractions] = useState<AskBoInteraction[]>([]);
  useEffect(() => {
    const mergePending = async () => {
      try {
        const pending = await invoke<AskBoInteraction[]>("ask_bo_pending");
        if (pending.length === 0) return;
        setInteractions((current) => {
          const known = new Set(current.map((interaction) => interaction.id));
          const fresh = pending.filter((interaction) => !known.has(interaction.id));
          if (fresh.length === 0) return current;
          fresh.forEach((interaction) => onNew?.(interaction));
          return [...current, ...fresh];
        });
      } catch {
        // Command noch nicht bereit — nächster Tick.
      }
    };
    void mergePending();
    const timer = setInterval(() => void mergePending(), 5000);
    const unlisteners = [
      listen<AskBoInteraction>("ask-bo", (event) => {
        setInteractions((current) => {
          if (current.some((interaction) => interaction.id === event.payload.id)) return current;
          onNew?.(event.payload);
          return [...current, { ...event.payload }];
        });
      }),
      listen<{ id: string; selected_options: string[]; field_values: string[]; values?: Record<string, unknown> }>(
        "ask-bo-answered",
        (event) => {
          setInteractions((current) =>
            current.map((interaction) =>
              interaction.id === event.payload.id
                ? {
                    ...interaction,
                    answered: {
                      selectedOptions: event.payload.selected_options,
                      fieldValues: event.payload.field_values,
                      values: event.payload.values,
                    },
                  }
                : interaction,
            ),
          );
        },
      ),
    ];
    return () => {
      clearInterval(timer);
      unlisteners.forEach((promise) => void promise.then((unlisten) => unlisten()));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const answer = useCallback((id: string, selectedOptions: string[], fieldValues: string[]) => {
    void invoke("ask_bo_answer", { id, selectedOptions, fieldValues }).catch((error) => console.error(error));
  }, []);
  return { interactions, answer };
}
