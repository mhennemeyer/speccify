import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import type { ITheme } from "@xterm/xterm";

export interface TerminalPreferences {
  font_size: number;
  popups: boolean;
  system_notifications: boolean;
}
export function useTerminalPreferences() {
  const [preferences, setPreferences] = useState<TerminalPreferences>({ font_size: 14, popups: true, system_notifications: true });
  const [error, setError] = useState("");
  useEffect(() => {
    let disposed = false;
    const subscription = listen<TerminalPreferences>("terminal-preferences", e => { if (!disposed) setPreferences(e.payload); });
    void subscription.then(() => invoke<TerminalPreferences>("terminal_preferences")).then(value => {
      if (!disposed) setPreferences(value);
    }).catch(e => { if (!disposed) setError(String(e)); });
    return () => { disposed = true; void subscription.then(unlisten => unlisten()); };
  }, []);
  async function update(patch: Partial<TerminalPreferences>) {
    try {
      const next = await invoke<TerminalPreferences>("terminal_preferences_update", {
        fontSize: patch.font_size, popups: patch.popups, systemNotifications: patch.system_notifications,
      });
      setPreferences(next); setError("");
    } catch (e) { setError(String(e)); }
  }
  return { preferences, update, error };
}

export function terminalTheme(dark: boolean): ITheme {
  return dark ? {
    background: "#0f172a", foreground: "#e2e8f0", cursor: "#f8fafc", cursorAccent: "#0f172a",
    selectionBackground: "#334e78", selectionForeground: "#ffffff",
    black: "#64748b", red: "#f87171", green: "#4ade80", yellow: "#facc15",
    blue: "#60a5fa", magenta: "#c084fc", cyan: "#22d3ee", white: "#e2e8f0",
    brightBlack: "#94a3b8", brightRed: "#fca5a5", brightGreen: "#86efac", brightYellow: "#fde047",
    brightBlue: "#93c5fd", brightMagenta: "#d8b4fe", brightCyan: "#67e8f9", brightWhite: "#ffffff",
  } : {
    background: "#ffffff", foreground: "#172033", cursor: "#0f172a", cursorAccent: "#ffffff",
    selectionBackground: "#bfdbfe", selectionForeground: "#0f172a",
    black: "#172033", red: "#b91c1c", green: "#15803d", yellow: "#854d0e",
    blue: "#1d4ed8", magenta: "#7e22ce", cyan: "#0e7490", white: "#475569",
    brightBlack: "#64748b", brightRed: "#dc2626", brightGreen: "#166534", brightYellow: "#a16207",
    brightBlue: "#2563eb", brightMagenta: "#9333ea", brightCyan: "#0891b2", brightWhite: "#334155",
  };
}
