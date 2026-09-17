import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { useCallback, useEffect, useState } from "react";

export interface UpdateSnapshot {
  current_version: string; supported: boolean; reason: string | null;
  preferences: { automatic: boolean; interval_hours: number };
  phase: "idle" | "checking" | "available" | "current" | "downloading" | "ready" | "preparing" | "installing" | "error";
  version: string | null; notes: string | null; downloaded: number;
  total: number | null; last_checked: number | null; error: string | null;
  active_work: number;
}
export function useUpdateSnapshot() {
  const [snapshot, setSnapshot] = useState<UpdateSnapshot>();
  const refresh = useCallback(async () => {
    setSnapshot(await invoke<UpdateSnapshot>("update_snapshot"));
  }, []);
  useEffect(() => {
    let stopped = false;
    const refresh = () => void invoke<UpdateSnapshot>("update_snapshot").then(value => {
      if (!stopped) setSnapshot(value);
    }).catch(() => {});
    refresh();
    const timer = setInterval(refresh, 1000);
    return () => { stopped = true; clearInterval(timer); };
  }, []);
  return { snapshot, refresh };
}

const changedFields = new Set<Element>();
export function updateBlockers(): string[] {
  const blockers: string[] = [];
  const editors = [...document.querySelectorAll('textarea:not(.xterm-helper-textarea), .cm-editor, [contenteditable="true"]')];
  if (document.querySelector('[data-update-dirty="true"]') || editors.some(editor => {
    if (editor.closest('[data-update-dirty="false"]')) return false;
    if (editor instanceof HTMLTextAreaElement) return !editor.readOnly && editor.value.length > 0;
    return true;
  })) {
    blockers.push("Editoransichten zuerst speichern und schließen.");
  }
  for (const field of changedFields) {
    if (!field.isConnected || field.closest('[data-update-dirty="false"]')
      || (field instanceof HTMLInputElement && field.type === 'text' && !field.value)) changedFields.delete(field);
  }
  if (changedFields.size) blockers.push("Bearbeitete Formulare zuerst speichern und schließen.");
  try {
    if (Object.keys(localStorage).some(key => key.startsWith("speccify.draft:"))) {
      blockers.push("Es gibt noch ungespeicherte Dokumententwürfe.");
    }
  } catch { blockers.push("Entwurfsspeicher kann nicht geprüft werden."); }
  return blockers;
}

/** Every window acknowledges only after locking its UI, including hidden windows. */
export function installUpdateGuard() {
  let token: string | undefined;
  let previousInert = false;
  const changed = (event: Event) => {
    if (event.target instanceof Element && !event.target.closest('[data-update-ui]')
      && event.target.matches('input,select')) changedFields.add(event.target);
  };
  document.addEventListener('change', changed, true);
  const listeners = [
    listen<string>('update-guard', event => {
      token = event.payload;
      const blockers = updateBlockers();
      previousInert = document.documentElement.inert;
      document.documentElement.inert = true;
      void invoke('update_guard_reply', { token, blockers });
    }),
    listen<string>('update-guard-release', event => {
      if (event.payload === token) {
        document.documentElement.inert = previousInert;
        token = undefined;
      }
    }),
  ];
  return () => {
    document.removeEventListener('change', changed, true);
    listeners.forEach(p => void p.then(unlisten => unlisten()));
    if (token) document.documentElement.inert = previousInert;
  };
}
