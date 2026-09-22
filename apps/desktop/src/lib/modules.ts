import { invoke } from "@tauri-apps/api/core";
import { useCallback, useEffect, useState } from "react";

/**
 * Spec 063: which modules of the project a spec touches, and where two specs
 * would collide. The catalogue (`modules` in the board root's
 * `.agent/settings.json`) is the project's architecture map; a spec's own
 * `modules:` front matter names what it touches. Overlap with another spec in
 * Doing is shown on the cards and in the inspector — the app warns, it does
 * not block.
 */
export interface ModuleDefinition {
  name: string;
  description: string;
  /** Optional path hints, e.g. `apps/desktop/src-tauri/src/terminal.rs`. */
  paths: string[];
}

/** Module names are slugs; the comparison is case-insensitive. */
export function normaliseModuleName(name: string): string {
  return name.trim().toLowerCase();
}

/** `a, B ,a` → `["a", "b"]` — the same normalisation as the native side. */
export function parseModuleList(value: string): string[] {
  const out: string[] = [];
  for (const raw of value.split(",")) {
    const name = normaliseModuleName(raw);
    if (name && name !== "null" && !out.includes(name)) out.push(name);
  }
  return out;
}

function definitionFrom(value: unknown): ModuleDefinition | null {
  if (typeof value === "string") {
    const name = normaliseModuleName(value);
    return name ? { name, description: "", paths: [] } : null;
  }
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  const name = typeof record.name === "string" ? normaliseModuleName(record.name) : "";
  if (!name) return null;
  const paths = Array.isArray(record.paths) ? record.paths.filter((p): p is string => typeof p === "string" && p.trim() !== "").map((p) => p.trim()) : [];
  return { name, description: typeof record.description === "string" ? record.description : "", paths };
}

/** The catalogue as read from settings; tolerant towards hand-written entries. */
export function parseModuleCatalogue(value: unknown): ModuleDefinition[] {
  if (!Array.isArray(value)) return [];
  const seen = new Set<string>();
  const out: ModuleDefinition[] = [];
  for (const entry of value) {
    const definition = definitionFrom(entry);
    if (!definition || seen.has(definition.name)) continue;
    seen.add(definition.name);
    out.push(definition);
  }
  return out;
}

export interface ModuleOverlap {
  module: string;
  /** The other specs in Doing that name the same module. */
  with: Array<{ file: string; id: string; number: number | null; title: string; owner: string | null }>;
}

interface ModuleSpecLike {
  file: string;
  id: string;
  number: number | null;
  title: string;
  station: string;
  owner: string | null;
  modules?: string[];
  archived?: boolean;
}

/**
 * Where `spec` collides: every module it names that another spec in Doing
 * names too. Done specs never count; a Backlog spec is compared against Doing
 * so the warning is visible before Backlog → Doing.
 */
export function moduleOverlaps<T extends ModuleSpecLike>(spec: T, all: T[]): ModuleOverlap[] {
  if (spec.station === "Done" || spec.archived) return [];
  const doing = all.filter((other) => other.file !== spec.file && other.station === "Doing" && !other.archived && (other.modules?.length ?? 0) > 0);
  const overlaps: ModuleOverlap[] = [];
  for (const module of spec.modules ?? []) {
    const others = doing.filter((other) => other.modules!.includes(module));
    if (others.length > 0) {
      overlaps.push({ module, with: others.map((other) => ({ file: other.file, id: other.id, number: other.number, title: other.title, owner: other.owner })) });
    }
  }
  return overlaps;
}

/** `#12` when numbered, else the id — how the board refers to a spec. */
export function specRef(spec: { id: string; number: number | null }): string {
  return spec.number !== null ? `#${spec.number}` : spec.id;
}

export interface ModuleCatalogue {
  modules: ModuleDefinition[];
  loaded: boolean;
  error: string | null;
  save: (modules: ModuleDefinition[]) => Promise<void>;
  reload: () => void;
}

/** Reads and writes the catalogue in the root's `.agent/settings.json` (`modules`). */
export function useModuleCatalogue(root: string | null | undefined): ModuleCatalogue {
  const [modules, setModules] = useState<ModuleDefinition[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!root) return;
    let stale = false;
    invoke<Record<string, unknown>>("project_settings_get", { project: root })
      .then((settings) => {
        if (stale) return;
        setModules(parseModuleCatalogue(settings.modules));
        setLoaded(true);
      })
      .catch(() => { if (!stale) setLoaded(true); /* ohne Settings: kein Katalog */ });
    return () => { stale = true; };
  }, [root, tick]);
  const save = useCallback(async (next: ModuleDefinition[]) => {
    if (!root) return;
    setError(null);
    const value = next.length === 0 ? null : next.map((module) => ({
      name: module.name,
      ...(module.description ? { description: module.description } : {}),
      ...(module.paths.length ? { paths: module.paths } : {}),
    }));
    try {
      await invoke("project_settings_set", { project: root, key: "modules", value });
      setModules(next);
    } catch (e) {
      setError(String(e));
      throw e;
    }
  }, [root]);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { modules, loaded, error, save, reload };
}
