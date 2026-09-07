// Autosave + Entwurfs-Speicher (BO-Finding 2026-09-07: ein App-Neustart
// während des Schreibens hat einen ganzen Plan gekostet). Zwei Schichten:
// 1. Jeder Tastenanschlag landet sofort als Entwurf in localStorage
//    (synchron, überlebt Neustart und Reload).
// 2. Kurz nach dem Tippen wird in die Datei gespeichert; gelingt das,
//    ist der Entwurf hinfällig und wird gelöscht.
// Beim nächsten Öffnen findet der Editor einen übrig gebliebenen Entwurf
// und stellt ihn wieder her.

import { useCallback, useEffect, useRef, useState } from "react";

export type AutosaveStatus = "saved" | "dirty" | "saving" | "error";

export function draftKey(project: string, file: string): string {
  return `speccify.draft:${project}:${file}`;
}

export function readDraft(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeDraft(key: string, text: string): void {
  try {
    localStorage.setItem(key, text);
  } catch {
    // Quota voll oder kein Storage — dann bleibt nur das Autosave.
  }
}

export function clearDraft(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // dito
  }
}

/** Hält `content` gegen `original` gespeichert: Entwurf sofort, Datei nach
 *  `delay` ms Ruhe, Rest beim Unmount. `save` schreibt die Datei. */
export function useAutosave({
  key,
  content,
  original,
  save,
  delay = 1200,
}: {
  key: string;
  content: string;
  original: string;
  save: (content: string) => Promise<void>;
  delay?: number;
}): { status: AutosaveStatus; error: string | null; flush: () => Promise<void> } {
  const [status, setStatus] = useState<AutosaveStatus>("saved");
  const [error, setError] = useState<string | null>(null);
  const lastSaved = useRef(original);
  const latest = useRef(content);
  const saveRef = useRef(save);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  latest.current = content;
  saveRef.current = save;

  const flush = useCallback(async () => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    const text = latest.current;
    if (text === lastSaved.current) return;
    setStatus("saving");
    try {
      await saveRef.current(text);
      lastSaved.current = text;
      clearDraft(key);
      setError(null);
      setStatus(latest.current === text ? "saved" : "dirty");
    } catch (e) {
      setError(String(e));
      setStatus("error");
    }
  }, [key]);

  useEffect(() => {
    if (content === lastSaved.current) {
      clearDraft(key);
      setStatus((previous) => (previous === "error" ? previous : "saved"));
      return;
    }
    writeDraft(key, content);
    setStatus("dirty");
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => void flush(), delay);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [content, key, delay, flush]);

  // Unmount (Editor zu, Tab weg): Rest sofort wegschreiben.
  useEffect(() => {
    return () => {
      if (latest.current !== lastSaved.current) {
        const text = latest.current;
        void saveRef.current(text).then(() => clearDraft(key)).catch(() => {});
      }
    };
  }, [key]);

  return { status, error, flush };
}

export function autosaveLabel(status: AutosaveStatus): string {
  switch (status) {
    case "saved":
      return "Gespeichert";
    case "dirty":
      return "Entwurf gesichert · speichert gleich…";
    case "saving":
      return "Speichert…";
    case "error":
      return "Speichern fehlgeschlagen — Entwurf bleibt gesichert";
  }
}
