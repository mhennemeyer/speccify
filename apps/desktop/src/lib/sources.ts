// Skill-Quellen (Plan skill-quellen-und-export.md, Q1/Q2): Git-URL oder
// Ordner, global (Dashboard → Bibliothek) und pro Projekt (Skills-Tab).
// Git-Quellen klont der Rust-Kern einmal nach ~/.speccify/sources/ und
// behandelt den Checkout wie eine lokale Bibliothek (D1).

import { invoke } from "@tauri-apps/api/core";

export interface SourceInfo {
  name: string;
  location: string;
  kind: "git" | "dir";
  scope: "global" | "project";
  /** Checkout oder Ordner — hier liegen die Skills (als `--library`). */
  path: string | null;
  state: "ready" | "missing" | "error";
  detail: string | null;
}

export function listSources(project?: string | null): Promise<SourceInfo[]> {
  return invoke<SourceInfo[]>("sources_list", { project: project ?? null });
}

export function addSource(location: string, project?: string | null): Promise<SourceInfo> {
  return invoke<SourceInfo>("source_add", { project: project ?? null, location });
}

export function removeSource(location: string, project?: string | null): Promise<void> {
  return invoke("source_remove", { project: project ?? null, location });
}

export function refreshSource(source: SourceInfo): Promise<SourceInfo> {
  return invoke<SourceInfo>("source_refresh", {
    location: source.location,
    scope: source.scope,
  });
}

export function looksLikeGit(location: string): boolean {
  const s = location.trim();
  return (
    /^(https?|ssh|git|file):\/\//.test(s) || s.startsWith("git@") || s.startsWith("git+") || s.endsWith(".git")
  );
}

export const SOURCE_KIND_LABEL: Record<SourceInfo["kind"], string> = {
  git: "Git",
  dir: "Ordner",
};

export const SOURCE_SCOPE_LABEL: Record<SourceInfo["scope"], string> = {
  global: "global",
  project: "Projekt",
};
