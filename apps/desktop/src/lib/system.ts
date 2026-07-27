// System-Daten nativ aus dem Rust-Kern (R3): Doctor, Python-Verwaltung
// (uv) und Knowledgebase-Liste — die dotagent-CLI-Bridge ist Geschichte.
// Die Typen entsprechen 1:1 den früheren `dotagent … --json`-Formaten.

import { invoke } from "@tauri-apps/api/core";

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

export const fetchDoctor = () => invoke<{ checks: DoctorCheck[] }>("doctor");

export interface PythonsInfo {
  installed: { path: string; version: string | null }[];
  available: string[];
  uv: boolean;
}

export const fetchPythons = () => invoke<PythonsInfo>("python_list");

export const installPython = (version: string) =>
  invoke<unknown>("python_install", { version });

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
  invoke<{ knowledgebases: Knowledgebase[]; base_dir: string }>("kb_list");
