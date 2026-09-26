// Oberflächensprache (Spec 073): Deutsch ist der Quelltext, Englisch kommt
// aus dem Wörterbuch `en.ts`. `t("Neu starten")` liefert je nach Sprache den
// deutschen Schlüssel oder seine Übersetzung; fehlt sie, bleibt der deutsche
// Text — nie ein Schlüssel, nie ein leerer String. Die Einstellung liegt wie
// das Theme in `~/.speccify/settings.json` (`language`: system | de | en) und
// wird per Tauri-Event an alle Fenster gemeldet; localStorage hält eine Kopie
// für den ersten Render.

import { useCallback, useSyncExternalStore } from "react";
import { invoke } from "@tauri-apps/api/core";
import { emit, listen } from "@tauri-apps/api/event";
import { en } from "./en";

export type LanguagePref = "system" | "de" | "en";
export type Language = "de" | "en";

const CACHE_KEY = "speccify.language";
const EVENT = "speccify:language";

export function normalizeLanguage(value: unknown): LanguagePref {
  return value === "de" || value === "en" ? value : "system";
}

/** Systemsprache: Deutsch bei `de*`, sonst Englisch. */
export function systemLanguage(): Language {
  const tag = (typeof navigator !== "undefined" ? navigator.language : "") || "";
  return tag.toLowerCase().startsWith("de") ? "de" : "en";
}

export function resolveLanguage(pref: LanguagePref): Language {
  return pref === "system" ? systemLanguage() : pref;
}

function cached(): LanguagePref {
  try {
    return normalizeLanguage(localStorage.getItem(CACHE_KEY));
  } catch {
    return "system";
  }
}

let pref: LanguagePref = cached();
const listeners = new Set<() => void>();

function apply(next: LanguagePref): void {
  pref = next;
  if (typeof document !== "undefined") {
    document.documentElement.lang = resolveLanguage(next);
  }
  for (const listener of listeners) listener();
}

apply(pref);

export function currentLanguage(): Language {
  return resolveLanguage(pref);
}

export function languagePref(): LanguagePref {
  return pref;
}

/** Übersetzt einen deutschen Quelltext; `{name}`-Platzhalter werden aus `vars` gefüllt. */
export function t(text: string, vars?: Record<string, string | number>): string {
  let out = text;
  if (currentLanguage() === "en") {
    const hit = en[text];
    if (hit) out = hit;
  }
  if (vars) {
    for (const [key, value] of Object.entries(vars)) {
      out = out.split(`{${key}}`).join(String(value));
    }
  }
  return out;
}

/** Einzahl/Mehrzahl mit Zahl: `plural(n, "Lauf", "Läufe")` → "1 Lauf" / "3 Läufe". */
export function plural(count: number, one: string, many: string): string {
  return `${count} ${t(count === 1 ? one : many)}`;
}

interface SettingsWithLanguage {
  language?: string;
  [key: string]: unknown;
}

let initialized = false;

/** Einmal je Fenster: gespeicherte Einstellung laden und Wechsel anderer Fenster hören. */
export function initLanguage(): void {
  if (initialized) return;
  initialized = true;
  void invoke<SettingsWithLanguage>("get_settings")
    .then((settings) => {
      const stored = normalizeLanguage(settings.language);
      apply(stored);
      try {
        localStorage.setItem(CACHE_KEY, stored);
      } catch {
        // ohne Cache geht es auch
      }
    })
    .catch(() => apply(pref));
  void listen<string>(EVENT, (event) => apply(normalizeLanguage(event.payload)));
}

export async function updateLanguage(next: LanguagePref): Promise<void> {
  apply(next);
  try {
    localStorage.setItem(CACHE_KEY, next);
  } catch {
    // dito
  }
  const settings = await invoke<SettingsWithLanguage>("get_settings");
  await invoke("save_settings", { settings: { ...settings, language: next } });
  await emit(EVENT, next);
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Einstellung, wirksame Sprache und Setter; der Aufrufer rendert bei jedem Wechsel neu. */
export function useLanguage(): [LanguagePref, Language, (next: LanguagePref) => Promise<void>] {
  const current = useSyncExternalStore(subscribe, () => pref, () => pref);
  const update = useCallback((next: LanguagePref) => updateLanguage(next), []);
  return [current, resolveLanguage(current), update];
}
