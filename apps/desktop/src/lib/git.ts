// Git fürs Projektfenster (Plan ide-im-projektfenster.md, I2/I3): Typen,
// Aufrufe nach git_cmd.rs und das Zerlegen eines Diffs in Hunks — das
// Frontend setzt den Patch für `git apply --cached` selbst zusammen
// (Diff-Kopf + ein Hunk), Rust wendet ihn nur an.

import { invoke } from "@tauri-apps/api/core";

export interface GitEntry {
  path: string;
  index: string;
  worktree: string;
  untracked: boolean;
  conflicted: boolean;
  renamed_from: string | null;
}

export interface GitStatus {
  repo: boolean;
  branch: string | null;
  upstream: string | null;
  ahead: number;
  behind: number;
  entries: GitEntry[];
  error: string | null;
}

export interface GitCommit {
  hash: string;
  short: string;
  author: string;
  date: string;
  subject: string;
}

export interface GitChangedFile {
  path: string;
  status: string;
  renamed_from: string | null;
}

export interface GitCommitDetail extends GitCommit {
  body: string;
  files: GitChangedFile[];
}

export interface GitBranch {
  name: string;
  current: boolean;
  upstream: string | null;
  remote: boolean;
  worktree: string | null;
}

export const STATUS_LABEL: Record<string, string> = {
  M: "geändert",
  A: "neu",
  D: "gelöscht",
  R: "umbenannt",
  C: "kopiert",
  T: "Typ geändert",
  U: "Konflikt",
  "?": "unversioniert",
};

export function entryLabel(entry: GitEntry, staged: boolean): string {
  if (entry.conflicted) return "Konflikt";
  if (entry.untracked) return "unversioniert";
  const code = staged ? entry.index : entry.worktree;
  return STATUS_LABEL[code] ?? code;
}

export function isStaged(entry: GitEntry): boolean {
  return !entry.untracked && !entry.conflicted && entry.index !== ".";
}

export function isUnstaged(entry: GitEntry): boolean {
  return entry.untracked || entry.conflicted || entry.worktree !== ".";
}

export const gitStatus = (project: string) => invoke<GitStatus>("project_git_status", { project });
export const gitLog = (project: string, limit = 30) =>
  invoke<GitCommit[]>("project_git_log", { project, limit });
export const gitFileLog = (project: string, path: string, limit = 100) =>
  invoke<GitCommit[]>("project_git_file_log", { project, path, limit });
export const gitDiff = (project: string, path: string, staged: boolean) =>
  invoke<string>("project_git_diff", { project, path, staged });
export const gitCommitDetail = (project: string, commit: string) =>
  invoke<GitCommitDetail>("project_git_commit_detail", { project, commit });
export const gitCommitDiff = (project: string, commit: string, path?: string | null) =>
  invoke<string>("project_git_commit_diff", { project, commit, path: path ?? null });
export const gitStage = (project: string, paths: string[], stage: boolean) =>
  invoke("project_git_stage", { project, paths, stage });
export const gitApplyPatch = (project: string, patch: string, reverse: boolean) =>
  invoke("project_git_apply_patch", { project, patch, reverse });
export const gitDiscard = (project: string, paths: string[]) =>
  invoke("project_git_discard", { project, paths });
export const gitCommit = (project: string, message: string) =>
  invoke<string>("project_git_commit", { project, message });
export const gitBranches = (project: string) =>
  invoke<GitBranch[]>("project_git_branches", { project });
export const gitSwitch = (project: string, branch: string, create: boolean) =>
  invoke<string>("project_git_switch", { project, branch, create });
export const gitBranchRename = (project: string, branch: string, name: string) =>
  invoke<string>("project_git_branch_rename", { project, branch, name });
export const gitBranchDelete = (project: string, branch: string) =>
  invoke<string>("project_git_branch_delete", { project, branch });
export const gitInit = (project: string) => invoke<string>("project_git_init", { project });

export interface BlameLine {
  line: number;
  short: string;
  author: string;
  date: string;
  summary: string;
  uncommitted: boolean;
}

export const gitBlame = (project: string, path: string) =>
  invoke<BlameLine[]>("project_git_blame", { project, path });

export interface DiffHunk {
  /** Die `@@`-Zeile. */
  heading: string;
  /** Alle Zeilen des Hunks inkl. der `@@`-Zeile. */
  lines: string[];
}

export interface ParsedDiff {
  /** Zeilen vor dem ersten Hunk (`diff --git`, `index`, `---`, `+++`). */
  header: string[];
  hunks: DiffHunk[];
}

/** Ein Diff (eine Datei) in Kopf und Hunks zerlegen. */
export function parseDiff(text: string): ParsedDiff {
  const header: string[] = [];
  const hunks: DiffHunk[] = [];
  let current: DiffHunk | null = null;
  for (const line of text.replace(/\n$/, "").split("\n")) {
    if (line.startsWith("@@")) {
      current = { heading: line, lines: [line] };
      hunks.push(current);
    } else if (current) {
      current.lines.push(line);
    } else {
      header.push(line);
    }
  }
  return { header, hunks };
}

/** Patch für genau einen Hunk — `git apply --cached` versteht das. */
export function hunkPatch(diff: ParsedDiff, index: number): string {
  const hunk = diff.hunks[index];
  if (!hunk) return "";
  return [...diff.header, ...hunk.lines].join("\n") + "\n";
}

/** `2026-09-06T10:00:00+02:00` → `2026-09-06 10:00`. */
export function shortDate(iso: string): string {
  return iso.replace("T", " ").slice(0, 16);
}

/** Ereignis aus der Toolbar (git-pull/-push/-commit) — der Git-Tab hört zu. */
export function requestGit(verb: "fetch" | "pull" | "push" | "commit") {
  window.dispatchEvent(new CustomEvent("speccify:git", { detail: verb }));
}
