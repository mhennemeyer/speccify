// CLI-Bridge: alle Daten kommen über `dotagent … --json` aus dem Toolkit.

import { invoke } from "@tauri-apps/api/core";

export interface RunSpec {
  command: string;
  args: string[];
  transport: "stdio" | "sse" | "http";
  autostart: boolean;
}

export interface Manifest {
  kind: "tool" | "mcp" | "kb";
  name: string;
  slug: string;
  description: string;
  tags: string[];
  category: string;
  run: RunSpec | null;
  requires_binaries: string[];
  source: "global" | "project";
  path: string | null;
}

export interface RegistryList {
  manifests: Manifest[];
  warnings: string[];
}

export interface DoctorCandidate {
  path: string;
  version: string | null;
}

export interface DoctorCheck {
  name: string;
  binary: string;
  found: boolean;
  path: string | null;
  version: string | null;
  hint: string;
  candidates: DoctorCandidate[];
}

export interface McpServer {
  slug: string;
  name: string;
  running: boolean;
  pid: number | null;
  log_file: string;
  transport: string | null;
}

export const runDotagent = (args: string[]) =>
  invoke<string>("run_dotagent", { args });

export async function runDotagentJson<T>(args: string[]): Promise<T> {
  return JSON.parse(await runDotagent(args)) as T;
}

export const fetchRegistry = () =>
  runDotagentJson<RegistryList>(["registry", "list", "--json"]);

export const fetchDoctor = () =>
  runDotagentJson<{ checks: DoctorCheck[] }>(["doctor", "--json"]);

export const fetchServers = () =>
  runDotagentJson<{ servers: McpServer[]; warnings: string[] }>([
    "mcp",
    "list",
    "--json",
  ]);

export interface PythonsInfo {
  installed: { path: string; version: string | null }[];
  available: string[];
  uv: boolean;
}

export const fetchPythons = () =>
  runDotagentJson<PythonsInfo>(["python", "list", "--json"]);

export interface BookEntry {
  title: string;
  file: string;
  /** Öffnbarer Pfad (Original-EPUB/PDF, sonst Markdown) — null wenn keins existiert. */
  path: string | null;
}

export interface Knowledgebase {
  name: string;
  path: string;
  books: number;
  chunks: number;
  index_size_mb: number;
  book_titles: string[];
  book_entries: BookEntry[];
}

export const fetchKnowledgebases = () =>
  runDotagentJson<{ knowledgebases: Knowledgebase[]; base_dir: string }>([
    "kb",
    "kbs",
    "--json",
  ]);

export const installPython = (version: string) =>
  runDotagent(["python", "install", version]);
