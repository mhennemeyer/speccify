// Types mirroring the backend's JSON (routes/playbooks.py).

export interface SourceRef {
  id: string;
  title: string;
  url: string;
  retrieved: string;
  note: string | null;
}

export interface PlaybookStep {
  id: string;
  title: string;
  detail: string;
  uses: string | null;
  verify: string | null;
  assets: string[];
  sources: SourceRef[];
}

export interface PlaybookSummary {
  id: string;
  source: string;
  version: string;
  title: string;
  summary: string;
  keywords: string[];
  platforms: string[];
  steps: number;
}

export interface PlaybookDetail {
  id: string;
  source: string;
  version: string;
  title: string;
  summary: string;
  applies_to: { platforms: string[]; requires: string[]; keywords: string[] };
  prerequisites: string[];
  steps: PlaybookStep[];
  sources: SourceRef[];
  pitfalls: string[];
  acceptance: { given: string | null; when: string | null; then: string | null }[];
  assets: string[];
  uses: string[];
  yaml: string;
}

/** What the user selected in the viewer — the context an agent asks about. */
export type Selection =
  | { kind: "playbook" }
  | { kind: "step"; stepId: string }
  | { kind: "source"; sourceId: string }
  | { kind: "asset"; path: string };
