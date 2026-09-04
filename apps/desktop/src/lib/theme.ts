// Erscheinungsbild (W7c): `system` | `light` | `dark`, global für alle
// Fenster. Quelle der Wahrheit ist `~/.speccify/settings.json` (Rust,
// `theme`); localStorage hält nur eine Kopie, damit das Fenster ohne
// Flackern in der richtigen Farbe startet. Ein Wechsel wird per
// Tauri-Event an alle Fenster gemeldet. Die Farben selbst sind CSS —
// `:root[data-theme="dark"]` in index.css spiegelt die Slate-Palette.

import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { emit, listen } from "@tauri-apps/api/event";

export type ThemePref = "system" | "light" | "dark";

const CACHE_KEY = "speccify.theme";
const EVENT = "speccify:theme";
const media = window.matchMedia("(prefers-color-scheme: dark)");

export function normalizeTheme(value: unknown): ThemePref {
  return value === "light" || value === "dark" ? value : "system";
}

export function applyTheme(pref: ThemePref): void {
  const dark = pref === "dark" || (pref === "system" && media.matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
}

function cached(): ThemePref {
  try {
    return normalizeTheme(localStorage.getItem(CACHE_KEY));
  } catch {
    return "system";
  }
}

/** Sofort beim Modul-Import anwenden — vor dem ersten Render. */
applyTheme(cached());

interface SettingsWithTheme {
  theme?: string;
  [key: string]: unknown;
}

export function useTheme(): [ThemePref, (next: ThemePref) => Promise<void>] {
  const [pref, setPref] = useState<ThemePref>(cached);
  const prefRef = useRef(pref);
  prefRef.current = pref;

  useEffect(() => {
    void invoke<SettingsWithTheme>("get_settings")
      .then((settings) => {
        const stored = normalizeTheme(settings.theme);
        setPref(stored);
        applyTheme(stored);
        try {
          localStorage.setItem(CACHE_KEY, stored);
        } catch {
          // ohne Cache geht es auch
        }
      })
      .catch(() => applyTheme(prefRef.current));
    const unlisten = listen<string>(EVENT, (event) => {
      const next = normalizeTheme(event.payload);
      setPref(next);
      applyTheme(next);
    });
    const onMedia = () => applyTheme(prefRef.current);
    media.addEventListener("change", onMedia);
    return () => {
      void unlisten.then((dispose) => dispose());
      media.removeEventListener("change", onMedia);
    };
  }, []);

  const update = useCallback(async (next: ThemePref) => {
    setPref(next);
    applyTheme(next);
    try {
      localStorage.setItem(CACHE_KEY, next);
    } catch {
      // dito
    }
    const settings = await invoke<SettingsWithTheme>("get_settings");
    await invoke("save_settings", { settings: { ...settings, theme: next } });
    await emit(EVENT, next);
  }, []);

  return [pref, update];
}
